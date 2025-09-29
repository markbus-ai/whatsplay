import re
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
import asyncio

from playwright.async_api import(
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError,
)

from .constants import locator as loc
from .object.message import Message, FileMessage


class ChatManager:
    def __init__(self, client):
        self.client = client
        self._page = client._page
        self.wa_elements = client.wa_elements
        
    import asyncio
    
    # Selectores estables del sidebar
    
    # Buscamos “unread” o “mensaje(s) no leído” en cualquier aria-label
    UNREAD_ARIA_REGEX_JS = r"(?:mensaje(?:s)?\s+no\s+le[ií]do|unread)"

    async def _check_unread_chats(self, debug: bool = True) -> List[Dict[str, Any]]:
        page = self._page
        unread_chats: List[Dict[str, Any]] = []
        await self.close()  # Asegura que no haya chat abierto
        
        

        def log(msg: str):
            if debug:
                print(msg)

        async def wait_for_grid():
            # Espera a que la grilla de chats esté presente (hidratación)
            try:
                await page.locator(loc.CHAT_LIST_GRID).wait_for(timeout=15000)
            except Exception:
                await page.wait_for_timeout(1000)

        async def get_scroller_handle():
            """Devuelve el ElementHandle del contenedor que realmente scrollea (lista virtualizada)."""
            grid = page.locator(loc.CHAT_LIST_GRID)
            grid_h = await grid.element_handle()
            if not grid_h:
                return await page.locator("#pane-side").element_handle()
            return await grid_h.evaluate_handle(
                """(el) => {
                    let cur = el;
                    while (cur && cur !== document.body) {
                    const s = getComputedStyle(cur);
                    if ((s.overflowY === 'auto' || s.overflowY === 'scroll') &&
                        cur.clientHeight < cur.scrollHeight) return cur;
                    cur = cur.parentElement;
                    }
                    return document.querySelector('#pane-side');
                }"""
            )

        async def row_is_unread(row_loc) -> bool:
            """
            Heurística robusta:
            1) aria-label con 'unread' o 'mensaje(s) no leído'
            2) badge específico (si existe en este build)
            3) título en negrita (font-weight >= 600 o 'bold')
            """
            try:
                # (1) cualquier aria-label que matchee ES/EN
                has_aria = await row_loc.locator("[aria-label]").evaluate_all(
                    "(els, rx) => els.some(el => (el.getAttribute('aria-label')||'').match(new RegExp(rx,'i')))",
                    self.UNREAD_ARIA_REGEX_JS,
                )
                if has_aria:
                    return True

                # (2) badge explícito (si existe en tu build)
                try:
                    if await row_loc.locator(f"xpath={loc.UNREAD_BADGE}").count() > 0:
                        return True
                except Exception:
                    pass

                # (3) título en negrita
                title = row_loc.locator(f"xpath={loc.SPAN_TITLE}")
                if await title.count() == 0:
                    return False
                is_bold = await title.evaluate(
                    """(el) => {
                        const w = getComputedStyle(el).fontWeight;
                        const n = parseInt(w, 10);
                        return isNaN(n) ? /bold/i.test(w) : n >= 600;
                    }"""
                )
                return bool(is_bold)
            except Exception:
                return False

        async def parse_row(row_loc):
            """Respeta tu misma estructura: delega al parser existente."""
            handle = await row_loc.element_handle()
            if not handle:
                return None
            return await self._parse_search_result(handle, "CHATS")

        try:
            # 0) UI lista
            await wait_for_grid()

            # 1) Debug inicial
            try:
                total_rows_now = await page.locator(f"xpath={loc.CHAT_LIST_ROWS}").count()
                log(f"DEBUG: filas visibles inicialmente: {total_rows_now}")
                if total_rows_now <= 2:
                    await page.locator(loc.ALL_CHATS_BUTTON).click()  # reset focus
                    log("DEBUG: pocos chats visibles, forzando click en 'All'")
                    log("DEBUG: 2 o menos chats visibles, tomando captura.")
                    await self._page.screenshot(path="pocos_chats_visibles.png")
                
            except Exception:
                log("DEBUG: no pude contar filas inicialmente")

            # 2) Scroller correcto (lista virtualizada)
            scroller_h = await get_scroller_handle()

            # 3) Barrido de filas visibles
            async def sweep(tag: str):
                nonlocal unread_chats
                rows = page.locator(f"xpath={loc.CHAT_LIST_ROWS}")
                count = await rows.count()
                log(f"DEBUG: {tag}: filas visibles ahora: {count}")

                for i in range(count):
                    row = rows.nth(i)
                    try:
                        if await row_is_unread(row):
                            chat = await parse_row(row)
                            if chat:
                                unread_chats.append(chat)
                                log(f"✓ no leído ({tag}): {chat.get('name','Sin nombre')}")
                    except Exception as e:
                        log(f"DEBUG: error evaluando fila {i} ({tag}): {e}")

            # 4) Barrido inicial
            await sweep("inicio")
            
            # # 5) Scroll ida y vuelta con barridos intermedios
            # for pass_idx in range(2):  # down y up
            #     direction = "down" if pass_idx == 0 else "up"
            #     step = 900 if direction == "down" else -900
            #     log(f"DEBUG: scroll {direction}…")
            #     for k in range(6):
            #         await sweep(f"{direction}:{k}")
            #         try:
            #             await scroller_h.evaluate("(el, dy)=>el.scrollBy(0, dy)", step)
            #         except Exception:
            #             # fallback: rueda del mouse si evaluate falla
            #             await page.mouse.wheel(0, step)
            #         await asyncio.sleep(0.25)

            # # 6) Último barrido
            # await sweep("final")

            # 7) Deduplicado suave (si tu parser repite items)
            def key(ch: Dict[str, Any]):
                return ch.get("id") or (ch.get("name"), ch.get("last_message"), ch.get("last_activity"))

            seen = set()
            dedup = []
            for ch in unread_chats:
                k = key(ch)
                if k in seen:
                    continue
                seen.add(k)
                dedup.append(ch)
            unread_chats = dedup

        except Exception as e:
            await self.client.emit("on_warning", f"Error detectando no leídos: {e}")
            log(f"DEBUG: Error general: {e}")

        # 8) Resumen final
        log("\nDEBUG: ===== RESUMEN =====")
        log(f"Total chats no leídos encontrados: {len(unread_chats)}")
        for i, chat in enumerate(unread_chats):
            log(f"  {i+1}. {chat.get('name','Sin nombre')}")

        return unread_chats

    async def _parse_search_result(
        self, element, result_type: str = "CHATS"
    ) -> Optional[Dict[str, Any]]:
        try:
            components = await element.query_selector_all(
                "xpath=.//div[@role='gridcell' and @aria-colindex='2']/parent::div/div"
            )
            count = len(components)

            unread_el = await element.query_selector(
                f"xpath={loc.SEARCH_ITEM_UNREAD_MESSAGES}"
            )
            unread_count = await unread_el.inner_text() if unread_el else "0"
            mic_span = await components[1].query_selector('xpath=.//span[@data-icon="mic"]')
            
            if count == 3:
                span_title_0 = await components[0].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                group_title = (
                    await span_title_0.get_attribute("title") if span_title_0 else ""
                )

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = (
                    await datetime_children[1].text_content()
                    if len(datetime_children) > 1
                    else ""
                )

                span_title_1 = await components[1].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                title = (
                    await span_title_1.get_attribute("title") if span_title_1 else ""
                )

                info_text = (await components[2].text_content()) or ""
                info_text = info_text.replace("\n", "")

                if "loading" in info_text or "status-" in info_text or "typing" in info_text:
                    return None

                return {
                    "type": result_type,
                    "group": group_title,
                    "name": title,
                    "last_activity": datetime_text,
                    "last_message": info_text,
                    "last_message_type": "audio" if mic_span else "text",
                    "unread_count": unread_count,
                    "element": element,
                }

            elif count == 2:
                span_title_0 = await components[0].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                title = (
                    await span_title_0.get_attribute("title") if span_title_0 else ""
                )

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = (
                    await datetime_children[1].text_content()
                    if len(datetime_children) > 1
                    else ""
                )

                info_children = await components[1].query_selector_all("xpath=./*")
                info_text = (
                    await info_children[0].text_content()
                    if len(info_children) > 0
                    else ""
                ) or ""
                info_text = info_text.replace("\n", "")
                if "loading" in info_text or "status-" in info_text or "typing" in info_text:
                    return None

                return {
                    "type": result_type,
                    "name": title,
                    "last_activity": datetime_text,
                    "last_message": info_text,
                    "last_message_type": "audio" if mic_span else "text",
                    "unread_count": unread_count,
                    "element": element,
                    "group": None,
                }

            return None

        except Exception as e:
            print(f"Error parsing result: {e}")
            return None

    async def close(self):
        """Cierra el chat o la vista actual presionando Escape."""
        if self._page:
            try:
                await self._page.keyboard.press("Escape")
            except Exception as e:
                await self.client.emit(
                    "on_warning", f"Error trying to close chat with Escape: {e}"
                )

    async def open(
        self, chat_name: str, timeout: int = 10000, force_open: bool = False
    ) -> bool:
        return await self.wa_elements.open(chat_name, timeout, force_open)

    async def search_conversations(
        self, query: str, close=True
    ) -> List[Dict[str, Any]]:
        """Busca conversaciones por término"""
        if not await self.client.wait_until_logged_in():
            return []
        try:
            return await self.wa_elements.search_chats(query, close)
        except Exception as e:
            await self.client.emit("on_error", f"Search error: {e}")
            return []

    async def collect_messages(self) -> List[Union[Message, FileMessage]]:
        """
        Recorre todos los contenedores de mensaje (message-in/message-out) actualmente visibles
        y devuelve una lista de instancias Message o FileMessage.
        """
        resultados: List[Union[Message, FileMessage]] = []
        msg_elements = await self._page.query_selector_all(
            'div[class*="message-in"], div[class*="message-out"]'
        )

        for elem in msg_elements:
            file_msg = await FileMessage.from_element(elem)
            if file_msg:
                resultados.append(file_msg)
                continue

            simple_msg = await Message.from_element(elem)
            if simple_msg:
                resultados.append(simple_msg)

        return resultados

    async def download_all_files(self, carpeta: Optional[str] = None) -> List[Path]:
        """
        Llama a collect_messages(), filtra FileMessage y descarga cada uno.
        Devuelve lista de Path donde se guardaron.
        """
        if not await self.client.wait_until_logged_in():
            return []

        if carpeta:
            downloads_dir = Path(carpeta)
        else:
            downloads_dir = Path.home() / "Downloads" / "WhatsAppFiles"

        archivos_guardados: List[Path] = []
        mensajes = await self.collect_messages()
        for m in mensajes:
            if isinstance(m, FileMessage):
                ruta = await m.download(self._page, downloads_dir)
                if ruta:
                    archivos_guardados.append(ruta)
        return archivos_guardados

    async def download_file_by_index(
        self, index: int, carpeta: Optional[str] = None
    ) -> Optional[Path]:
        """
        Descarga sólo el FileMessage en la posición `index` de la lista devuelta
        por collect_messages() filtrando por FileMessage.
        """
        if not await self.client.wait_until_logged_in():
            return None

        if carpeta:
            downloads_dir = Path(carpeta)
        else:
            downloads_dir = Path.home() / "Downloads" / "WhatsAppFiles"

        mensajes = await self.collect_messages()
        archivos = [m for m in mensajes if isinstance(m, FileMessage)]
        if index < 0 or index >= len(archivos):
            return None

        return await archivos[index].download(self._page, downloads_dir)

    async def send_message(
        self, chat_query: str, message: str, force_open=True
    ) -> bool:
        """Envía un mensaje a un chat"""
        print("mandando mensaje...")
        if not await self.client.wait_until_logged_in():
            return False

        try:
            if force_open:
                opened = await self.open(chat_query)
                if not opened:
                    await self.client.emit("on_error", f"No se pudo abrir el chat: {chat_query}")
                    return False
                print(f"✅ Chat '{chat_query}' abierto directamente enviando mensaje")
            await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)
            input_box = await self._page.wait_for_selector(
                loc.CHAT_INPUT_BOX, timeout=10000
            )
            if not input_box:
                await self.client.emit(
                    "on_error",
                    "No se encontró el cuadro de texto para enviar el mensaje",
                )
                return False

            await input_box.click()
            await input_box.fill(message)
            await self._page.keyboard.press("Enter")
            return True

        except Exception as e:
            await self._page.screenshot(path="send_message_error.png")
            await self.client.emit("on_error", f"Error al enviar el mensaje: {e}")
            return False
        finally:
            await self.close()

    async def send_file(self, chat_name, path):
        """Envía un archivo a un chat especificado en WhatsApp Web usando Playwright"""
        try:
            if not os.path.isfile(path):
                msg = f"El archivo no existe: {path}"
                await self.client.emit("on_error", msg)
                return False

            if not await self.client.wait_until_logged_in():
                msg = "No se pudo iniciar sesión"
                await self.client.emit("on_error", msg)
                return False

            if not await self.open(chat_name):
                msg = f"No se pudo abrir el chat: {chat_name}"
                await self.client.emit("on_error", msg)
                return False

            await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)

            attach_btn = await self._page.wait_for_selector(
                loc.ATTACH_BUTTON, timeout=5000
            )
            await attach_btn.click()

            input_files = await self._page.query_selector_all(loc.FILE_INPUT)
            if not input_files:
                msg = "No se encontró input[type='file']"
                await self.client.emit("on_error", msg)
                return False

            await input_files[0].set_input_files(path)
            await self.client.asyncio.sleep(1)

            send_btn = await self._page.wait_for_selector(
                loc.SEND_BUTTON, timeout=10000
            )
            await send_btn.click()

            return True

        except Exception as e:
            msg = f"Error inesperado en send_file: {str(e)}"
            await self.client.emit("on_error", msg)
            await self._page.screenshot(path="send_file_error.png")
            return False
        finally:
            await self.close()

    async def new_group(self, group_name: str, members: list[str]):
        return await self.wa_elements.new_group(group_name, members)

    async def add_members_to_group(self, group_name: str, members: list[str]) -> bool:
        """
        Abre un grupo y le añade nuevos miembros.
        """
        try:
            # 1. Abrir el chat del grupo
            if not await self.open(group_name):
                await self.client.emit("on_error", f"No se pudo abrir el grupo '{group_name}'")
                return False

            # 2. Llamar al método de bajo nivel para agregar miembros
            success = await self.wa_elements.add_members_to_group(group_name, members)
            return success

        except Exception as e:
            await self.client.emit("on_error", f"Error al añadir miembros al grupo '{group_name}': {e}")
            return False
