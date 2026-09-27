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

from .constants import locator as loc
from .logging_setup import get_logger

logger = get_logger(__name__)
from .constants.states import State
from .filters import MessageFilter


class WhatsAppElements:
    """Helper class for interacting with WhatsApp Web elements"""

    def __init__(self, page: Page):
        self.page = page
        self._search_active = False

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
        """Return a search editor without falling back to the chat composer."""
        for selector in loc.SEARCH_TEXT_BOX:
            try:
                element = await self.wait_for_selector(selector, timeout=timeout)
                if element:
                    return element
            except Exception:
                continue
        return None

    async def click_search_button(self) -> bool:
        """Activa el campo de búsqueda (click o foco en el input siempre visible)"""
        try:
            # En la nueva WhatsApp Web (2026), el search es un <input> siempre visible.
            # Intentamos hacerle click directamente.
            search_input_selectors = [
                "input[aria-label='Buscar un chat o iniciar uno nuevo']",
                "input[aria-label='Search for a chat or start a new one']",
                "input[aria-label*='Buscar' i]",
                "input[aria-label*='Search' i]",
            ]
            for sel in search_input_selectors:
                try:
                    inp = await self.page.wait_for_selector(sel, timeout=3000, state="visible")
                    if inp:
                        await inp.click()
                        await asyncio.sleep(0.3)
                        self._search_active = True
                        return True
                except Exception:
                    continue

            # Fallback: intentar con los selectores de locator.py
            for selector in loc.SEARCH_BUTTON:
                try:
                    element = await self.page.wait_for_selector(
                        selector, timeout=2000, state="visible"
                    )
                    if element:
                        await element.click()
                        self._search_active = True
                        return True
                except Exception:
                    continue

            # Último recurso: atajos de teclado
            shortcuts = [
                "Control+/",
                "Control+Alt+/",
                "Control+f",
                "/",
            ]
            for shortcut in shortcuts:
                try:
                    await self.page.keyboard.press(shortcut)
                    await asyncio.sleep(0.5)
                    self._search_active = True
                    return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.warning(f"Error clicking search button: {e}")
            return False

    async def verify_search_active(self) -> bool:
        """Return whether search is active, not merely visible in the DOM."""
        if self._search_active:
            return True
        try:
            focused_search = await self.page.evaluate(
                """() => {
                    const active = document.activeElement;
                    if (!active) return false;
                    const text = [
                        active.getAttribute('aria-label'),
                        active.getAttribute('placeholder'),
                        active.getAttribute('title'),
                    ].filter(Boolean).join(' ').toLowerCase();
                    if (active.tagName === 'INPUT') {
                        return text.includes('search') || text.includes('buscar');
                    }
                    if (active.getAttribute('contenteditable') === 'true') {
                        return text.includes('search') || text.includes('buscar');
                    }
                    return false;
                }"""
            )
            if focused_search is True:
                self._search_active = True
                return True
            return False
        except Exception:
            return False

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
        """Close only an active search, without bubbling Escape to the chat."""
        if not await self.verify_search_active():
            return False

        search_box = await self._get_search_box(timeout=1000)
        if search_box:
            try:
                await search_box.press("Escape")
                self._search_active = False
                return True
            except Exception:
                pass

        for selector in loc.SEARCH_CLOSE_BUTTON:
            try:
                close_button = await self.wait_for_selector(selector, timeout=1000)
                if close_button:
                    await close_button.click()
                    self._search_active = False
                    return True
            except Exception:
                continue

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
            # Cerrar búsqueda
            try:
                if close:
                    await self.close_search()
            except:
                pass

        return results

    async def open(self, chat_name: str, timeout: int = 10000, open_via_url: bool = False) -> bool:
        """
        Abre un chat por su nombre visible o número. Si no está visible, lo busca.
        """
        import time as _time
        _t0 = _time.time()
        def _log(msg: str) -> None:
            elapsed = _time.time() - _t0
            logger.info(f"[open:{elapsed:.2f}s] {msg}")

        _log(f"inicio: chat_name='{chat_name}' timeout={timeout}")

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
                if invalid_warning and await invalid_warning.is_visible():
                    _log("numero invalido detectado")
                    return False
                _log("chat abierto via URL OK")
                return True
            except PlaywrightTimeoutError:
                _log(f"TIMEOUT via URL")
                return False
            except Exception as e:
                _log(f"EXCEPTION via URL: {e}")
                return False

        span_xpath = (
            f"//div[@role='row']//div[@data-testid='cell-frame-title']"
            f"//span[contains(@title, {repr(chat_name)})]"
        )

        try:
            chat_element = await self.page.query_selector(f"xpath={span_xpath}")
            _log(f"query_selector directo: {'encontrado' if chat_element else 'no encontrado'}")

            if chat_element:
                await chat_element.click()
                self._search_active = False
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
                _log("texto tipeado en input de busqueda")

                # Wait for search spinner to detach from DOM.
                try:
                    await self.page.wait_for_selector("svg[role='status']", state="detached", timeout=10000)
                    _log("spinner detached from DOM")
                except PlaywrightTimeoutError:
                    _log("timeout waiting for spinner, continuing")

                await asyncio.sleep(1)

                _log("esperando SEARCH_ITEM...")
                results = await self.page.wait_for_selector(loc.SEARCH_ITEM, timeout=5000)
                _log(f"SEARCH_ITEM: {results is not None}")
                if not results:
                    raise Exception("No se encontraron resultados de busqueda")

                await asyncio.sleep(1)
                chat_results = await self.page.query_selector_all(loc.SEARCH_ITEM)
                _log(f"chat_results count={len(chat_results)}")

                found = False
                for chat in chat_results:
                    title_el = await chat.query_selector(f"xpath={loc.SPAN_TITLE}")
                    if title_el:
                        title = await title_el.get_attribute("title")
                        if title and chat_name.lower() in title.lower():
                            _log(f"clickeando chat: {title}")
                            await chat.click()
                            self._search_active = False
                            found = True
                            break
                if not found:
                    _log("chat no encontrado en results, usando ArrowDown+Enter")
                    await self.page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.5)
                    await self.page.keyboard.press("Enter")
                    self._search_active = False

            _log(f"esperando CHAT_INPUT_BOX (timeout={timeout}ms)...")
            await self.page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=timeout)
            _log("CHAT_INPUT_BOX encontrado, SUCCESS")
            return True

        except PlaywrightTimeoutError:
            _log("TIMEOUT esperando CHAT_INPUT_BOX")
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
            if not self.open(group_name, timeout=5000):
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
