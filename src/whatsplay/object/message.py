# models.py
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import Page, ElementHandle, Download
import asyncio

logger = logging.getLogger(__name__)

from ..codec_detector import detect_codec


def parse_timestamp(raw: str) -> Optional[datetime]:
    """Extract ``[HH:MM(:SS)?]`` from a ``data-pre-plain-text`` attribute value.

    Returns a ``datetime`` with today's date and the parsed time,
    or ``None`` if the format does not match.
    """
    m = re.match(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]", raw)
    if not m:
        return None
    hh, mm = m.group(1).split(":")[:2]
    now = datetime.now()
    return now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)


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
    ):
        self.page = page
        self.sender = sender
        self.timestamp = timestamp
        self.text = text
        self.container = container
        self.is_outgoing = is_outgoing
        self.msg_id = msg_id

    @classmethod
    async def from_element(cls, elem: ElementHandle, page: Page) -> Optional["Message"]:
        """
        Create a Message instance from a DOM element.

        Args:
            elem: The message container element.
            page: The Playwright page.

        Returns:
            A new Message instance or None if parsing fails.
        """
        try:
            # 0) ID if exists
            msg_id = (await elem.get_attribute("data-id")) or ""
            testid = (await elem.get_attribute("data-testid")) or ""

            # 1) Sender + Timestamp: ambos desde data-pre-plain-text
            #    Formato: "[HH:MM(:SS)?] Sender Name: message text"
            sender = ""
            timestamp = datetime.now()
            pre_plain = await elem.query_selector('[data-pre-plain-text]')
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

            # Direction (in/out): WhatsApp Web ya no usa conv-msg-right/left.
            # "Tú" es el sender de mensajes salientes en español.
            is_outgoing = (sender == "Tú") or (not sender and testid.startswith("conv-msg-AC"))

            # 3) Text
            texto = ""
            selectable = await elem.query_selector(
                '[data-testid="selectable-text"]'
            )
            if selectable:
                raw_inner = await selectable.inner_text()
                if raw_inner:
                    lineas = raw_inner.split("\n")
                    if len(lineas) > 1 and (
                        lineas[0].strip().startswith(sender) or ":" in lineas[0]
                    ):
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

            # Take screenshot after hover
            # await self.container.screenshot(path="after_hover.png")
            # print("self.container: ", self.container)
            await asyncio.sleep(0.5)
            # input("presiona enter para continuar")

            # 2. Find reaction button
            reaction_bar = self.page.locator('[aria-label="Reaccionar"]')
            if not reaction_bar:
                # print("Error: No se encontró el botón '[aria-label="Reaccionar"]'.")
                return None
            await reaction_bar.click()

            # 3. Find "More reactions" button
            more_reactions_button_handle = self.page.locator(
                '[aria-label="Más reacciones"]'
            )
            if not more_reactions_button_handle:
                # print("Error: No se encontró el botón '[aria-label="Más reacciones"]'.")
                return None

            await more_reactions_button_handle.click()

            # 4. Find emoji in picker
            emoji_in_picker = self.page.locator(f'[data-emoji="{emoji}"]')

            # 5. Click emoji
            await emoji_in_picker.wait_for(state="visible", timeout=5000)
            await emoji_in_picker.click()

            # print(f"Successfully reacted with '{emoji}'")

        except Exception as e:
            print(f"An error occurred while reacting to message {self.msg_id}: {e}")


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
    ):
        super().__init__(page, sender, timestamp, text, container)
        self.filename = filename
        self.download_icon = download_icon

    @classmethod
    async def from_element(
        cls, elem: ElementHandle, page: Page
    ) -> Optional["FileMessage"]:
        """
        Create a FileMessage from a DOM element.

        Checks for the presence of a download icon and attempts to parse the filename.

        Args:
            elem: The message container element.
            page: The Playwright page.

        Returns:
            A new FileMessage instance or None if not a valid file message.
        """
        try:
            # 1) Check for download icon
            icon = await elem.query_selector('span[data-icon="audio-download"]')
            if not icon:
                return None

            # 2) Find filename
            filename = ""
            title_handle = await icon.evaluate_handle(
                """
                (node) => {
                    let curr = node;
                    while (curr) {
                        if (curr.title && curr.title.startsWith("Download")) {
                            return curr;
                        }
                        curr = curr.parentElement;
                    }
                    return null;
                }
            """
            )

            if title_handle:
                title_elem: ElementHandle = title_handle.as_element()
                if title_elem:
                    raw_title = await title_elem.get_attribute("title")
                    if raw_title and '"' in raw_title:
                        parts = raw_title.split('"')
                        if len(parts) >= 2:
                            filename = parts[1].strip()

            if not filename:
                return None

            # 3) Extract base message data
            base_msg = await Message.from_element(elem, page)
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
    ):
        super().__init__(page, sender, timestamp, text, container)
        self.duration = duration

    @classmethod
    async def from_element(
        cls, elem: ElementHandle, page: Page
    ) -> Optional["VoiceMessage"]:
        """
        Create a VoiceMessage from a DOM element.

        Checks for voice message indicators (mic icon, voice container).

        Args:
            elem: The message container element.
            page: The Playwright page.

        Returns:
            A new VoiceMessage instance or None if not a valid voice message.
        """
        try:
            is_quoted = await elem.query_selector('[aria-label="Mensaje citado"]')
            if is_quoted:
                return None

            has_play_button = await elem.query_selector(
                'button[aria-label*="voz"], button[aria-label*="voice" i]'
            )
            has_voice_container = await elem.query_selector(
                'span[aria-label*="voz"], span[aria-label*="voice" i]'
            )

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

            base_msg = await Message.from_element(elem, page)
            if not base_msg:
                return None

            return cls(
                page=page,
                sender=base_msg.sender,
                timestamp=base_msg.timestamp,
                text=base_msg.text,
                container=elem,
                duration=duration,
            )

        except Exception:
            return None

    async def download_via_play(
        self, page: Page, downloads_dir: Path
    ) -> Optional[Path]:
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

            play_button = await self.container.query_selector(
                'button[aria-label="Reproducir mensaje de voz"]'
            )
            if not play_button:
                return None

            await play_button.click()
            await asyncio.sleep(1)

            download_icon = await self.container.query_selector(
                'span[data-icon="audio-download"]'
            )
            if not download_icon:
                return None

            async with page.expect_download() as evento:
                await download_icon.click()
            descarga: Download = await evento.value

            filename = (
                descarga.suggested_filename
                or f"voice_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.ogg"
            )
            destino = downloads_dir / filename

            await descarga.save_as(str(destino))
            return destino

        except Exception:
            return None

    async def download_via_context_menu(
        self, page: Page, downloads_dir: Path
    ) -> Optional[Path]:
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
                        "VoiceMessage.download_via_context_menu: "
                        "no target element found for msg %s",
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

            filename = (
                download.suggested_filename
                or f"voice_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.ogg"
            )
            destino = downloads_dir / filename

            await download.save_as(str(destino))
            return destino

        except Exception:
            return None

    async def download_via_blob(
        self, page: Page, downloads_dir: Path
    ) -> Optional[Path]:
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

    async def _download_blob_audio(
        self, page: Page, blob_url: str, destino: Path
    ) -> Optional[Path]:
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

    async def _download_url_audio(
        self, page: Page, audio_url: str, destino: Path
    ) -> Optional[Path]:
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
