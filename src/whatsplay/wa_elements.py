"""
Utilities for interacting with WhatsApp Web elements
"""

import asyncio
import datetime
from typing import Optional, List, Dict, Any
from playwright.async_api import (
    Page,
    ElementHandle,
    TimeoutError as PlaywrightTimeoutError,
)
import re
import unicodedata

from .constants import locator as loc
from .logging_setup import get_logger
from .object.message import _safe_dispose

logger = get_logger(__name__)
from .constants.states import State
from .filters import MessageFilter

_PHONE_TITLE = re.compile(r"^\+?[\d\s().-]{7,}$")

# Seconds to wait for the header/composer to switch to the clicked chat.
ACTIVE_CHAT_SETTLE_SECS = 3.0
# Seconds to wait for a typed search to show the requested chat.
SEARCH_RESULTS_WAIT_SECS = 8.0


def normalize_chat_title(title: str) -> str:
    """Canonical form used to decide whether two chat titles are the same chat.

    Phone numbers compare by digits only ("+54 9 2234 48-0402" == "5492234480402").
    Names compare without accents, case or repeated spaces, and without the "~"
    WhatsApp puts before unsaved push names. Partial matches never count:
    "Cliente" and "Cliente (pruebas)" are different chats.
    """
    text = unicodedata.normalize("NFKD", title or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.strip().lstrip("~").strip()
    if _PHONE_TITLE.match(text):
        return re.sub(r"\D", "", text)
    return " ".join(text.casefold().split())


def same_chat(a: str, b: str) -> bool:
    """Whether two chat titles name the same chat (exact, after normalizing).

    Phones must carry the same full digit string: a local number such as
    "2235988856" is also a suffix of numbers in other countries, so it never
    matches "+54 9 2235 98-8856".
    """
    na, nb = normalize_chat_title(a), normalize_chat_title(b)
    return bool(na) and na == nb


def parse_composer_label(label: Optional[str]) -> Optional[tuple]:
    """Split a composer aria-label into (kind, title), kind being "group" or "chat".

    Returns None for any label that is not a known chat composer (a caption
    box, a search editor, an unknown UI language).
    """
    if not isinstance(label, str):
        return None
    for kind, prefix in loc.COMPOSER_LABEL_PREFIXES:
        if label.startswith(prefix):
            title = label[len(prefix):].strip()
            return (kind, title) if title else None
    return None


class WhatsAppElements:
    """Helper class for interacting with WhatsApp Web elements"""

    def __init__(self, page: Page):
        self.page = page
        self._search_active = False
        # Title of the chat the last successful open() verified. Opening by
        # URL names a phone, but a saved contact is shown by name.
        self.last_opened_title: Optional[str] = None

    async def get_state(self) -> Optional[State]:
        """
        Determina el estado actual de WhatsApp Web basado en los elementos visibles.

        El orden es critico: LOADING y QR se checkean ANTES que LOGGED_IN porque
        comparten elementos visibles (wa-wordmark aparece en QR y loading screen).
        """
        try:
            # Orden: LOADING > QR_AUTH > LOADING_CHATS > AUTH > LOGGED_IN
            # Todos los estados van a DEBUG: get_state() corre en cada tick del
            # poller (cada ~2s), así que loguearlos a nivel INFO generaba
            # ~217k líneas/día de ruido. Activá whatsplay.wa_elements=DEBUG
            # para verlos.
            if await self.page.locator(loc.LOADING).is_visible():
                logger.debug("state=LOADING")
                return State.LOADING
            elif await self.page.locator(loc.QR_CODE).is_visible():
                logger.debug("state=QR_AUTH")
                return State.QR_AUTH
            elif await self.page.locator(loc.LOADING_CHATS).is_visible():
                logger.debug("state=LOADING_CHATS")
                return State.LOADING
            elif await self.page.locator(loc.AUTH).is_visible():
                logger.debug("state=AUTH")
                return State.AUTH
            elif await self.page.locator(loc.LOGGED_IN).is_visible():
                # Confirmar que tambien esta el chat list (distinguir de QR screen)
                if await self.page.locator("[data-testid='chat-list']").is_visible():
                    logger.debug("state=LOGGED_IN")
                    return State.LOGGED_IN
            return None
        except Exception:
            return None

    async def wait_for_selector(
        self, selector: str, timeout: int = 5000, state: str = "visible"
    ) -> Optional[ElementHandle]:
        """
        Espera por un elemento y lo retorna cuando está disponible
        """
        try:
            element = await self.page.wait_for_selector(
                selector, timeout=timeout, state=state
            )
            return element
        except PlaywrightTimeoutError:
            return None

    async def _get_search_box(self, timeout: int = 2000) -> Optional[ElementHandle]:
        """Return the side-pane search input, never the chat composer."""
        for selector in loc.SEARCH_TEXT_BOX:
            try:
                element = await self.wait_for_selector(selector, timeout=timeout)
                if element:
                    return element
            except Exception:
                continue
        return None

    async def _search_query(self) -> Optional[str]:
        """Current text in the search input, or None if the input is missing."""
        try:
            return await self.page.evaluate(
                "(sel) => { const i = document.querySelector(sel); return i ? i.value : null; }",
                loc.SEARCH_TEXT_BOX[0],
            )
        except Exception:
            return None

    async def click_search_button(self) -> bool:
        """Focus the side-pane search input.

        No keyboard-shortcut fallback: a shortcut that does nothing would
        leave focus wherever it was (possibly the chat composer) and the
        query would be typed there.
        """
        box = await self._get_search_box(timeout=3000)
        if not box:
            logger.warning("Search input not found")
            return False
        try:
            await box.click()
            self._search_active = True
            return True
        except Exception as e:
            logger.warning(f"Error focusing the search input: {e}")
            return False
        finally:
            await _safe_dispose(box)

    async def verify_search_active(self) -> bool:
        """Whether a search is in progress: the search input holds text.

        Read from the DOM every time; a cached flag drifts from the page.
        """
        query = await self._search_query()
        active = bool(query)
        self._search_active = active
        return active

    async def prepare_search(self) -> Optional[ElementHandle]:
        """Select All/Todos, activate search, and return its input."""
        if await self.verify_search_active() and not await self.close_search():
            return None

        if not await self.click_chat_filter("all"):
            return None

        if not await self.click_search_button():
            return None

        search_box = await self._get_search_box()
        if not search_box:
            await self.close_search()
            self._search_active = False
            return None

        self._search_active = True
        return search_box

    async def close_search(self) -> bool:
        """Close the search and verify it closed. True when no search remains.

        Escape is pressed on the search input itself (verified live: it clears
        the query and keeps the open chat); the clear button is the fallback.
        """
        if not await self.verify_search_active():
            return True

        search_box = await self._get_search_box(timeout=1000)
        if search_box:
            try:
                await search_box.press("Escape")
            except Exception:
                pass
            finally:
                await _safe_dispose(search_box)
            if not await self.verify_search_active():
                return True

        for selector in loc.SEARCH_CLOSE_BUTTON:
            close_button = await self.wait_for_selector(selector, timeout=1000)
            if close_button:
                try:
                    await close_button.click()
                except Exception:
                    pass
                finally:
                    await _safe_dispose(close_button)
                if not await self.verify_search_active():
                    return True

        logger.warning("Search could not be closed; query still %r", await self._search_query())
        return False

    async def get_qr_code(self) -> Optional[bytes]:
        """
        Obtiene la imagen del código QR si está disponible
        """
        try:
            qr_element = await self.wait_for_selector(loc.QR_CODE)
            if qr_element:
                return await qr_element.screenshot()
            return None
        except Exception:
            return None

    async def search_chats(self, query: str, close=True) -> List[Dict[str, Any]]:
        """Busca chats usando un término y retorna los resultados"""
        results = []
        
        try:
            search_box = await self.prepare_search()
            if not search_box:
                return results

            # Escribir consulta con reintento
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    await search_box.click()
                    await search_box.fill("")
                    await search_box.type(query, delay=100)
                    break
                except Exception as e:
                    if attempt == max_attempts - 1:
                        return results

            # Esperar resultados
            results_container = await self.wait_for_selector(
                loc.SEARCH_RESULT, timeout=5000
            )
            if not results_container:
                logger.info("No search results found")
                return results

            # Obtener y procesar resultados
            items = await self.page.locator(loc.SEARCH_ITEM).all()
            for item in items:
                text = await item.inner_text()
                if text:
                    formatted = MessageFilter.filter_search_result(text)
                    results.append(formatted)

        except Exception as e:
            logger.warning(f"Error searching chats: {e}")
        finally:
            # Release the query handle and close the search.
            try:
                await _safe_dispose(results_container)
            except NameError:
                pass
            try:
                await _safe_dispose(search_box)
            except NameError:
                pass
            try:
                if close:
                    await self.close_search()
            except:
                pass

        return results

    async def dismiss_blocking_dialog(self) -> bool:
        """Close a modal dialog that intercepts clicks. True when none remains.

        Only the dialog's own close (X) button is used; a dialog without one is
        left alone, since its other buttons may confirm something.
        """
        try:
            if await self.page.locator(loc.BLOCKING_DIALOG).count() == 0:
                return True
            close = self.page.locator(loc.DIALOG_CLOSE_BUTTON)
            if await close.count() == 0:
                logger.warning("A modal dialog blocks the page and has no close button")
                return False
            await close.first.click()
            await asyncio.sleep(0.5)
            if await self.page.locator(loc.BLOCKING_DIALOG).count() == 0:
                logger.info("Dismissed a blocking dialog")
                return True
            logger.warning("A modal dialog is still open after clicking its close button")
            return False
        except Exception as e:
            logger.warning(f"Could not dismiss a blocking dialog: {e}")
            return False

    async def active_chat(self) -> Optional[tuple]:
        """(kind, title) of the open chat; kind is "group", "chat" or None.

        Read from the open composer's aria-label ("Escribir un mensaje para X"),
        with the header title as a read-only fallback (kind None).
        """
        try:
            info = await self.page.evaluate(
                """([composerSel, headerSel]) => {
                    const composer = document.querySelector(composerSel);
                    const header = document.querySelector(headerSel);
                    return {
                        composer: composer ? composer.getAttribute('aria-label') : null,
                        header: header ? header.textContent : null,
                    };
                }""",
                [loc.ACTIVE_CHAT_COMPOSER, loc.ACTIVE_CHAT_HEADER_TITLE],
            )
        except Exception:
            return None
        if not isinstance(info, dict):
            return None

        parsed = parse_composer_label(info.get("composer"))
        if parsed:
            return parsed
        header = info.get("header")
        if isinstance(header, str) and header.strip():
            return (None, header.strip())
        return None

    async def active_chat_title(self) -> Optional[str]:
        """Title of the open chat, or None if no chat is open."""
        active = await self.active_chat()
        return active[1] if active else None

    async def is_active_chat(self, chat_name: str, is_group: Optional[bool] = None) -> bool:
        """Whether the open chat is exactly `chat_name`.

        With is_group set, a group and a contact that share a title are told
        apart; when the kind cannot be read the check fails closed.
        """
        active = await self.active_chat()
        if active is None or not same_chat(active[1], chat_name):
            return False
        if is_group is None:
            return True
        return active[0] == ("group" if is_group else "chat")

    async def _wait_until_active(self, chat_name: str, is_group: Optional[bool] = None) -> bool:
        """Give WhatsApp a moment to switch panes after a click, then verify."""
        deadline = asyncio.get_running_loop().time() + ACTIVE_CHAT_SETTLE_SECS
        while True:
            if await self.is_active_chat(chat_name, is_group):
                return True
            if asyncio.get_running_loop().time() >= deadline:
                return False
            await asyncio.sleep(0.3)

    async def _wait_for_contact_chat(self) -> Optional[str]:
        """Title of the open contact chat once its composer is labelled, else None."""
        deadline = asyncio.get_running_loop().time() + ACTIVE_CHAT_SETTLE_SECS
        while True:
            active = await self.active_chat()
            if active and active[0] == "chat":
                return active[1]
            if asyncio.get_running_loop().time() >= deadline:
                return None
            await asyncio.sleep(0.3)

    async def _listed_matches(self, chat_name: str) -> tuple:
        """(matching cells, all cells) of side-pane rows titled exactly `chat_name`.

        The caller must dispose every cell in the second list.
        """
        cells = await self.page.query_selector_all(f"xpath={loc.CHAT_LIST_TITLES}")
        matches = []
        for cell in cells:
            title = await cell.get_attribute("title")
            if isinstance(title, str) and same_chat(title, chat_name):
                matches.append(cell)
        return matches, cells

    async def _click_listed_chat(self, chat_name: str, wait_secs: float = 0.0) -> Optional[bool]:
        """Click the only side-pane row titled exactly `chat_name`.

        Returns True when clicked, False when no row matches, and None when
        several rows match: picking one would be a guess, so nothing is clicked.
        With `wait_secs`, waits for the row to show up (search results render
        progressively) and only clicks once two consecutive reads agree on a
        single match, so a duplicate that is still rendering is not missed.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + wait_secs
        previous = None
        while True:
            matches, cells = await self._listed_matches(chat_name)
            try:
                count = len(matches)
                if count > 1:
                    logger.error(
                        "%d listed chats are titled %r; refusing to pick one", count, chat_name
                    )
                    return None
                settled = wait_secs <= 0 or previous == count
                if count == 1 and settled:
                    await matches[0].click()
                    self._search_active = False
                    return True
                if count == 0 and wait_secs <= 0:
                    return False
                if loop.time() >= deadline:
                    return False
                previous = count
            finally:
                for cell in cells:
                    await _safe_dispose(cell)
            await asyncio.sleep(0.3)

    async def open(
        self,
        chat_name: str,
        timeout: int = 10000,
        open_via_url: bool = False,
        is_group: Optional[bool] = None,
    ) -> bool:
        """
        Abre un chat por su nombre visible o número. Si no está visible, lo busca.

        Returns True only when the open chat is verifiably `chat_name` (and a
        group or a contact when `is_group` says so). It never falls back to
        "whatever comes first" and refuses titles shared by several chats.
        """
        import time as _time
        _t0 = _time.time()
        def _log(msg: str) -> None:
            elapsed = _time.time() - _t0
            logger.info(f"[open:{elapsed:.2f}s] {msg}")

        _log(f"inicio: chat_name='{chat_name}' timeout={timeout}")
        await self.dismiss_blocking_dialog()

        if open_via_url:
            numero_limpio = re.sub(r"\D", "", chat_name)
            url = f"https://web.whatsapp.com/send?phone={numero_limpio}"
            _log(f"abriendo por URL: {url}")
            try:
                await self.page.goto(url, timeout=60000)
                self._search_active = False
                await self.page.wait_for_selector(loc.LOGGED_IN, timeout=30000)
                _log("LOGGED_IN detectado tras navegacion")
                await self.page.wait_for_selector(
                    f"{loc.CHAT_INPUT_BOX}|{loc.INVALID_NUMBER_WARNING}",
                    timeout=timeout
                )
                invalid_warning = await self.page.query_selector(loc.INVALID_NUMBER_WARNING)
                try:
                    if invalid_warning and await invalid_warning.is_visible():
                        _log("numero invalido detectado")
                        return False
                finally:
                    await _safe_dispose(invalid_warning)
                # The URL already targets the phone; a saved contact is shown
                # by name, so verify it is a contact chat and remember its title.
                title = await self._wait_for_contact_chat()
                if title is None:
                    _log(f"tras URL no hay un chat de contacto abierto: {await self.active_chat()!r}")
                    return False
                self.last_opened_title = title
                _log(f"chat abierto via URL OK: {title!r}")
                return True
            except PlaywrightTimeoutError:
                _log(f"TIMEOUT via URL")
                return False
            except Exception as e:
                _log(f"EXCEPTION via URL: {e}")
                return False

        try:
            listed = await self._click_listed_chat(chat_name)
            if listed is None:
                _log("varios chats con ese título en la lista; no se abre ninguno")
                return False
            if listed:
                _log("click directo OK")
            else:
                _log("chat no visible, entrando a ruta de busqueda")
                await asyncio.sleep(2)
                search_box = await self.prepare_search()
                _log(f"search preparation: {search_box is not None}")
                if not search_box:
                    raise Exception("Input de busqueda no encontrado")

                await asyncio.sleep(1)
                await search_box.fill("")
                await asyncio.sleep(0.5)
                await search_box.type(chat_name, delay=100)
                # type() sends keys to whatever has focus; if focus moved while
                # typing, part of the query went elsewhere. Never search with it.
                typed = await search_box.input_value()
                if typed != chat_name:
                    _log(f"el buscador quedó con {typed!r}, no con la consulta; se aborta")
                    await self.close_search()
                    await _safe_dispose(search_box)
                    return False
                _log("texto tipeado en input de busqueda")
                await _safe_dispose(search_box)

                # Results render in the same side-pane grid as the chat list,
                # so the exact-title match is shared with the direct route.
                listed = await self._click_listed_chat(
                    chat_name, wait_secs=SEARCH_RESULTS_WAIT_SECS
                )
                if listed is not True:
                    _log("varios resultados con ese título" if listed is None
                         else "chat no encontrado en resultados; no se abre ningún otro")
                    await self.close_search()
                    return False
                _log(f"clickeando chat: {chat_name}")
                # Leave no query behind; Escape on the search input keeps the
                # opened chat (verified live).
                await self.close_search()

            _log(f"esperando ACTIVE_CHAT_COMPOSER (timeout={timeout}ms)...")
            await self.page.wait_for_selector(loc.ACTIVE_CHAT_COMPOSER, timeout=timeout)
            if not await self._wait_until_active(chat_name, is_group):
                _log(f"chat activo no es '{chat_name}': {await self.active_chat()!r}")
                return False
            self.last_opened_title = chat_name
            _log("chat verificado, SUCCESS")
            return True

        except PlaywrightTimeoutError:
            # Also reached when search results never appear: leave no query
            # behind in the search box.
            if self._search_active:
                await self.close_search()
            _log("TIMEOUT abriendo el chat")
            return False

        except Exception as e:
            if self._search_active:
                await self.close_search()
            _log(f"EXCEPTION: {type(e).__name__}: {e}")
            return False


    async def new_group(self, group_name: str, members: List[str]) -> Optional[ElementHandle]:
        logger.info(f"Creating new group: {group_name} with members: {members}")
        """
        Crea un nuevo grupo con el nombre especificado
        """
        try:
            # Hacer click en el botón de nuevo chat
            new_chat_button = await self.page.wait_for_selector(
                loc.NEW_CHAT_BUTTON, timeout=5000
            )
            if new_chat_button:
                await new_chat_button.click()
            new_group_button = await self.page.wait_for_selector(
                loc.NEW_GROUP_BUTTON, timeout=5000
            )
            if new_group_button:
                await new_group_button.click()
            # Esperar al campo de nombre del grupo
            member_name_input = await self.page.wait_for_selector(
                loc.INPUT_MEMBERS_GROUP, timeout=5000
            )
            if member_name_input:
                for name in members:
                    await member_name_input.fill(name)
                    await asyncio.sleep(0.5)  # Esperar un poco entre entradas
                    await self.page.keyboard.press("Enter")
                    
            enter_arrow = await self.page.wait_for_selector(
                "xpath=//span[@data-icon='arrow-forward']", timeout=5000
            )
            if enter_arrow:
                await enter_arrow.click()
                
            input_group_name = await self.page.wait_for_selector(
                loc.ENTER_GROUP_NAME, timeout=5000
            )
            if input_group_name:
                await input_group_name.fill(group_name)
                await self.page.keyboard.press("Enter")
            


        except PlaywrightTimeoutError:
            logger.warning("Timeout while trying to create a new group")
            return None
        except Exception as e:
            logger.warning(f"Error creating new group: {e}")
            return None
            
    async def add_members_to_group(
        self, group_name: str, members: List[str]
    ) -> bool:
        """
        Agrega miembros a un grupo existente. Asume que el chat del grupo ya está abierto.
        """
        try:
            if not await self.open(group_name, timeout=5000, is_group=True):
                logger.warning(f"❌ No se pudo abrir el grupo '{group_name}'")
                return False
            
            # 2. Hacer clic en la cabecera para abrir la info del grupo
            header = await self.page.wait_for_selector(loc.GROUP_INFO_BUTTON, timeout=5000)
            await header.click()

            # 2. Buscar y hacer clic en el botón "Add participant"
            # Usamos un selector de texto porque es más robusto
            add_participant_button = await self.page.wait_for_selector(
                loc.ADD_MEMBERS_BUTTON, timeout=5000
            )
            await add_participant_button.click()

            # 3. Agregar cada miembro
            member_input = await self.page.wait_for_selector(
                loc.INPUT_MEMBERS_GROUP, timeout=5000
            )
            for member in members:
                await member_input.fill(member)
                await asyncio.sleep(0.5)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(0.5)

            # 4. Confirmar la adición
            confirm_button = await self.page.wait_for_selector(
                loc.CONFIRM_ADD_MEMBERS_BUTTON, timeout=5000
            )
            await confirm_button.click()
            await asyncio.sleep(0.5)  # Esperar un poco para que se procese
            
            confirm_add_button = await self.page.wait_for_selector('//div[text()="Add member"]', timeout=3000)
            
            # Esperar un poco para que se procese y cerrar el panel
            await asyncio.sleep(1)
            await self.page.keyboard.press("Escape")
            return True

        except PlaywrightTimeoutError:
            logger.warning(f"Timeout al intentar agregar miembros a '{group_name}'")
            await self.page.keyboard.press("Escape") # Intentar limpiar
            return False
        except Exception as e:
            logger.warning(f"Error agregando miembros a '{group_name}': {e}")
            await self.page.keyboard.press("Escape") # Intentar limpiar
            return False
    async def del_member_group(self, group_name: str, member_name: str) -> bool:
        """
        Elimina un miembro de un grupo existente. Asume que el chat del grupo ya está abierto.
        """
        try:
            if not await self.open(group_name, timeout=5000):
                logger.warning(f"❌ No se pudo abrir el grupo '{group_name}'")
                return False

            # 1. Abrir info de grupo
            logger.debug(" 1. Esperando GROUP_INFO_BUTTON...")
            header = await self.page.wait_for_selector(loc.GROUP_INFO_BUTTON, timeout=5000)
            await header.click()

            # 2. Contenedor de info del grupo
            logger.debug(" 2. Esperando contenedor 'Group info'...")
            group_info = await self.page.wait_for_selector('div[aria-label="Group info"]', timeout=5000)
            if not group_info:
                logger.warning("❌ No se encontró el contenedor 'Group info'")
                return False

            # 3. Buscar el <span> del miembro por coincidencia parcial
            logger.debug(" 3. Buscando miembro por coincidencia parcial...")
            span_member = await group_info.evaluate_handle(
                f"""
                (container) => {{
                    const spans = Array.from(container.querySelectorAll('span[title]'));
                    return spans.find(s => s.textContent.trim().toLowerCase().includes("{member_name.lower()}")) || null;
                }}
                """
            )

            # ⚠️ Verificar si se encontró o no
            if not await span_member.evaluate("el => !!el"):
                logger.warning(f"❌ No se encontró el miembro '{member_name}'")
                return False

            # 4. Subir al contenedor general del miembro (div[role="button"])
            member_row = await span_member.evaluate_handle("el => el.closest('div[role=\"button\"]')")
            if not await member_row.evaluate("el => !!el"):
                logger.warning("⚠️ No se encontró el contenedor del miembro")
                return False

            # 5. Buscar el contenedor del status
            status_container = await member_row.evaluate_handle(
                """(row) => {
                    const divs = Array.from(row.querySelectorAll('div'));
                    return divs.find(div => {
                        const span = div.querySelector('span');
                        return span && span.getAttribute('title');
                    }) || null;
                }"""
            )
            if not await status_container.evaluate("el => !!el"):
                logger.warning("⚠️ No se encontró el contenedor del estado del miembro")
                return False

            # 6. Hover sobre el estado
            logger.debug(" 4. Hover sobre el estado...")
            await status_container.scroll_into_view_if_needed()
            await status_container.hover()
            logger.info(f"✅ Hover sobre el estado de '{member_name}'")

            # 7. Esperar botón de menú
            logger.debug(" 5. Esperando botón ⋮ ...")
            try:
                menu_btn = await self.page.wait_for_selector(
                    'button[aria-label="Open the chat context menu"]',
                    timeout=3000
                )
                await menu_btn.click()
                logger.info("✅ Menú contextual clickeado correctamente.")
            except Exception as e:
                logger.warning(f"❌ No se pudo hacer clic en el botón del menú: {e}")
                return False

            # 8. Clic en "Remove"
            remove_button = await self.page.wait_for_selector(loc.REMOVE_MEMBER_BUTTON, timeout=5000)
            await remove_button.click()
            await asyncio.sleep(0.5)

            # 9. Confirmar
            confirm_button = await self.page.wait_for_selector('//div[text()="Remove"]', timeout=3000)
            await confirm_button.click()
            await asyncio.sleep(0.5)

            logger.info(f"✅ Miembro '{member_name}' eliminado de '{group_name}'.")
            return True

        except PlaywrightTimeoutError:
            logger.warning(f"⏱️ Timeout al intentar eliminar miembro de '{group_name}'")
            await self.page.keyboard.press("Escape")
            return False
        except Exception as e:
            logger.warning(f"❌ Error eliminando miembro '{member_name}' de '{group_name}': {e}")
            await self.page.keyboard.press("Escape")
            return False

    async def click_chat_filter(self, filter_type: str) -> bool:
        """Hace click en los filtros de chat (Todos, Grupos, No leídos)"""
        labels = {
            "all": ("All", "Todos"),
            "groups": ("Grupos",),
            "unread": ("No leídos",),
        }
        label_options = labels.get(filter_type)
        if not label_options:
            return False

        def _has_text_selector(role: str) -> str:
            return ", ".join(
                f"button[role='{role}']:has-text('{label}')"
                for label in label_options
            )

        async def _click_tab() -> bool:
            tab = self.page.locator(_has_text_selector("tab"))
            if await tab.count() > 0 and await tab.first.is_visible():
                await tab.first.click()
                await asyncio.sleep(0.3)
                return True
            return False

        async def _click_dropdown() -> bool:
            more = self.page.locator("button#additional-filters")
            if await more.count() == 0:
                return False
            await more.first.click()
            await asyncio.sleep(0.3)
            item = self.page.locator(_has_text_selector("menuitem"))
            if await item.count() > 0:
                await item.first.click()
                await asyncio.sleep(0.3)
                return True
            return False

        async def _click_xpath_fallback() -> bool:
            xpath = {
                "all": loc.ALL_CHATS_BUTTON,
                "groups": loc.GROUPS_CHATS_BUTTON,
                "unread": loc.UNREAD_CHATS_BUTTON,
            }.get(filter_type)
            if not xpath:
                return False
            el = await self.wait_for_selector(xpath, timeout=3000)
            if el:
                await el.click()
                await asyncio.sleep(0.3)
                return True
            return False

        return await _click_tab() or await _click_dropdown() or await _click_xpath_fallback()
