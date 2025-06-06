import asyncio
import time
from typing import Optional, Dict, List, Any, Union
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from .base_client import BaseWhatsAppClient
from .wa_elements import WhatsAppElements
from .utils import show_qr_window, copy_file_to_clipboard
from .constants.states import State
from .constants import locator as loc
from .object.message import Message, FileMessage
import datetime

class Client(BaseWhatsAppClient):
    """
    Cliente de WhatsApp Web implementado con Playwright
    """
    def __init__(self,
                 user_data_dir: Optional[str] = None,
                 headless: bool = False,
                 locale: str = 'en-US',
                 auth: Optional[Any] = None):
        super().__init__(user_data_dir=user_data_dir, headless=headless, auth=auth)
        self.locale = locale
        self.poll_freq = 0.25
        self.wa_elements = None
        self.qr_task = None
        self.current_state = None
        self.unread_messages_sleep = 1  # Tiempo de espera para cargar mensajes no leídos

    @property
    def running(self) -> bool:
        """Check if client is running"""
        return getattr(self, '_is_running', False)

    async def stop(self) -> None:
        self._is_running = False
        try:
            if hasattr(self, '_browser') and self._browser:
                await self._browser.close()
                self._browser = None
        except Exception as e:
            await self.emit("on_error", f"Error al cerrar el navegador: {e}")
        await self.emit("on_stop")

    async def start(self) -> None:
        """Inicia el cliente y maneja el ciclo principal"""
        await super().start()
        self.wa_elements = WhatsAppElements(self._page)
        self._is_running = True
        
        # Iniciar el ciclo principal
        try:
            await self._main_loop()
        finally:
            await self.stop()

    async def _main_loop(self) -> None:
        """Implementación del ciclo principal con Playwright"""
        await self.emit("on_start")
        await self._page.screenshot(path="init_main.png", full_page=True)
        asyncio.create_task(self._auto_screenshot_loop(interval=30))

        qr_binary = None
        state = None
        last_qr_shown = None  # Guarda la última imagen QR mostrada

        while self.running:
            curr_state = await self._get_state()
            self.current_state = curr_state  # Actualizar la propiedad current_state

            if curr_state is None:
                await asyncio.sleep(self.poll_freq)
                continue

            if curr_state != state:
                if curr_state == State.AUTH:
                    await self.emit("on_auth")

                elif curr_state == State.QR_AUTH:
                    try:
                        qr_code_canvas = await self._page.wait_for_selector(loc.QR_CODE, timeout=5000)
                        qr_binary = await self._extract_image_from_canvas(qr_code_canvas)

                        # Mostrar solo si la imagen QR es distinta a la última mostrada
                        if qr_binary != last_qr_shown:
                            show_qr_window(qr_binary)
                            last_qr_shown = qr_binary

                        await self.emit("on_qr", qr_binary)
                    except PlaywrightTimeoutError:
                        pass

                elif curr_state == State.LOADING:
                    loading_chats = await self._is_present(loc.LOADING_CHATS)
                    await self.emit("on_loading", loading_chats)

                elif curr_state == State.LOGGED_IN:
                    await self.emit("on_logged_in")

                    # Buscar y hacer clic en botón "Continue" si aparece
                    try:
                        continue_button = await self._page.query_selector("button:has(div:has-text('Continue'))")
                        if continue_button:
                            await continue_button.click()
                            await asyncio.sleep(1)  # Esperar a que se actualice la interfaz
                    except Exception as e:
                        await self.emit("on_error", f"⚠️ Error al hacer clic en 'Continue': {e}")


            else:
                if curr_state == State.QR_AUTH:
                    try:
                        qr_code_canvas = await self._page.query_selector(loc.QR_CODE)
                        if qr_code_canvas:
                            curr_qr_binary = await self._extract_image_from_canvas(qr_code_canvas)

                            # Mostrar solo si la imagen QR cambió respecto a la última mostrada
                            if curr_qr_binary != last_qr_shown:
                                show_qr_window(curr_qr_binary)
                                last_qr_shown = curr_qr_binary
                                await self.emit("on_qr_change", curr_qr_binary)
                    except Exception:
                        pass

                elif curr_state == State.LOGGED_IN:
                    unread_chats = []
                    try:
                        continue_button = await self._page.query_selector("button:has(div:has-text('Continue'))")
                        if continue_button:
                            await self.emit("on_debug", "🟢 Botón 'Continue' detectado. Haciendo clic...")
                            await continue_button.click()
                            await asyncio.sleep(2)  # Esperar a que se actualice la interfaz
                    except Exception as e:
                        await self.emit("on_error", f"⚠️ Error al hacer clic en 'Continue': {e}")
                    try:
                        unread_button = await self._page.query_selector(loc.UNREAD_CHATS_BUTTON)
                        if unread_button:
                            await unread_button.click()
                            await asyncio.sleep(self.unread_messages_sleep)

                            chat_list = await self._page.query_selector_all(loc.UNREAD_CHAT_DIV)
                            if chat_list and len(chat_list) > 0:
                                chats = await chat_list[0].query_selector_all(loc.SEARCH_ITEM)
                                for chat in chats:
                                    inner_text = await chat.inner_text()
                                    chat_result = await self._parse_search_result(chat, "CHATS")
                                    if chat_result:
                                        unread_chats.append(chat_result)
                                        await self.emit("on_unread_chat", [chat_result])

                        all_button = await self._page.query_selector(loc.ALL_CHATS_BUTTON)
                        if all_button:
                            await all_button.click()

                    except Exception as e:
                        await self.emit("on_error", f"Error checking unread chats: {e} ({type(e)})")

            await self.emit("on_tick")
            await asyncio.sleep(self.poll_freq)


    async def _get_state(self) -> Optional[State]:
        """Obtiene el estado actual de WhatsApp Web"""
        return await self.wa_elements.get_state()
    
    async def open(self, chat_name: str, close = True) -> bool:
        try:
            if not await self.wait_until_logged_in():
                await self.emit("on_error", "Cliente no logueado.")
                return False

            # Helper function to escape chat name for CSS selectors
            def escape_css_string(value: str) -> str:
                return value.replace('"', '\\"')

            # Helper function to escape chat name for XPath query
            def escape_xpath_string(value: str) -> str:
                if "'" in value and '"' in value:
                    parts = value.split("'")
                    return "concat('" + "', \"'\" , '".join(parts) + "')"
                elif "'" in value:
                    return f'"{value}"'
                else:
                    return f"'{value}'"

            escaped_chat_name_for_css = escape_css_string(chat_name)

            async def find_and_click_chat_in_list(name_css_escaped: str) -> bool:
                chat_selector = f"span[title='{name_css_escaped}']"
                chat_element = await self._page.query_selector(chat_selector)
                if chat_element and await chat_element.is_visible():
                    try:
                        await chat_element.scroll_into_view_if_needed()
                        await chat_element.click()
                        await self._page.wait_for_timeout(1500)  # Wait for chat to open
                        return True
                    except Exception as e:
                        await self.emit("on_warning", f"Error al hacer clic en '{chat_name}' directamente: {e}")
                return False

            # 1. Try in "All Chats" (this is often default, but click to be sure)
            await self.emit("on_info", "Intentando abrir chat en 'Todos los chats'.")
            all_chats_button = await self._page.query_selector(loc.ALL_CHATS_BUTTON)
            if all_chats_button and await all_chats_button.is_visible():
                try:
                    await all_chats_button.click()
                    await self._page.wait_for_timeout(1000)  # Wait for filter to apply
                    if await find_and_click_chat_in_list(escaped_chat_name_for_css):
                        await self.emit("on_info", f"Chat '{chat_name}' abierto desde 'Todos los chats'.")
                        return True
                except Exception as e:
                    await self.emit("on_warning", f"Error al intentar filtrar por 'Todos los chats': {e}")
            else: # Fallback if 'All Chats' button not found or not clicked, try finding directly
                if await find_and_click_chat_in_list(escaped_chat_name_for_css):
                    await self.emit("on_info", f"Chat '{chat_name}' abierto directamente (sin filtro explícito).")
                    return True

            # 2. Try in "Unread"
            await self.emit("on_info", "Intentando abrir chat en 'No leídos'.")
            unread_chats_button = await self._page.query_selector(loc.UNREAD_CHATS_BUTTON)
            if unread_chats_button and await unread_chats_button.is_visible():
                try:
                    await unread_chats_button.click()
                    await self._page.wait_for_timeout(1000)  # Wait for filter to apply
                    if await find_and_click_chat_in_list(escaped_chat_name_for_css):
                        await self.emit("on_info", f"Chat '{chat_name}' abierto desde 'No leídos'.")
                        return True
                except Exception as e:
                    await self.emit("on_warning", f"Error al intentar filtrar por 'No leídos': {e}")
            
            # 3. Use the main search bar
            await self.emit("on_info", f"Chat '{chat_name}' no encontrado en filtros, usando buscador general.")
            
            if not await self.wa_elements.click_search_button():
                await self.emit("on_error", "No se pudo activar la barra de búsqueda.")
                return False

            search_box_typed = False
            for selector in loc.SEARCH_TEXT_BOX:
                search_input = await self._page.query_selector(selector)
                if search_input and await search_input.is_visible():
                    try:
                        await search_input.click(timeout=1000) 
                        await self._page.wait_for_timeout(200)
                        await search_input.fill("") 
                        await search_input.type(chat_name, delay=75)
                        search_box_typed = True
                        break
                    except Exception as e:
                        await self.emit("on_warning", f"Error al escribir en el buscador ({selector}): {e}")
            
            if not search_box_typed:
                await self.emit("on_error", "No se pudo escribir en la barra de búsqueda.")
                try: await self._page.keyboard.press("Escape") # Close search bar if open
                except: pass
                return False

            xpath_safe_chat_name = escape_xpath_string(chat_name)
            chat_list_item_selector = f"{loc.SEARCH_ITEM}[.//span[@title={xpath_safe_chat_name}]]"

            try:
                chat_result_element = await self._page.wait_for_selector(
                    chat_list_item_selector, 
                    timeout=7000, 
                    state="visible" 
                )
                if chat_result_element:
                    await chat_result_element.scroll_into_view_if_needed()
                    await chat_result_element.click()
                    await self._page.wait_for_timeout(1500) 
                    await self.emit("on_info", f"Chat '{chat_name}' abierto desde el buscador general.")
                    # Search usually closes on click, or we can press Escape if needed
                    # For now, assume it's handled or chat opening takes precedence.
                    return True
                else:
                    # This case should ideally be caught by PlaywrightTimeoutError
                    await self.emit("on_error", f"No se encontró '{chat_name}' en resultados del buscador (elemento no devuelto).")
                    try: await self._page.keyboard.press("Escape")
                    except: pass
                    return False
            except PlaywrightTimeoutError:
                await self.emit("on_error", f"No se encontró '{chat_name}' en resultados del buscador (timeout).")
                try: await self._page.keyboard.press("Escape")
                except: pass
                return False
            except Exception as e:
                await self.emit("on_error", f"Error al seleccionar '{chat_name}' de resultados: {e}")
                try: await self._page.keyboard.press("Escape")
                except: pass
                return False

        except PlaywrightError as e:
            await self.emit("on_error", f"Error general de Playwright al abrir el chat '{chat_name}': {e}")
            return False
        except Exception as e:
            await self.emit("on_error", f"Error inesperado al abrir el chat '{chat_name}': {e}")
            return False

    async def _is_present(self, selector: str) -> bool:
        """Verifica si un elemento está presente en la página"""
        try:
            element = await self._page.query_selector(selector)
            return element is not None
        except Exception:
            return False

    async def _extract_image_from_canvas(self, canvas_element) -> Optional[bytes]:
        """Extrae la imagen de un elemento canvas"""
        if not canvas_element:
            return None
        try:
            return await canvas_element.screenshot()
        except Exception as e:
            await self.emit("on_error", f"Error extracting QR image: {e}")
            return None
        
    async def _parse_search_result(self, element, result_type: str = "CHATS") -> Optional[Dict[str, Any]]:
        try:
            components = await element.query_selector_all("xpath=.//div[@role='gridcell' and @aria-colindex='2']/parent::div/div")
            count = len(components)

            unread_el = await element.query_selector(f"xpath={loc.SEARCH_ITEM_UNREAD_MESSAGES}")
            unread_count = await unread_el.inner_text() if unread_el else "0"

            if count == 3:
                span_title_0 = await components[0].query_selector(f"xpath={loc.SPAN_TITLE}")
                group_title = await span_title_0.get_attribute("title") if span_title_0 else ""

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = await datetime_children[1].text_content() if len(datetime_children) > 1 else ""

                span_title_1 = await components[1].query_selector(f"xpath={loc.SPAN_TITLE}")
                title = await span_title_1.get_attribute("title") if span_title_1 else ""

                info_text = (await components[2].text_content()) or ""
                info_text = info_text.replace("\n", "")


                return {
                    "type": result_type,
                    "group": group_title,
                    "name": title,
                    "last_activity": datetime_text,
                    "last_message": info_text,
                    "unread_count": unread_count,
                    "element": element
                }

            elif count == 2:
                span_title_0 = await components[0].query_selector(f"xpath={loc.SPAN_TITLE}")
                title = await span_title_0.get_attribute("title") if span_title_0 else ""

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = await datetime_children[1].text_content() if len(datetime_children) > 1 else ""

                info_children = await components[1].query_selector_all("xpath=./*")
                info_text = (await info_children[0].text_content() if len(info_children) > 0 else "") or ""
                info_text = info_text.replace("\n", "")


                return {
                    "type": result_type,
                    "name": title,
                    "last_activity": datetime_text,
                    "last_message": info_text,
                    "unread_count": unread_count,
                    "element": element
                }

            return None

        except Exception as e:
            print(f"Error parsing result: {e}")
            return None




    async def wait_until_logged_in(self, timeout: int = 60) -> bool:
        """Espera hasta que el estado sea LOGGED_IN o se agote el tiempo"""
        start = time.time()
        while time.time() - start < timeout:
            if self.current_state == State.LOGGED_IN:
                return True
            await asyncio.sleep(self.poll_freq)
        await self.emit("on_error", "Tiempo de espera agotado para iniciar sesión")
        return False

    async def search_conversations(self, query: str, close=True) -> List[Dict[str, Any]]:
        """Busca conversaciones por término"""
        if not await self.wait_until_logged_in():
            return []
        try:
            return await self.wa_elements.search_chats(query, close)
        except Exception as e:
            await self.emit("on_error", f"Search error: {e}")
            return []

    async def collect_messages(self) -> List[Union[Message, FileMessage]]:
        """
        Recorre todos los contenedores de mensaje (message-in/message-out) actualmente visibles
        y devuelve una lista de instancias Message o FileMessage.
        """
        resultados: List[Union[Message, FileMessage]] = []
        # Selector de cada mensaje en pantalla
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
        if not await self.wait_until_logged_in():
            return []

        # Carpeta destino
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

    async def download_file_by_index(self, index: int, carpeta: Optional[str] = None) -> Optional[Path]:
        """
        Descarga sólo el FileMessage en la posición `index` de la lista devuelta
        por collect_messages() filtrando por FileMessage.
        """
        if not await self.wait_until_logged_in():
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

    async def send_message(self, chat_query: str, message: str) -> bool:
        """Envía un mensaje a un chat"""
        if not await self.wait_until_logged_in():
            return False

        try:
            await self.open(chat_query)
            await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)
            input_box = await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)
            if not input_box:
                await self.emit("on_error", "No se encontró el cuadro de texto para enviar el mensaje")
                return False

            await input_box.click()
            await input_box.fill(message)
            await self._page.keyboard.press("Enter")
            return True

        except Exception as e:
            await self.emit("on_error", f"Error al enviar el mensaje: {e}")
            return False
    async def send_file(self, chat_name, path):
        try:
            await self.open(chat_name)
            copy_file_to_clipboard(path)
            
            input_box = await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)
            await input_box.click()
            
            await self._page.keyboard.press('Control+v')
            await asyncio.sleep(2)  # async sleep para no bloquear
            
            await self._page.keyboard.press('Enter')
            return True
        except Exception as e:
            await self.emit("on_error", f"Error al enviar el mensaje: {e}")
            return False
            
    async def _auto_screenshot_loop(self, interval: int = 30):
        """
        Toma una captura de pantalla cada `interval` segundos mientras el cliente esté corriendo.
        """
        counter = 0
        while self.running:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshots/wa_{timestamp}_{counter}.png"
            try:
                Path("screenshots").mkdir(exist_ok=True)
                await self._page.screenshot(path=filename, full_page=True)
                await self.emit("on_info", f"Screenshot tomada: {filename}")
            except Exception as e:
                await self.emit("on_error", f"Error al tomar screenshot periódica: {e}")
            counter += 1
            await asyncio.sleep(interval)


        
