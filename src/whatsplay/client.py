import asyncio
import time
import cv2
import numpy as np
from typing import Optional, Dict, List, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from .base_client import BaseWhatsAppClient
from .wa_elements import WhatsAppElements
from .utils import show_qr_window, close_all_windows
from .constants.states import State
from .constants import locator as loc


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
        return self._is_running
    async def stop(self):
        self._is_running = False
        close_all_windows()
        await self._browser.close()
        await self.emit("on_stop")

    async def start(self) -> None:
        """Inicia el cliente y maneja el ciclo principal"""
        await super().start()
        self.wa_elements = WhatsAppElements(self._page)
        
        # Iniciar el ciclo principal
        try:
            await self._main_loop()
        finally:
            await self.stop()

    async def _main_loop(self) -> None:
        """Implementación del ciclo principal con Playwright"""
        await self.emit("on_start")
        
        qr_binary = None
        state = None

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
                        show_qr_window(qr_binary)
                        await self.emit("on_qr", qr_binary)
                    except PlaywrightTimeoutError:
                        pass

                elif curr_state == State.LOADING:
                    loading_chats = await self._is_present(loc.LOADING_CHATS)
                    await self.emit("on_loading", loading_chats)

                elif curr_state == State.LOGGED_IN:
                    await self.emit("on_logged_in")

                state = curr_state

            else:
                if curr_state == State.QR_AUTH:
                    try:
                        qr_code_canvas = await self._page.query_selector(loc.QR_CODE)
                        if qr_code_canvas:
                            curr_qr_binary = await self._extract_image_from_canvas(qr_code_canvas)
                            if curr_qr_binary != qr_binary:
                                qr_binary = curr_qr_binary
                                show_qr_window(qr_binary)
                                await self.emit("on_qr_change", qr_binary)
                    except Exception:
                        pass

                elif curr_state == State.LOGGED_IN:
                    unread_chats = []
                    try:
                        # Hacer clic en el botón de chats no leídos
                        unread_button = await self._page.query_selector(loc.UNREAD_CHATS_BUTTON)
                        if unread_button:
                            await unread_button.click()
                            await asyncio.sleep(self.unread_messages_sleep)

                            # Obtener la lista de chats no leídos
                            chat_list = await self._page.query_selector_all(loc.UNREAD_CHAT_DIV)
                            if chat_list and len(chat_list) > 0:
                                chats = await chat_list[0].query_selector_all(loc.SEARCH_ITEM)
                                for chat in chats:
                                    print("chat: ", chat)
                                    chat_result = await self._parse_search_result(chat, "CHATS")
                                    if chat_result:
                                        unread_chats.append(chat_result)
                                        await self.emit("on_unread_chat", [chat_result])

                        # Volver a todos los chats
                        all_button = await self._page.query_selector(loc.ALL_CHATS_BUTTON)
                        if all_button:
                            await all_button.click()
                    except Exception as e:
                        await self.emit("on_error", f"Error checking unread chats: {e}")

            await self.emit("on_tick")
            await asyncio.sleep(self.poll_freq)

    async def _get_state(self) -> Optional[State]:
        """Obtiene el estado actual de WhatsApp Web"""
        return await self.wa_elements.get_state()

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
            # Capturar screenshot del elemento canvas
            return await canvas_element.screenshot()
        except Exception as e:
            await self.emit("on_error", f"Error extracting QR image: {e}")
            return None

    async def _parse_search_result(self, element, result_type: str = "CHATS") -> Optional[Dict[str, Any]]:
        """Parsea un resultado de búsqueda"""
        try:
            # Implementación básica para extraer información del chat
            text = await element.inner_text()
            if not text:
                return None
                
            # Extraer nombre y última actividad
            lines = text.strip().split('\n')
            if len(lines) < 1:
                return None
                
            result = {
                "type": result_type,
                "name": lines[0],
                "last_activity": lines[1] if len(lines) > 1 else "",
                "element": element
            }
            
            return result
        except Exception as e:
            await self.emit("on_error", f"Error parsing search result: {e}")
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

    # Mantener los métodos existentes
    async def search_conversations(self, query: str, close=True) -> List[Dict[str, Any]]:
        """Busca conversaciones por término"""
        if not await self.wait_until_logged_in():
            return []

        try:
            return await self.wa_elements.search_chats(query, close)
        except Exception as e:
            await self.emit("on_error", f"Search error: {e}")
            return []


    async def send_message(self, chat_query: str, message: str) -> bool:
        """Envía un mensaje a un chat"""
        if not await self.wait_until_logged_in():
            return False

        try:
            print("Enviando mensaje...")
            # Primero intentar encontrar el chat en la lista visible
            visible_chat_found = False
            try:
                # Buscar el chat por nombre en la lista visible
                chat_list = await self._page.query_selector_all(loc.SEARCH_ITEM)
                for chat in chat_list:
                    # Usar un selector CSS válido en lugar de XPath
                    chat_name_element = await chat.query_selector("span[title]")
                    if chat_name_element:
                        chat_name = await chat_name_element.get_attribute("title")
                        if chat_name and chat_query.lower() in chat_name.lower():
                            await chat.click()
                            await self._page.wait_for_timeout(1000)
                            visible_chat_found = True
                            print("chat encontrado: ", chat_name)
                            break
            except Exception as e:
                # Si hay un error al buscar en la lista visible, continuamos con la búsqueda normal
                await self.emit("on_error", f"Error al buscar chat visible: {e}")
            
            # Si no se encontró en la lista visible, usar el buscador
            if not visible_chat_found:
                print("Buscando chat...")
                # Buscar el chat por nombre usando el buscador
                self.search_conversations(chat_query, close=False)

                # Buscar el primer resultado por clase '_ak8q' y hacer clic
                chat_result = await self._page.wait_for_selector('div._ak8q', timeout=5000)
                if not chat_result:
                    await self.emit("on_error", f"No se encontró ningún resultado para: {chat_query}")
                    return False
                await chat_result.click()
                await self._page.wait_for_timeout(1000)

            # Obtener el input de mensaje
            input_box = await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)
            if not input_box:
                await self.emit("on_error", "No se encontró el cuadro de texto para enviar el mensaje")
                return False

            # Escribir y enviar el mensaje
            await input_box.click()
            await input_box.fill(message)
            await self._page.keyboard.press("Enter")
            return True

        except Exception as e:
            await self.emit("on_error", f"Error al enviar el mensaje: {e}")
            return False


