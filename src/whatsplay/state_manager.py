import asyncio
from .constants.states import State
from .constants import locator as loc
from .utils import show_qr_window, close_qr_window, update_qr_code
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)

class StateManager:
    def __init__(self, client):
        self.client = client
        self._page = client._page
        self.wa_elements = client.wa_elements
        self.last_qr_shown = None
        self.qr_server_started = False

    async def _get_state(self) -> State:
        """Obtiene el estado actual de WhatsApp Web"""
        return await self.wa_elements.get_state()

    async def _handle_qr_logic(self, qr_binary):
        """Handles the logic for showing and updating the QR code."""
        if qr_binary and qr_binary != self.last_qr_shown:
            if not self.qr_server_started:
                show_qr_window(qr_binary)
                self.qr_server_started = True
            else:
                update_qr_code(qr_binary)
            self.last_qr_shown = qr_binary
            return True
        return False

    async def _handle_state_change(self, curr_state, prev_state):
        """Maneja los cambios de estado"""
        if curr_state == State.AUTH:
            await self.client.emit("on_auth")

        elif curr_state == State.QR_AUTH:
            try:
                qr_code_canvas = await self._page.wait_for_selector(
                    loc.QR_CODE, timeout=5000
                )
                qr_binary = await self._extract_image_from_canvas(qr_code_canvas)

                if await self._handle_qr_logic(qr_binary):
                    await self.client.emit("on_qr", qr_binary)

            except PlaywrightTimeoutError:
                await self.client.emit(
                    "on_warning", "Tiempo de espera agotado para el código QR"
                )
            except Exception as e:
                await self.client.emit("on_error", f"Error al procesar código QR: {e}")

        elif curr_state == State.LOADING:
            loading_chats = await self.wa_elements.wait_for_selector(loc.LOADING_CHATS) is not None
            await self.client.emit("on_loading", loading_chats)

        elif curr_state == State.LOGGED_IN:
            if self.qr_server_started:
                close_qr_window()
                self.qr_server_started = False
            await self.client.emit("on_logged_in")
            await self._handle_logged_in_state()

    async def _handle_same_state(self, state):
        """Maneja la lógica cuando el estado no ha cambiado"""
        if state == State.QR_AUTH:
            await self._handle_qr_auth_state()
        elif state == State.LOGGED_IN:
            await self._handle_logged_in_state()

    async def _handle_qr_auth_state(self):
        """Maneja el estado de autenticación QR"""
        try:
            qr_code_canvas = await self._page.query_selector(loc.QR_CODE)
            if qr_code_canvas:
                curr_qr_binary = await self._extract_image_from_canvas(qr_code_canvas)

                if await self._handle_qr_logic(curr_qr_binary):
                    await self.client.emit("on_qr_change", curr_qr_binary)
        except Exception as e:
            await self.client.emit("on_warning", f"Error al actualizar código QR: {e}")

    async def _handle_logged_in_state(self):
        """Maneja el estado de sesión iniciada"""
        try:
            continue_button = await self._page.query_selector(
                "button:has(div:has-text('Continue'))"
            )
            if continue_button:
                await continue_button.click()
                await asyncio.sleep(1)
                return

            unread_chats = await self.client.chat_manager._check_unread_chats()
            if unread_chats:
                await self.client.emit("on_unread_chat", unread_chats)

        except Exception as e:
            await self.client.emit("on_error", f"Error en estado de sesión iniciada: {e}")

    async def _extract_image_from_canvas(self, canvas_element):
        """Extrae la imagen de un elemento canvas"""
        if not canvas_element:
            return None
        try:
            return await canvas_element.screenshot()
        except Exception as e:
            await self.client.emit("on_error", f"Error extracting QR image: {e}")
            return None