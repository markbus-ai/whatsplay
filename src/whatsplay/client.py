import asyncio
import signal
import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
import re
import urllib.parse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from .base_client import BaseWhatsAppClient
from .wa_elements import WhatsAppElements
from .utils import show_qr_window
from .constants.states import State
from .constants import locator as loc
from .object.message import Message, FileMessage

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
        self._cached_chats = set()
        self.poll_freq = 0.25
        self.wa_elements = None
        self.qr_task = None
        self.current_state = None
        self.unread_messages_sleep = 1  # Tiempo de espera para cargar mensajes no leídos
        self._shutdown_event = asyncio.Event()
        self._consecutive_errors = 0
        self.last_qr_shown = None
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Configura los manejadores de señales para un cierre limpio"""
        if sys.platform != 'win32':
            # En Windows, asyncio solo soporta add_signal_handler para SIGINT y SIGTERM
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    asyncio.get_event_loop().add_signal_handler(
                        sig, lambda s=sig: asyncio.create_task(self._handle_signal(s)))
                except (NotImplementedError, RuntimeError):
                    # Algunas plataformas pueden no soportar add_signal_handler
                    signal.signal(sig, lambda s, f: asyncio.create_task(self._handle_signal(s)))
        else:
            # En Windows, solo podemos manejar estas señales
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda s, f: asyncio.create_task(self._handle_signal(s)))
    
    async def _handle_signal(self, signum):
        """Maneja las señales del sistema para un cierre limpio"""
        signame = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        print(f"\nRecibida señal {signame}. Cerrando limpiamente...")
        self._shutdown_event.set()
        await self.stop()
        sys.exit(0)

    @property
    def running(self) -> bool:
        """Check if client is running"""
        return getattr(self, '_is_running', False)

    async def stop(self):
        """Detiene el cliente y libera todos los recursos"""
        if not hasattr(self, '_is_running') or not self._is_running:
            return
            
        self._is_running = False
        
        try:
            # Cerrar página si existe
            if hasattr(self, '_page') and self._page:
                try:
                    await self._page.close()
                except Exception as e:
                    await self.emit("on_error", f"Error al cerrar la página: {e}")
                finally:
                    self._page = None
            
            # Llamar al stop del padre para limpiar el contexto y el navegador
            await super().stop()
            
            # Asegurarse de que el navegador se cierre
            if hasattr(self, '_browser') and self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    await self.emit("on_error", f"Error al cerrar el navegador: {e}")
                finally:
                    self._browser = None
            
            # Detener Playwright si está activo
            if hasattr(self, 'playwright') and self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    await self.emit("on_error", f"Error al detener Playwright: {e}")
                finally:
                    self.playwright = None
                    
        except Exception as e:
            await self.emit("on_error", f"Error durante la limpieza: {e}")
        finally:
            await self.emit("on_stop")
            self._shutdown_event.set()

    async def start(self) -> None:
        """Inicia el cliente y maneja el ciclo principal"""
        try:
            await super().start()
            self.wa_elements = WhatsAppElements(self._page)
            self._is_running = True
            
            # Iniciar el ciclo principal
            await self._main_loop()
            
        except asyncio.CancelledError:
            # Manejar cancelación de tareas
            await self.emit("on_info", "Operación cancelada")
            raise
            
        except Exception as e:
            await self.emit("on_error", f"Error en el bucle principal: {e}")
            raise
            
        finally:
            # Asegurarse de que todo se cierre correctamente
            await self.stop()
    async def _main_loop(self) -> None:
        """Implementación del ciclo principal con manejo de errores"""
        if not self._page:
            await self.emit("on_error", "No se pudo inicializar la página")
            return
            
        await self.emit("on_start")
        
        # Tarea para capturas de pantalla automáticas (opcional, comentado por defecto)
        # screenshot_task = asyncio.create_task(self._auto_screenshot_loop(interval=30))
        
        try:
            # Tomar captura inicial para depuración
            try:
                await self._page.screenshot(path="init_main.png", full_page=True)
            except Exception as e:
                await self.emit("on_warning", f"No se pudo tomar captura inicial: {e}")
                
            await self._run_main_loop()
            
        except asyncio.CancelledError:
            await self.emit("on_info", "Bucle principal cancelado")
            raise
            
        except Exception as e:
            await self.emit("on_error", f"Error en el bucle principal: {e}")
            raise
            
        finally:
            # Cancelar tareas pendientes
            # screenshot_task.cancel()
            # try:
            #     await screenshot_task
            # except asyncio.CancelledError:
            #     pass
            pass
    
    async def _run_main_loop(self) -> None:
        """Bucle principal de la aplicación"""
        qr_binary = None
        state = None
        last_qr_shown = None  # Guarda la última imagen QR mostrada

        while self._is_running and not self._shutdown_event.is_set():
            try:
                curr_state = await self._get_state()
                self.current_state = curr_state  # Actualizar la propiedad current_state

                if curr_state is None:
                    await asyncio.sleep(self.poll_freq)
                    continue

                if curr_state != state:
                    await self._handle_state_change(curr_state, state)
                    state = curr_state
                else:
                    await self._handle_same_state(curr_state, last_qr_shown)
                    
                await self.emit("on_tick")
                await asyncio.sleep(self.poll_freq)
                
            except asyncio.CancelledError:
                await self.emit("on_info", "Bucle principal cancelado")
                raise
                
            except Exception as e:
                await self.emit("on_error", f"Error en la iteración del bucle: {e}")
                await asyncio.sleep(1)  # Pequeña pausa para evitar bucles rápidos de error
                
                # Si el error persiste, intentar reconectar después de varios fallos
                if self._consecutive_errors > 5:  # Ajusta según sea necesario
                    await self.emit("on_warning", "Demasiados errores consecutivos, intentando reconectar...")
                    try:
                        await self.reconnect()
                        self._consecutive_errors = 0
                    except Exception as reconnect_error:
                        await self.emit("on_error", f"Error al reconectar: {reconnect_error}")
                        # Si la reconexión falla, salir del bucle
                        break
    
    async def _handle_state_change(self, curr_state, prev_state):
        """Maneja los cambios de estado"""
        if curr_state == State.AUTH:
            await self.emit("on_auth")

        elif curr_state == State.QR_AUTH:
            try:
                qr_code_canvas = await self._page.wait_for_selector(loc.QR_CODE, timeout=5000)
                qr_binary = await self._extract_image_from_canvas(qr_code_canvas)

                if qr_binary != self.last_qr_shown:
                    show_qr_window(qr_binary)
                    self.last_qr_shown = qr_binary

                await self.emit("on_qr", qr_binary)
            except PlaywrightTimeoutError:
                await self.emit("on_warning", "Tiempo de espera agotado para el código QR")
            except Exception as e:
                await self.emit("on_error", f"Error al procesar código QR: {e}")

        elif curr_state == State.LOADING:
            loading_chats = await self._is_present(loc.LOADING_CHATS)
            await self.emit("on_loading", loading_chats)

        elif curr_state == State.LOGGED_IN:
            await self.emit("on_logged_in")
            await self._handle_logged_in_state()
    
    async def _handle_same_state(self, state, last_qr_shown):
        """Maneja la lógica cuando el estado no ha cambiado"""
        if state == State.QR_AUTH:
            await self._handle_qr_auth_state(last_qr_shown)
        elif state == State.LOGGED_IN:
            await self._handle_logged_in_state()
    
    async def _handle_qr_auth_state(self, last_qr_shown):
        """Maneja el estado de autenticación QR"""
        try:
            qr_code_canvas = await self._page.query_selector(loc.QR_CODE)
            if qr_code_canvas:
                curr_qr_binary = await self._extract_image_from_canvas(qr_code_canvas)

                if curr_qr_binary != last_qr_shown:
                    show_qr_window(curr_qr_binary)
                    last_qr_shown = curr_qr_binary
                    await self.emit("on_qr_change", curr_qr_binary)
        except Exception as e:
            await self.emit("on_warning", f"Error al actualizar código QR: {e}")
    
    async def _handle_logged_in_state(self):
        """Maneja el estado de sesión iniciada"""
        try:
            # Intentar hacer clic en el botón Continue si está presente
            continue_button = await self._page.query_selector("button:has(div:has-text('Continue'))")
            if continue_button:
                await continue_button.click()
                await asyncio.sleep(1)
                return  # Salir después de manejar el botón Continue
                
            # Manejar chats no leídos
            unread_chats = await self._check_unread_chats()
            if unread_chats:
                await self.emit("on_unread_chat", unread_chats)
                
        except Exception as e:
            await self.emit("on_error", f"Error en estado de sesión iniciada: {e}")
    
    async def _check_unread_chats(self):
        """Verifica y devuelve los chats no leídos"""
        unread_chats = []
        try:
            unread_button = await self._page.query_selector(loc.UNREAD_CHATS_BUTTON)
            if unread_button:
                await unread_button.click()
                await asyncio.sleep(self.unread_messages_sleep)

                chat_list = await self._page.query_selector_all(loc.UNREAD_CHAT_DIV)
                if chat_list and len(chat_list) > 0:
                    chats = await chat_list[0].query_selector_all(loc.SEARCH_ITEM)
                    for chat in chats:
                        chat_result = await self._parse_search_result(chat, "CHATS")
                        if chat_result:
                            unread_chats.append(chat_result)
            
            # Volver a la vista de todos los chats
            all_button = await self._page.query_selector(loc.ALL_CHATS_BUTTON)
            if all_button:
                await all_button.click()
                
        except Exception as e:
            await self.emit("on_warning", f"Error al verificar chats no leídos: {e}")
            
        return unread_chats

    async def _get_state(self) -> Optional[State]:
        """Obtiene el estado actual de WhatsApp Web"""
        return await self.wa_elements.get_state()

    async def _is_present(self, selector: str, timeout: int = 1000) -> bool:
        """Verifica si un elemento está presente en la página."""
        if not self.wa_elements:
            return False
        element = await self.wa_elements.wait_for_selector(selector, timeout=timeout)
        return element is not None
        
    async def close(self):
        """Cierra el chat o la vista actual presionando Escape."""
        if self._page:
            try:
                await self._page.keyboard.press("Escape")
            except Exception as e:
                await self.emit("on_warning", f"Error trying to close chat with Escape: {e}")
    async def open(self, chat_name: str, timeout: int = 10000, force_open: bool = False) -> bool:
        """
        Abre un chat por su nombre visible. Si no está en el DOM, lo busca y lo abre.

        Args:
            chat_name (str): El nombre del chat tal como aparece en WhatsApp.
            timeout (int): Tiempo máximo de espera para elementos (en ms).

        Returns:
            bool: True si se abrió el chat correctamente, False si falló.
        """
        page = self._page
# detectar si chat_name es número (solo dígitos y + opcional)
        es_numero = bool(re.fullmatch(r"\+?\d+", chat_name))

        if es_numero or force_open:
            # quitar '+' si existe
            numero = chat_name.lstrip("+")
            url = f"https://web.whatsapp.com/send?phone={numero}"
            await page.goto(url)
        span_xpath = f"//span[contains(@title, {repr(chat_name)})]"

        try:
            # 1. Buscar el chat directamente visible
            chat_element = await page.query_selector(f"xpath={span_xpath}")
            if chat_element:
                await chat_element.click()
                print(f"✅ Chat '{chat_name}' abierto directamente.")
            else:
                print(f"🔍 Chat '{chat_name}' no visible, usando buscador...")

                # 2. Click en botón de búsqueda
                for btn in loc.SEARCH_BUTTON:
                    btns = await page.query_selector_all(f"xpath={btn}")
                    if btns:
                        await btns[0].click()
                        break
                else:
                    raise Exception("❌ Botón de búsqueda no encontrado")

                # 3. Escribir en el input de búsqueda
                for input_xpath in loc.SEARCH_TEXT_BOX:
                    inputs = await page.query_selector_all(f"xpath={input_xpath}")
                    if inputs:
                        await inputs[0].fill(chat_name)
                        break
                else:
                    raise Exception("❌ Input de búsqueda no encontrado")

                # 4. Esperar resultado y presionar ↓ y Enter
                await page.wait_for_selector(loc.SEARCH_ITEM, timeout=timeout)
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
                print(f"✅ Chat '{chat_name}' abierto desde buscador.")

            # 5. Confirmar apertura del input de mensajes
            await page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=timeout)
            return True

        except PlaywrightTimeoutError:
            print(f"❌ Timeout esperando el input del chat '{chat_name}'")
            return False
        except Exception as e:
            print(f"❌ Error al abrir el chat '{chat_name}': {e}")
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

    async def send_message(self, chat_query: str, message: str, force_open=True) -> bool:
        """Envía un mensaje a un chat"""
        if not await self.wait_until_logged_in():
            return False

        try:
            if force_open:
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
        finally:
            await self.close()

    async def send_file(self, chat_name, path):
        """Envía un archivo a un chat especificado en WhatsApp Web usando Playwright"""

        try:
            if not os.path.isfile(path):
                msg = f"El archivo no existe: {path}"
                await self.emit("on_error", msg)
                return False

            if not await self.wait_until_logged_in():
                msg = "No se pudo iniciar sesión"
                await self.emit("on_error", msg)
                return False

            if not await self.open(chat_name):
                msg = f"No se pudo abrir el chat: {chat_name}"
                await self.emit("on_error", msg)
                return False

            await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)

            attach_btn = await self._page.wait_for_selector(loc.ATTACH_BUTTON, timeout=5000)
            await attach_btn.click()

            input_files = await self._page.query_selector_all(loc.FILE_INPUT)
            if not input_files:
                msg = "No se encontró input[type='file']"
                await self.emit("on_error", msg)
                return False

            await input_files[0].set_input_files(path)
            await asyncio.sleep(1)  # Esperar que se cargue previsualización

            send_btn = await self._page.wait_for_selector(loc.SEND_BUTTON, timeout=10000)
            await send_btn.click()

            return True

        except Exception as e:
            msg = f"Error inesperado en send_file: {str(e)}"
            await self.emit("on_error", msg)
            await self._page.screenshot(path="debug_send_file/error_unexpected.png")
            return False
        finally:
            await self.close()
