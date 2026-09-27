# models.py
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Dict, Any
from playwright.async_api import Page, ElementHandle, Download
import asyncio

from ..logging_setup import get_logger

logger = get_logger(__name__)

from ..codec_detector import detect_codec


def normalize_sender_name(value: Optional[str]) -> str:
    """Normalize a sender name for identity comparison.

    Casefolds, collapses whitespace, and strips accents so "Tú" matches
    "tu" and "  BIKES Amigorena " matches "Bikes Amigorena".
    """
    if not value:
        return ""
    collapsed = " ".join(value.split()).casefold()
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFKD", collapsed) if not unicodedata.combining(ch)
    )
    return stripped


def normalize_own_push_names(own_push_names: Optional[Iterable[str]]) -> frozenset:
    """Normalize the account push names into a lookup set (accent-insensitive)."""
    if own_push_names is None:
        return frozenset()
    if isinstance(own_push_names, str):
        own_push_names = [own_push_names]
    names = {normalize_sender_name(name) for name in own_push_names}
    return frozenset(name for name in names if name)


#: Normalized tokens that always mean "own message" (Spanish/English WA Web).
OWN_SENDER_TOKENS = frozenset({"tu"})


class DirectionSignal:
    """String constants for ``Message.direction_signal``.

    Single authority for signal names; the precedence order lives in
    DIRECTION_ORDER. Values stay plain strings for backward compatibility
    (probes, logs, and consumers compare against ``"tail-out"`` etc.).
    """

    TAIL_OUT = "tail-out"
    TAIL_IN = "tail-in"
    CLASS_OUT = "class-out"
    CLASS_IN = "class-in"
    DATA_ID_OUT = "data-id-out"
    DATA_ID_IN = "data-id-in"
    GROUP_OUT = "group-out"
    GROUP_IN = "group-in"
    POSITION_OUT = "position-out"
    POSITION_IN = "position-in"
    SENDER_OWN = "sender-own"
    NONE = "none"


#: Layered direction precedence (single source of truth).
#: tail (ground truth for group leaders) > class / data-id (opportunistic,
#: dead in some WA Web builds) > group inheritance (tail-delimited groups,
#: applied by ChatManager AFTER from_element) > positional inner-bubble
#: alignment > sender identity (optional last resort) > none (documented
#: fail-safe default to incoming, flagged via the fallback counter).
#: Referenced by Message.from_element, ChatManager.collect_messages, and
#: the console probe (examples/wa_direction_probe.js, parity-tested).
DIRECTION_ORDER = (
    DirectionSignal.TAIL_OUT,
    DirectionSignal.TAIL_IN,
    DirectionSignal.CLASS_OUT,
    DirectionSignal.CLASS_IN,
    DirectionSignal.DATA_ID_OUT,
    DirectionSignal.DATA_ID_IN,
    DirectionSignal.GROUP_OUT,
    DirectionSignal.GROUP_IN,
    DirectionSignal.POSITION_OUT,
    DirectionSignal.POSITION_IN,
    DirectionSignal.SENDER_OWN,
    DirectionSignal.NONE,
)

#: Geometry rule: a bubble candidate counts as the inner bubble only when
#: narrower than ``row_width * POSITIONAL_ABSTAIN_RATIO``; at/above the
#: ratio the probe abstains (null) so group inheritance decides instead of
#: a lying positional. Boundary-tested under node (test_probe_parity.py).
POSITIONAL_ABSTAIN_RATIO = 0.85

#: Ancestor-walk depth for the selectable-text anchor when resolving the
#: inner bubble (text path of the geometry probe).
BUBBLE_WALK_DEPTH = 6

#: Parent-walk depth when searching a chat container fallback for the
#: midpoint basis (geometry probe).
CONTAINER_WALK_DEPTH = 8

#: Count of bubbles that survived every layer with no signal (none ->
#: incoming default). Flagged path: incremented in
#: ChatManager._apply_group_tail_inheritance with a log line, never silent.
_DIRECTION_FALLBACK_COUNT = 0


def get_direction_fallback_count() -> int:
    """Return how many bubbles fell through to the none->incoming default."""
    return _DIRECTION_FALLBACK_COUNT


def reset_direction_fallback_count() -> None:
    """Reset the none->incoming fallback counter (tests, diagnostics)."""
    global _DIRECTION_FALLBACK_COUNT
    _DIRECTION_FALLBACK_COUNT = 0


def _flag_direction_fallback(testid: str) -> None:
    """Flag a bubble that defaulted to incoming with zero signals."""
    global _DIRECTION_FALLBACK_COUNT
    _DIRECTION_FALLBACK_COUNT += 1
    logger.warning(
        "direction: bubble %s has no tail/class/data-id/group/positional/"
        "sender signal; defaulting to incoming (fail-safe, verify sender)",
        testid or "?",
    )


async def _self_or_descendant_has_class(elem: ElementHandle, class_name: str) -> bool:
    """Check a direction CSS class on the bubble container itself or below it.

    Live DOM evidence shows ``message-out`` / ``message-in`` may live on
    the ``[data-testid^=conv-msg]`` container itself (``el.classList``),
    not on a descendant, so a descendant-only ``query_selector`` misses
    them. A single ``evaluate`` covers self + descendants at once.
    Returns False when evaluation is unavailable (strict bool check so
    mock handles never count as a positive signal).
    """
    try:
        found = await elem.evaluate(
            "(el, cls) => el.classList.contains(cls) || !!el.querySelector('.' + cls)",
            class_name,
        )
        return found is True
    except Exception:
        return False


async def _resolve_data_id(elem: ElementHandle, outer_id: str) -> str:
    """Resolve the ``data-id`` direction carrier for a bubble container.

    Live DOM evidence shows ``data-id`` may live on an inner row rather
    than the outer ``[data-testid^=conv-msg]`` container, so an empty
    outer value falls back to the first descendant carrying ``data-id``.
    """
    if outer_id:
        return outer_id
    try:
        inner = await elem.query_selector("[data-id]")
        if inner is not None:
            return (await inner.get_attribute("data-id")) or ""
    except Exception:
        pass
    return ""


#: JS probe reporting bubble alignment relative to the chat container.
#: Returns {"side": "right"|"left", "rectLeft": float, "chatMid": float}
#: or None when geometry is unavailable or inconclusive. Measures the
#: inner bubble (selectable-text ancestor / narrower child), never the
#: full-width row container: live v3 evidence showed the row rect reports
#: side=left for every bubble including tail-out outgoing. When the bubble
#: width ~= row width the probe abstains (null) so the group layer decides
#: instead of a lying positional. Midpoint comparison keeps the signal
#: robust to window size: right = outgoing, left = incoming.
#: Single-sourced from POSITIONAL_ABSTAIN_RATIO / BUBBLE_WALK_DEPTH /
#: CONTAINER_WALK_DEPTH (template below); the console probe embeds the
#: same block, guarded by test_probe_parity.py.
_POSITIONAL_SIDE_TEMPLATE = """(el) => {
    try {
        const rowRect = el.getBoundingClientRect();
        if (!rowRect || rowRect.width === 0) return null;
        // Measure the inner bubble, not the full-width row container.
        let target = null;
        const anchor = el.querySelector('[data-testid="selectable-text"]');
        if (anchor) {
            let cur = anchor;
            for (let i = 0; i < __BUBBLE_WALK__ && cur && cur !== el; i++) {
                const r = cur.getBoundingClientRect();
                if (r && r.width > 0 && r.width < rowRect.width * __RATIO__) {
                    target = r;
                    break;
                }
                cur = cur.parentElement;
            }
            if (!target) {
                const ar = anchor.getBoundingClientRect();
                if (ar && ar.width > 0) target = ar;
            }
        } else {
            // No text anchor (voice note, sticker, document): first
            // child row meaningfully narrower than the row container.
            const kids = el.children || [];
            for (let i = 0; i < kids.length && !target; i++) {
                const r = kids[i].getBoundingClientRect();
                if (r && r.width > 0 && r.width < rowRect.width * __RATIO__) {
                    target = r;
                }
            }
        }
        if (!target || target.width === 0) return null;
        // Inconclusive geometry (bubble ~= row width): abstain so the
        // group layer decides instead of a lying positional.
        if (target.width >= rowRect.width * __RATIO__) return null;
        let container = el.closest('[data-testid="conversation-panel-body"]');
        if (!container) {
            let cur = el.parentElement;
            for (let i = 0; i < __CONTAINER_WALK__ && cur; i++) {
                const r = cur.getBoundingClientRect();
                if (r.width > rowRect.width * 2) { container = cur; break; }
                cur = cur.parentElement;
            }
        }
        const basis = container
            ? container.getBoundingClientRect()
            : { left: 0, width: window.innerWidth };
        const chatMid = basis.left + basis.width / 2;
        const center = target.left + target.width / 2;
        return { side: center > chatMid ? 'right' : 'left', rectLeft: target.left, chatMid };
    } catch (e) {
        return null;
    }
}"""

POSITIONAL_SIDE_JS = (
    _POSITIONAL_SIDE_TEMPLATE.replace("__RATIO__", str(POSITIONAL_ABSTAIN_RATIO))
    .replace("__BUBBLE_WALK__", str(BUBBLE_WALK_DEPTH))
    .replace("__CONTAINER_WALK__", str(CONTAINER_WALK_DEPTH))
)


async def _resolve_positional_side(elem: ElementHandle) -> Optional[str]:
    """Resolve inner-bubble alignment: "right" (outgoing), "left" (incoming).

    Config-free signal for continuation bubbles that carry no tail, no
    direction class, and no data-id bit. Measures the inner bubble, not
    the full-width row container, and returns None when geometry is
    unavailable or inconclusive (bubble ~= row width) so callers fall
    through to group inheritance and, as a last resort, sender identity.
    """
    try:
        result = await elem.evaluate(POSITIONAL_SIDE_JS)
    except Exception:
        return None
    if isinstance(result, dict):
        side = result.get("side")
        if side in ("right", "left"):
            return side
    elif isinstance(result, str) and result in ("right", "left"):
        return result
    return None


def parse_timestamp(raw: str) -> Optional[datetime]:
    """Extract the message time from a ``data-pre-plain-text`` attribute value.

    Acepta las formas que fue usando WhatsApp Web:
      - legacy sin fecha: ``[10:00] Sender:``
      - con fecha (Sept 2026): ``[18:51, 3/9/2026] Sender:``
      - 12h con am/pm (observado Sept 2026): ``6:55 p.m. Sender:``

    Returns a ``datetime`` with today's date and the parsed time,
    or ``None`` if the format does not match.
    """
    # Forma con corchetes: [HH:MM(:SS)?] o [HH:MM, d/m/yyyy]
    m = re.match(r"\[(\d{1,2}:\d{2}(?::\d{2})?)(?:,\s*\d{1,2}/\d{1,2}/\d{2,4})?\]", raw)
    if m:
        hh, mm = m.group(1).split(":")[:2]
        now = datetime.now()
        return now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)

    # Forma 12h suelta: "6:55 p.m." / "7:07 p. m." / "12:30 am"
    m12 = re.match(r"(\d{1,2}):(\d{2})\s*([ap])\.?\s*m", raw.strip().lower())
    if m12:
        hh = int(m12.group(1)) % 12
        mm = int(m12.group(2))
        if m12.group(3) == "p":
            hh += 12
        now = datetime.now()
        return now.replace(hour=hh, minute=mm, second=0, microsecond=0)

    return None


def _format_duration(seconds: object) -> str:
    """Format a float duration in seconds to ``MM:SS``.

    Returns ``""`` for ``None``, negative, or non-numeric input.
    """
    try:
        seconds = float(seconds)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if seconds < 0:
        return ""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


class Message:
    """
    Represents a WhatsApp message.

    This object encapsulates all data related to a single message in a chat,
    including its content, sender, timestamp, and interactivity methods.

    Attributes:
        page (Page): The Playwright Page object.
        sender (str): The name or phone number of the sender.
        timestamp (datetime): The time the message was received.
        text (str): The text content of the message.
        container (ElementHandle): The DOM element containing the message.
        is_outgoing (bool): True if the message was sent by the user, False otherwise.
        msg_id (str): The unique identifier of the message.
    """

    def __init__(
        self,
        page: Page,
        sender: str,
        timestamp: datetime,
        text: str,
        container: ElementHandle,
        is_outgoing: bool = False,
        msg_id: str = "",
        sender_inherited: bool = False,
        direction_signal: str = "none",
    ):
        self.page = page
        self.sender = sender
        self.timestamp = timestamp
        self.text = text
        self.container = container
        self.is_outgoing = is_outgoing
        self.msg_id = msg_id
        # True when sender was inherited from a neighboring bubble in
        # collect_messages (sender-less continuation). Display-only: consumers
        # must use is_outgoing / is_from_self() for skip logic, never this.
        self.sender_inherited = sender_inherited
        # Which signal decided is_outgoing (a DirectionSignal value; see
        # DIRECTION_ORDER for precedence).
        self.direction_signal = direction_signal

    def is_from_self(self, own_push_names: Optional[Iterable[str]] = None) -> bool:
        """Safe skip decision for bot consumers.

        Returns True when the bubble is structurally outgoing OR its sender
        is the account identity ("Tu" or one of own_push_names). An
        inherited display sender alone never counts as self.
        """
        if self.is_outgoing:
            return True
        if self.sender_inherited or not self.sender:
            return False
        own = normalize_own_push_names(own_push_names) | OWN_SENDER_TOKENS
        return normalize_sender_name(self.sender) in own

    @classmethod
    async def from_element(
        cls,
        elem: ElementHandle,
        page: Page,
        own_push_names: Optional[Iterable[str]] = None,
    ) -> Optional["Message"]:
        """
        Create a Message instance from a DOM element.

        Args:
            elem: The message container element.
            page: The Playwright page.
            own_push_names: Account push names identifying own bubbles
                (e.g. ["Bikes Amigorena"]). Compared accent/case-insensitively.

        Direction precedence is DIRECTION_ORDER (see module constants):
        tail is ground truth for group leaders; class and data-id are
        opportunistic (dead in some WA Web builds, never required) and
        outrank group inheritance; group inheritance (ChatManager, applied
        after this method) outranks positional; positional measures the
        inner bubble and abstains on inconclusive geometry; sender identity
        ("Tu", or own_push_names when explicitly passed) is an optional
        last resort. A bubble with no signal in either direction defaults
        to incoming with direction_signal "none" (documented fail-safe;
        ChatManager flags survivors via the fallback counter + log).

        Returns:
            A new Message instance or None if parsing fails.
        """
        try:
            # 0) ID if exists (outer container first, inner row fallback:
            #    data-id may live on a descendant, not on the conv-msg node).
            msg_id = (await elem.get_attribute("data-id")) or ""
            msg_id = await _resolve_data_id(elem, msg_id)
            testid = (await elem.get_attribute("data-testid")) or ""

            # 1) Sender + Timestamp: ambos desde data-pre-plain-text
            #    Formato: "[HH:MM(:SS)?] Sender Name: message text"
            sender = ""
            timestamp = datetime.now()
            pre_plain = await elem.query_selector("[data-pre-plain-text]")
            if pre_plain:
                raw = await pre_plain.get_attribute("data-pre-plain-text")
                if raw:
                    # Sender (después del "] ")
                    if "] " in raw:
                        sender = raw.split("] ", 1)[1].rstrip(": ").strip()
                    # Timestamp (desde el bracket)
                    parsed_ts = parse_timestamp(raw)
                    if parsed_ts:
                        timestamp = parsed_ts
            if not sender:
                # Fallback: aria-label del span remitente (solo primer msg de cada uno)
                remitente_span = await elem.query_selector(
                    'xpath=.//span[@aria-label and substring(@aria-label, string-length(@aria-label))=":"]'
                )
                if remitente_span:
                    raw_label = await remitente_span.get_attribute("aria-label")
                    if raw_label:
                        sender = raw_label.rstrip(":").strip()

            # Direction layers in DIRECTION_ORDER precedence (tail first).
            # Class + data-id stay opportunistic (dead in some builds);
            # positional is the primary continuation signal; sender identity
            # is an optional last resort (never required).
            is_outgoing = False
            direction_signal = DirectionSignal.NONE

            tail_out = await elem.query_selector('[data-testid="tail-out"]')
            tail_in = await elem.query_selector('[data-testid="tail-in"]')
            # Direction classes may sit on the container itself
            # (el.classList) or on a descendant; check both at once.
            # The descendant query_selector is kept as a fallback for
            # handles where evaluate is unavailable.
            message_out = await elem.query_selector(".message-out")
            message_in = await elem.query_selector(".message-in")
            has_message_out = message_out is not None or await _self_or_descendant_has_class(
                elem, "message-out"
            )
            has_message_in = message_in is not None or await _self_or_descendant_has_class(
                elem, "message-in"
            )

            # data-id direction bit: "true_<chat>_<id>" = own, "false_..." = peer.
            data_id_outgoing: Optional[bool] = None
            if msg_id:
                head = msg_id.split("_", 1)[0].casefold()
                if head == "true":
                    data_id_outgoing = True
                elif head == "false":
                    data_id_outgoing = False

            positional_side = await _resolve_positional_side(elem)

            # Sender identity is a last resort: "Tu" always counts as own
            # (WhatsApp's own-message label, not per-account config), while
            # account push names only count when explicitly passed
            # (own_push_names is not None). Consulted solely when tail +
            # class + data-id + positional are all inconclusive.
            if own_push_names is None:
                configured_own: frozenset = frozenset()
            else:
                configured_own = normalize_own_push_names(own_push_names)
            own_names = configured_own | OWN_SENDER_TOKENS
            sender_is_own = bool(sender) and normalize_sender_name(sender) in own_names

            if tail_out is not None:
                is_outgoing, direction_signal = True, DirectionSignal.TAIL_OUT
            elif tail_in is not None:
                direction_signal = DirectionSignal.TAIL_IN
            elif has_message_out:
                is_outgoing, direction_signal = True, DirectionSignal.CLASS_OUT
            elif has_message_in:
                direction_signal = DirectionSignal.CLASS_IN
            elif data_id_outgoing is True:
                is_outgoing, direction_signal = True, DirectionSignal.DATA_ID_OUT
            elif data_id_outgoing is False:
                direction_signal = DirectionSignal.DATA_ID_IN
            elif positional_side == "right":
                is_outgoing, direction_signal = True, DirectionSignal.POSITION_OUT
            elif positional_side == "left":
                direction_signal = DirectionSignal.POSITION_IN
            elif sender_is_own:
                # Optional last resort for sender-signed bubbles when every
                # structural and geometric signal is inconclusive. (The
                # legacy conv-msg-AC prefix fallback was removed in v2.5.0:
                # Sept 2026 live evidence showed the AC prefix on every row
                # in both directions, so it only produced false outgoing.)
                is_outgoing, direction_signal = True, DirectionSignal.SENDER_OWN

            # 3) Text
            texto = ""
            selectable = await elem.query_selector('[data-testid="selectable-text"]')
            if selectable:
                raw_inner = await selectable.inner_text()
                if raw_inner:
                    lineas = raw_inner.split("\n")
                    if len(lineas) > 1 and (lineas[0].strip().startswith(sender) or ":" in lineas[0]):
                        texto = "\n".join(lineas[1:]).strip()
                    else:
                        texto = raw_inner.strip()

            return cls(
                page=page,
                sender=sender,
                timestamp=timestamp,
                text=texto,
                container=elem,
                is_outgoing=is_outgoing,
                msg_id=msg_id,
                direction_signal=direction_signal,
            )
        except Exception as ex:
            logger.debug("Message.from_element EXCEPTION for %s: %s: %s", testid, type(ex).__name__, ex)
            return None

    async def react(self, emoji: str):
        """
        Reacts to this message with the given emoji.

        This method simulates the user interaction of hovering over the message,
        clicking the reaction button, and selecting an emoji.

        Args:
            emoji (str): The emoji character to react with (e.g., "👍", "❤️").
        """

        try:
            # 1. Hover over the message to make the action bar appear.
            await self.container.hover()
            await asyncio.sleep(0.5)

            # 2. Find reaction button
            reaction_bar = self.page.locator('[aria-label="Reaccionar"]')
            if not reaction_bar:
                return None
            await reaction_bar.click()

            # 3. Find "More reactions" button
            more_reactions_button_handle = self.page.locator('[aria-label="Más reacciones"]')
            if not more_reactions_button_handle:
                return None

            await more_reactions_button_handle.click()

            # 4. Find emoji in picker
            emoji_in_picker = self.page.locator(f'[data-emoji="{emoji}"]')

            # 5. Click emoji
            await emoji_in_picker.wait_for(state="visible", timeout=5000)
            await emoji_in_picker.click()

        except Exception as e:
            logger.warning(f"An error occurred while reacting to message {self.msg_id}: {e}")


# ==============================
# File message helpers
# ==============================


async def _find_file_icon(elem: ElementHandle) -> Optional[ElementHandle]:
    """
    Find a file/document icon in a message element.

    Tries multiple selectors for compatibility across WhatsApp Web versions:
    - audio-download (legacy)
    - document-PDF-icon (2026)
    - any data-icon containing 'document' (fallback)

    Returns:
        The icon element, or None if not a file message.
    """
    selectors = [
        'span[data-icon="audio-download"]',
        'span[data-icon="document-PDF-icon"]',
        'span[data-icon*="document"]',
    ]
    for selector in selectors:
        icon = await elem.query_selector(selector)
        if icon:
            return icon
    return None


async def _extract_filename(icon: ElementHandle) -> str:
    """
    Extract filename from a file message icon.

    WhatsApp Web stores filenames in the `title` attribute of
    `div[data-testid="document-thumb"]`, formatted as: Ver "filename.ext"

    Returns:
        The filename, or empty string if not found.
    """
    # Walk up from icon to find the document-thumb container
    result = await icon.evaluate("""
        (node) => {
            let curr = node;
            for (let i = 0; i < 10 && curr; i++) {
                if (curr.getAttribute && curr.getAttribute('data-testid') === 'document-thumb') {
                    let title = curr.getAttribute('title') || '';
                    // Title format: Ver "filename.ext"
                    let match = title.match(/"(.+?)"/);
                    return match ? match[1] : '';
                }
                curr = curr.parentElement;
            }
            return '';
        }
    """)
    return result


class FileMessage(Message):
    """
    Represents a message containing a downloadable file.

    Inherits from `Message` and adds specific functionality for handling
    media and document attachments.

    Attributes:
        filename (str): The name of the file (e.g., "document.pdf").
        download_icon (ElementHandle): The DOM element for the download button.
    """

    def __init__(
        self,
        page: Page,
        sender: str,
        timestamp: datetime,
        text: str,
        container: ElementHandle,
        filename: str,
        download_icon: ElementHandle,
        is_outgoing: bool = False,
        msg_id: str = "",
        sender_inherited: bool = False,
        direction_signal: str = "none",
    ):
        super().__init__(
            page,
            sender,
            timestamp,
            text,
            container,
            is_outgoing=is_outgoing,
            msg_id=msg_id,
            sender_inherited=sender_inherited,
            direction_signal=direction_signal,
        )
        self.filename = filename
        self.download_icon = download_icon

    @classmethod
    async def from_element(
        cls,
        elem: ElementHandle,
        page: Page,
        own_push_names: Optional[Iterable[str]] = None,
    ) -> Optional["FileMessage"]:
        """
        Create a FileMessage from a DOM element.

        Checks for the presence of a download/document icon and extracts the filename.

        Args:
            elem: The message container element.
            page: The Playwright page.
            own_push_names: Account push names identifying own bubbles.

        Returns:
            A new FileMessage instance or None if not a valid file message.
        """
        try:
            # 1) Find file icon (try multiple selectors for compatibility)
            icon = await _find_file_icon(elem)
            if not icon:
                return None

            # 2) Extract filename from DOM
            filename = await _extract_filename(icon)
            if not filename:
                return None

            # 3) Extract base message data
            base_msg = await Message.from_element(elem, page, own_push_names)
            if not base_msg:
                return None

            return cls(
                page=page,
                sender=base_msg.sender,
                timestamp=base_msg.timestamp,
                text=base_msg.text,
                container=elem,
                filename=filename,
                download_icon=icon,
                is_outgoing=base_msg.is_outgoing,
                msg_id=base_msg.msg_id,
                sender_inherited=base_msg.sender_inherited,
                direction_signal=base_msg.direction_signal,
            )

        except Exception:
            return None

    async def download(self, page: Page, downloads_dir: Path) -> Optional[Path]:
        """
        Download the attached file.

        Clicks the download icon and waits for the download to complete.

        Args:
            page: The Playwright Page object.
            downloads_dir: The directory where the file should be saved.

        Returns:
            The Path to the saved file, or None if the download failed.
        """
        try:
            # 1) Create directory
            downloads_dir.mkdir(parents=True, exist_ok=True)

            # 2) Wait for download
            async with page.expect_download() as evento:
                await self.download_icon.click()
            descarga: Download = await evento.value

            # 3) Get filename and path
            suggested = descarga.suggested_filename or self.filename
            destino = downloads_dir / suggested

            # 4) Save to disk
            await descarga.save_as(str(destino))
            return destino

        except Exception:
            return None

    def get_codec_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get codec information from a downloaded audio file.

        Args:
            file_path: Path to the downloaded audio file

        Returns:
            Dict with codec info or None if detection fails
        """
        return detect_codec(file_path)


class VoiceMessage(Message):
    """
    Represents a voice message without visible download icon.

    This class handles voice messages that need to be played first
    to trigger the download capability.
    """

    def __init__(
        self,
        page: Page,
        sender: str,
        timestamp: datetime,
        text: str,
        container: ElementHandle,
        duration: str = "",
        is_outgoing: bool = False,
        msg_id: str = "",
        sender_inherited: bool = False,
        direction_signal: str = "none",
    ):
        super().__init__(
            page,
            sender,
            timestamp,
            text,
            container,
            is_outgoing=is_outgoing,
            msg_id=msg_id,
            sender_inherited=sender_inherited,
            direction_signal=direction_signal,
        )
        self.duration = duration

    @classmethod
    async def from_element(
        cls,
        elem: ElementHandle,
        page: Page,
        own_push_names: Optional[Iterable[str]] = None,
    ) -> Optional["VoiceMessage"]:
        """
        Create a VoiceMessage from a DOM element.

        Checks for voice message indicators (mic icon, voice container).

        Args:
            elem: The message container element.
            page: The Playwright page.
            own_push_names: Account push names identifying own bubbles.

        Returns:
            A new VoiceMessage instance or None if not a valid voice message.
        """
        try:
            is_quoted = await elem.query_selector('[aria-label="Mensaje citado"]')
            if is_quoted:
                return None

            has_play_button = await elem.query_selector('button[aria-label*="voz"], button[aria-label*="voice" i]')
            has_voice_container = await elem.query_selector('span[aria-label*="voz"], span[aria-label*="voice" i]')

            # Check for voice icon using evaluate (more reliable than :has selector)
            has_voice_icon = await elem.evaluate(
                """(el) => {
                    const svgs = el.querySelectorAll('svg');
                    for (const svg of svgs) {
                        const title = svg.querySelector('title');
                        if (title && title.textContent.includes('ic-keyboard-voice')) {
                            return true;
                        }
                    }
                    return false;
                }"""
            )

            if not has_play_button and not has_voice_container and not has_voice_icon:
                return None

            duration = ""
            try:
                # Method 1: native audio.duration (works when audio element exists)
                seconds = await elem.evaluate(
                    """(el) => {
                        const audio = el.querySelector('audio');
                        if (!audio) return null;
                        const d = audio.duration;
                        return (typeof d === 'number' && !isNaN(d) && d >= 0) ? d : null;
                    }"""
                )
                if seconds is not None:
                    duration = _format_duration(seconds)
                else:
                    # Method 2: fallback — parse from slider aria-valuetext "0:00/MM:SS"
                    slider_dur = await elem.evaluate(
                        """(el) => {
                            const slider = el.querySelector('[role="slider"][aria-valuetext]');
                            if (!slider) return null;
                            const vt = slider.getAttribute('aria-valuetext');
                            if (!vt) return null;
                            // format: "0:00/MM:SS" or "M:SS/MM:SS"
                            const parts = vt.split('/');
                            if (parts.length < 2) return null;
                            const total = parts[parts.length - 1].trim();
                            const m = total.match(/^(\\d{1,2}):(\\d{2})$/);
                            if (!m) return null;
                            return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
                        }"""
                    )
                    if slider_dur is not None:
                        duration = _format_duration(slider_dur)
            except Exception:
                logger.warning("VoiceMessage: failed to extract voice duration")

            base_msg = await Message.from_element(elem, page, own_push_names)
            if not base_msg:
                return None

            return cls(
                page=page,
                sender=base_msg.sender,
                timestamp=base_msg.timestamp,
                text=base_msg.text,
                container=elem,
                duration=duration,
                is_outgoing=base_msg.is_outgoing,
                msg_id=base_msg.msg_id,
                sender_inherited=base_msg.sender_inherited,
                direction_signal=base_msg.direction_signal,
            )

        except Exception:
            return None

    async def download_via_play(self, page: Page, downloads_dir: Path) -> Optional[Path]:
        """
        Download voice message by clicking play first, then download.

        Method 1: Click play button → wait for download icon → download

        Args:
            page: The Playwright Page object.
            downloads_dir: The directory where the file should be saved.

        Returns:
            The Path to the saved file, or None if download failed.
        """
        try:
            downloads_dir.mkdir(parents=True, exist_ok=True)

            play_button = await self.container.query_selector('button[aria-label="Reproducir mensaje de voz"]')
            if not play_button:
                return None

            await play_button.click()
            await asyncio.sleep(1)

            download_icon = await self.container.query_selector('span[data-icon="audio-download"]')
            if not download_icon:
                return None

            async with page.expect_download() as evento:
                await download_icon.click()
            descarga: Download = await evento.value

            filename = descarga.suggested_filename or f"voice_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.ogg"
            destino = downloads_dir / filename

            await descarga.save_as(str(destino))
            return destino

        except Exception:
            return None

    async def download_via_context_menu(self, page: Page, downloads_dir: Path) -> Optional[Path]:
        """
        Download voice message via right-click context menu.

        Method 3: Right-click → select "Descargar" → download

        Args:
            page: The Playwright page.
            downloads_dir: The directory where the file should be saved.

        Returns:
            The Path to the saved file, or None if download failed.
        """
        try:
            downloads_dir.mkdir(parents=True, exist_ok=True)

            await self.container.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)

            async with page.expect_download() as download_info:
                target_found = await page.evaluate(
                    """(el) => {
                        // Priority: play button is the most stable voice target
                        // Support both Spanish (voz) and English (voice) locale
                        const target = el.querySelector('button[aria-label*="voz"], button[aria-label*="voice" i]')
                            || el.querySelector('[class*="_ak4"]');
                        if (!target) return false;
                        const rect = target.getBoundingClientRect();
                        const event = new MouseEvent('contextmenu', {
                            bubbles: true,
                            cancelable: true,
                            view: window,
                            clientX: rect.left + rect.width / 2,
                            clientY: rect.top + rect.height / 2
                        });
                        target.dispatchEvent(event);
                        return true;
                    }""",
                    self.container,
                )
                if not target_found:
                    logger.warning(
                        "VoiceMessage.download_via_context_menu: no target element found for msg %s",
                        self.msg_id,
                    )

                await asyncio.sleep(0.5)

                await page.evaluate(
                    """
                    () => {
                        const menu = document.querySelector('[role="menu"]');
                        if (menu) {
                            const items = menu.querySelectorAll('[role="menuitem"]');
                            for (const item of items) {
                                if (item.textContent.includes('Descargar')) {
                                    item.click();
                                }
                            }
                        }
                    }"""
                )

            download = await download_info.value

            filename = download.suggested_filename or f"voice_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.ogg"
            destino = downloads_dir / filename

            await download.save_as(str(destino))
            return destino

        except Exception:
            return None

    async def download_via_blob(self, page: Page, downloads_dir: Path) -> Optional[Path]:
        """
        Download voice message by extracting audio blob directly.

        Method 2: Extract audio src/blob via JavaScript → download

        Args:
            page: The Playwright Page object.
            downloads_dir: The directory where the file should be saved.

        Returns:
            The Path to the saved file, or None if download failed.
        """
        try:
            downloads_dir.mkdir(parents=True, exist_ok=True)

            audio_data = await self.container.evaluate(
                """
                () => {
                    const audio = this.querySelector('audio') || this.querySelector('video');
                    if (!audio) return null;
                    
                    if (audio.src && audio.src.startsWith('blob:')) {
                        return { type: 'blob', src: audio.src };
                    }
                    if (audio.currentSrc) {
                        return { type: 'src', src: audio.currentSrc };
                    }
                    return null;
                }
                """
            )

            if not audio_data or not audio_data.get("src"):
                return None

            filename = f"voice_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.ogg"
            destino = downloads_dir / filename

            if audio_data["type"] == "blob":
                return await self._download_blob_audio(page, audio_data["src"], destino)
            else:
                return await self._download_url_audio(page, audio_data["src"], destino)

        except Exception:
            return None

    async def _download_blob_audio(self, page: Page, blob_url: str, destino: Path) -> Optional[Path]:
        """Download audio from blob URL."""
        try:
            import base64

            audio_base64 = await page.evaluate(
                f"""
                async () => {{
                    const response = await fetch('{blob_url}');
                    const blob = await response.blob();
                    return new Promise((resolve) => {{
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    }});
                }}
                """
            )

            if audio_base64:
                audio_bytes = base64.b64decode(audio_base64)
                destino.write_bytes(audio_bytes)
                return destino

            return None
        except Exception:
            return None

    async def _download_url_audio(self, page: Page, audio_url: str, destino: Path) -> Optional[Path]:
        """Download audio from direct URL."""
        try:
            import httpx

            response = await httpx.AsyncClient().get(audio_url)
            if response.status_code == 200:
                destino.write_bytes(response.content)
                return destino
            return None
        except Exception:
            return None

    async def download(self, page: Page, downloads_dir: Path) -> Optional[Path]:
        """
        Download voice message using combined methods.

        Tries: 1) play → download icon, 2) context menu, 3) blob.

        Args:
            page: The Playwright page.
            downloads_dir: The directory where the file should be saved.

        Returns:
            The Path to the saved file, or None if download failed.
        """
        file_path = await self.download_via_play(page, downloads_dir)
        if not file_path:
            file_path = await self.download_via_context_menu(page, downloads_dir)
        if not file_path:
            file_path = await self.download_via_blob(page, downloads_dir)
        return file_path

    def get_codec_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get codec information from downloaded audio file."""
        return detect_codec(file_path)
