"""
State management module for WhatsApp Web client.

This module handles the various states of the WhatsApp Web interface
including authentication, QR code display, loading, and logged-in states.
"""

import asyncio
from typing import Optional

from playwright.async_api import (
    ElementHandle,
    TimeoutError as PlaywrightTimeoutError,
)

from .constants import locator as loc
from .constants.states import State
from .utils import close_qr_window, show_qr_window, update_qr_code

# Constants
QR_CODE_TIMEOUT = 5000
DEFAULT_SLEEP_AFTER_CONTINUE = 1


class StateManager:
    """
    Manages WhatsApp Web client state transitions and QR code handling.

    This class monitors the WhatsApp Web state and triggers appropriate
    actions for each state transition, including QR code display,
    authentication handling, and unread message detection.

    Attributes:
        client: Reference to the main WhatsApp client
        _page: Playwright page object for browser interactions
        wa_elements: WhatsApp Web elements helper
        last_qr_shown: Binary data of the last displayed QR code
        qr_server_started: Flag indicating if QR server is running
    """

    def __init__(self, client) -> None:
        """
        Initialize StateManager with client reference.

        Args:
            client: The main WhatsApp client instance
        """
        self.client = client
        self._page = client._page
        self.wa_elements = client.wa_elements
        self.last_qr_shown: Optional[bytes] = None
        self.qr_server_started: bool = False

    async def _get_state(self) -> Optional[State]:
        """
        Get the current state of WhatsApp Web.

        Returns:
            Current State enum value or None if state cannot be determined
        """
        return await self.wa_elements.get_state()

    async def _handle_qr_logic(self, qr_binary: bytes) -> bool:
        """
        Handle the logic for showing and updating the QR code.

        This method manages the QR code server lifecycle and updates
        the displayed QR code when it changes.

        Args:
            qr_binary: Binary data of the QR code image

        Returns:
            True if QR code was updated or shown, False otherwise
        """
        if not qr_binary or qr_binary == self.last_qr_shown:
            return False

        if not self.qr_server_started:
            show_qr_window(qr_binary)
            self.qr_server_started = True
        else:
            update_qr_code(qr_binary)

        self.last_qr_shown = qr_binary
        return True

    async def _handle_state_change(
        self, curr_state: State, prev_state: Optional[State]
    ) -> None:
        """
        Handle state transitions.

        This method is called when the WhatsApp Web state changes and
        triggers appropriate actions for each state.

        Args:
            curr_state: Current state
            prev_state: Previous state (may be None on first detection)
        """
        if curr_state == State.AUTH:
            await self._handle_auth_state()

        elif curr_state == State.QR_AUTH:
            await self._handle_qr_auth_state_change()

        elif curr_state == State.LOADING:
            await self._handle_loading_state()

        elif curr_state == State.LOGGED_IN:
            await self._handle_logged_in_state_change()

    async def _handle_auth_state(self) -> None:
        """Handle the authentication state."""
        await self.client.emit("on_auth")

    async def _handle_qr_auth_state_change(self) -> None:
        """Handle QR authentication state transition."""
        try:
            qr_code_canvas = await self._page.wait_for_selector(
                loc.QR_CODE, timeout=QR_CODE_TIMEOUT
            )
            qr_binary = await self._extract_image_from_canvas(qr_code_canvas)

            if await self._handle_qr_logic(qr_binary):
                await self.client.emit("on_qr", qr_binary)

        except PlaywrightTimeoutError:
            await self.client.emit(
                "on_warning", "Timeout waiting for QR code"
            )
        except Exception as e:
            await self.client.emit("on_error", f"Error processing QR code: {e}")

    async def _handle_loading_state(self) -> None:
        """Handle the loading state."""
        loading_chats = (
            await self.wa_elements.wait_for_selector(loc.LOADING_CHATS) is not None
        )
        await self.client.emit("on_loading", loading_chats)

    async def _handle_logged_in_state_change(self) -> None:
        """Handle logged-in state transition."""
        if self.qr_server_started:
            close_qr_window()
            self.qr_server_started = False

        await self.client.emit("on_logged_in")
        await self._handle_logged_in_state()

    async def _handle_same_state(self, state: State) -> None:
        """
        Handle logic when the state hasn't changed.

        This method is called on each tick when the state remains the same,
        allowing for periodic actions like QR code refresh or unread message checks.

        Args:
            state: Current state
        """
        if state == State.QR_AUTH:
            await self._handle_qr_auth_state()
        elif state == State.LOGGED_IN:
            await self._handle_logged_in_state()

    async def _handle_qr_auth_state(self) -> None:
        """
        Handle QR authentication state (periodic check).

        Checks if the QR code has changed and updates the display if necessary.
        """
        try:
            qr_code_canvas = await self._page.query_selector(loc.QR_CODE)
            if not qr_code_canvas:
                return

            curr_qr_binary = await self._extract_image_from_canvas(qr_code_canvas)

            if await self._handle_qr_logic(curr_qr_binary):
                await self.client.emit("on_qr_change", curr_qr_binary)

        except Exception as e:
            await self.client.emit("on_warning", f"Error updating QR code: {e}")

    async def _handle_logged_in_state(self) -> None:
        """
        Handle logged-in state (periodic check).

        Checks for continue buttons and unread chats when in logged-in state.
        """
        try:
            # Check for continue button (privacy policy updates, etc.)
            continue_button = await self._page.query_selector(
                "button:has(div:has-text('Continue'))"
            )
            if continue_button:
                await continue_button.click()
                await asyncio.sleep(DEFAULT_SLEEP_AFTER_CONTINUE)
                return

            # Check for unread chats
            unread_chats = await self.client.chat_manager._check_unread_chats()
            if unread_chats:
                await self.client.emit("on_unread_chat", unread_chats)

        except Exception as e:
            await self.client.emit("on_error", f"Error in logged-in state: {e}")

    async def _extract_image_from_canvas(
        self, canvas_element: Optional[ElementHandle]
    ) -> Optional[bytes]:
        """
        Extract image data from a canvas element.

        Args:
            canvas_element: Canvas element containing the image

        Returns:
            Binary image data or None if extraction fails
        """
        if not canvas_element:
            return None

        try:
            return await canvas_element.screenshot()
        except Exception as e:
            await self.client.emit("on_error", f"Error extracting QR image: {e}")
            return None
