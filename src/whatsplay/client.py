"""
Main WhatsApp Web client implementation.

This module provides the high-level Client class that orchestrates
all WhatsApp Web automation functionality.
"""

import asyncio
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base_client import BaseWhatsAppClient
from .chat_manager import ChatManager
from .constants.states import State
from .object.message import FileMessage, Message
from .state_manager import StateManager
from .wa_elements import WhatsAppElements

# Constants
DEFAULT_POLL_FREQUENCY = 0.25
DEFAULT_LOGIN_TIMEOUT = 60
MAX_CONSECUTIVE_ERRORS = 5
DEFAULT_UNREAD_MESSAGES_SLEEP = 1


class Client(BaseWhatsAppClient):
    """
    High-level WhatsApp Web client with full automation capabilities.

    This client provides a complete interface for WhatsApp Web automation
    including authentication, chat management, message sending, and event handling.

    Attributes:
        locale: Locale for the browser (default: "en-US")
        poll_freq: Frequency of state polling in seconds
        current_state: Current WhatsApp Web state
        unread_messages_sleep: Sleep time between unread message checks
        wa_elements: WhatsApp Web elements helper
        chat_manager: Chat operations manager
        state_manager: State transition manager

    Example:
        >>> client = Client(auth=LocalProfileAuth("./session"))
        >>> @client.event("on_logged_in")
        ... async def on_ready():
        ...     print("Client is ready!")
        >>> await client.start()
    """

    def __init__(
        self,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
        locale: str = "en-US",
        auth: Optional[Any] = None,
    ) -> None:
        """
        Initialize the WhatsApp Web client.

        Args:
            user_data_dir: Directory for browser profile data
            headless: Run browser in headless mode
            locale: Browser locale setting
            auth: Authentication provider instance
        """
        super().__init__(user_data_dir=user_data_dir, headless=headless, auth=auth)
        self.locale = locale
        self._cached_chats: set = set()
        self.poll_freq = DEFAULT_POLL_FREQUENCY
        self.wa_elements: Optional[WhatsAppElements] = None
        self.qr_task: Optional[asyncio.Task] = None
        self.current_state: Optional[State] = None
        self.unread_messages_sleep = DEFAULT_UNREAD_MESSAGES_SLEEP
        self._shutdown_event = asyncio.Event()
        self._consecutive_errors = 0
        self.last_qr_shown: Optional[bytes] = None
        self.chat_manager: Optional[ChatManager] = None
        self.state_manager: Optional[StateManager] = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """
        Configure signal handlers for clean shutdown.

        Sets up handlers for SIGINT and SIGTERM to ensure proper cleanup
        when the process is terminated.
        """
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    asyncio.get_event_loop().add_signal_handler(
                        sig, lambda s=sig: asyncio.create_task(self._handle_signal(s))
                    )
                except (NotImplementedError, RuntimeError):
                    signal.signal(
                        sig, lambda s, f: asyncio.create_task(self._handle_signal(s))
                    )
        else:
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(
                    sig, lambda s, f: asyncio.create_task(self._handle_signal(s))
                )

    async def _handle_signal(self, signum: int) -> None:
        """
        Handle system signals for graceful shutdown.

        Args:
            signum: Signal number received
        """
        signame = (
            signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        )
        print(f"\nReceived signal {signame}. Shutting down gracefully...")
        self._shutdown_event.set()
        await self.stop()
        sys.exit(0)

    @property
    def running(self) -> bool:
        """Check if the client is currently running."""
        return getattr(self, "_is_running", False)

    async def stop(self) -> None:
        """
        Stop the client and clean up resources.

        This method ensures all resources are properly released including
        browser instances, pages, and the Playwright instance.
        """
        if not getattr(self, "_is_running", False):
            return

        self._is_running = False

        try:
            # Close page
            if hasattr(self, "_page") and self._page:
                try:
                    await self._page.close()
                except Exception as e:
                    await self.emit("on_error", f"Error closing page: {e}")
                finally:
                    self._page = None

            # Call parent stop
            await super().stop()

            # Close browser
            if hasattr(self, "_browser") and self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    await self.emit("on_error", f"Error closing browser: {e}")
                finally:
                    self._browser = None

            # Stop playwright
            if hasattr(self, "playwright") and self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    await self.emit("on_error", f"Error stopping Playwright: {e}")
                finally:
                    self.playwright = None

        except Exception as e:
            await self.emit("on_error", f"Error during cleanup: {e}")
        finally:
            await self.emit("on_stop")
            self._shutdown_event.set()

    async def start(self) -> None:
        """
        Start the WhatsApp Web client.

        Initializes all components and begins the main event loop.
        This method will run until the client is stopped.

        Raises:
            Exception: If initialization or main loop fails
        """
        try:
            await super().start()
            self.wa_elements = WhatsAppElements(self._page)
            self.chat_manager = ChatManager(self)
            self.state_manager = StateManager(self)
            self._is_running = True
            await self._main_loop()

        except asyncio.CancelledError:
            await self.emit("on_info", "Operation cancelled")
            raise
        except Exception as e:
            await self.emit("on_error", f"Error in main loop: {e}")
            raise
        finally:
            await self.stop()

    async def _main_loop(self) -> None:
        """
        Initialize and start the main event loop.

        Sets up initial state and begins monitoring WhatsApp Web.
        """
        if not self._page:
            await self.emit("on_error", "Could not initialize page")
            return

        await self.emit("on_start")

        try:
            await self._page.screenshot(path="init_main.png", full_page=True)
        except Exception as e:
            await self.emit("on_warning", f"Could not take initial screenshot: {e}")

        await self._run_main_loop()

    async def _run_main_loop(self) -> None:
        """
        Execute the main event loop.

        Continuously monitors WhatsApp Web state and handles state transitions
        until the client is stopped or encounters unrecoverable errors.
        """
        state: Optional[State] = None

        while self._is_running and not self._shutdown_event.is_set():
            try:
                curr_state = await self.state_manager._get_state()
                self.current_state = curr_state

                if curr_state is None:
                    await asyncio.sleep(self.poll_freq)
                    continue

                if curr_state != state:
                    await self.state_manager._handle_state_change(curr_state, state)
                    state = curr_state
                    self._consecutive_errors = 0  # Reset error counter on successful state change
                else:
                    await self.state_manager._handle_same_state(curr_state)

                await self.emit("on_tick")
                await asyncio.sleep(self.poll_freq)

            except asyncio.CancelledError:
                await self.emit("on_info", "Main loop cancelled")
                raise

            except Exception as e:
                self._consecutive_errors += 1
                await self.emit("on_error", f"Error in loop iteration: {e}")
                await asyncio.sleep(1)

                if self._consecutive_errors > MAX_CONSECUTIVE_ERRORS:
                    await self.emit(
                        "on_warning",
                        "Too many consecutive errors, attempting to reconnect...",
                    )
                    try:
                        await self.reconnect()
                        self._consecutive_errors = 0
                    except Exception as reconnect_error:
                        await self.emit(
                            "on_error", f"Reconnection error: {reconnect_error}"
                        )
                        break

    async def wait_until_logged_in(self, timeout: int = DEFAULT_LOGIN_TIMEOUT) -> bool:
        """
        Wait until the client is logged in.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if logged in within timeout, False otherwise
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.current_state == State.LOGGED_IN:
                return True
            await asyncio.sleep(self.poll_freq)

        await self.emit("on_error", "Login timeout expired")
        return False

    # -------------------------------------------------------------------------
    # Delegated methods to ChatManager
    # -------------------------------------------------------------------------

    async def close(self) -> None:
        """Close the currently open chat."""
        return await self.chat_manager.close()

    async def open(
        self, chat_name: str, timeout: int = 10000, open_via_url: bool = False
    ) -> bool:
        """
        Open a chat by name.

        Args:
            chat_name: Name of the chat to open
            timeout: Maximum wait time in milliseconds
            open_via_url: Force opening via URL (for phone numbers)

        Returns:
            True if chat was opened successfully
        """
        return await self.chat_manager.open(chat_name, timeout, open_via_url=open_via_url)

    async def search_conversations(
        self, query: str, close: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for conversations.

        Args:
            query: Search term
            close: Close search after completion

        Returns:
            List of matching conversations
        """
        return await self.chat_manager.search_conversations(query, close)

    async def collect_messages(self) -> List[Union[Message, FileMessage]]:
        """
        Collect all visible messages in the current chat.

        Returns:
            List of Message and FileMessage objects
        """
        return await self.chat_manager.collect_messages()

    async def download_all_files(self, carpeta: Optional[str] = None) -> List[Path]:
        """
        Download all files from the current chat.

        Args:
            carpeta: Optional custom download directory

        Returns:
            List of paths to downloaded files
        """
        return await self.chat_manager.download_all_files(carpeta)

    async def download_file_by_index(
        self, index: int, carpeta: Optional[str] = None
    ) -> Optional[Path]:
        """
        Download a specific file by index.

        Args:
            index: Zero-based file index
            carpeta: Optional custom download directory

        Returns:
            Path to downloaded file or None if failed
        """
        return await self.chat_manager.download_file_by_index(index, carpeta)

    async def send_message(
        self, chat_query: str, message: str, open_via_url: bool = False
    ) -> bool:
        """
        Send a text message.

        Args:
            chat_query: Chat name or identifier
            message: Message text to send
            open_via_url: Open chat via URL before sending

        Returns:
            True if message was sent successfully
        """
        return await self.chat_manager.send_message(chat_query, message, open_via_url=open_via_url)

    async def send_file(self, chat_name: str, path: str) -> bool:
        """
        Send a file attachment.

        Args:
            chat_name: Name of the chat
            path: Absolute path to the file

        Returns:
            True if file was sent successfully
        """
        return await self.chat_manager.send_file(chat_name, path)

    async def new_group(self, group_name: str, members: List[str]) -> bool:
        """
        Create a new group.

        Args:
            group_name: Name for the new group
            members: List of member names

        Returns:
            True if group was created successfully
        """
        return await self.wa_elements.new_group(group_name, members)

    async def add_members_to_group(
        self, group_name: str, members: List[str]
    ) -> bool:
        """
        Add members to an existing group.

        Args:
            group_name: Name of the group
            members: List of member names to add

        Returns:
            True if members were added successfully
        """
        return await self.wa_elements.add_members_to_group(group_name, members)

    async def del_members_from_group(
        self, group_name: str, members: List[str]
    ) -> bool:
        """
        Remove members from a group.

        Args:
            group_name: Name of the group
            members: List of member names to remove

        Returns:
            True if members were removed successfully
        """
        return await self.wa_elements.del_member_group(group_name, members)
