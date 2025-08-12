import asyncio
import signal
import sys
import time
from typing import Optional, Dict, List, Any, Union

from .base_client import BaseWhatsAppClient
from .wa_elements import WhatsAppElements
from .constants.states import State
from .chat_manager import ChatManager
from .state_manager import StateManager
from .object.message import Message, FileMessage



class Client(BaseWhatsAppClient):
    """
    Cliente de WhatsApp Web implementado con Playwright
    """

    def __init__(
        self,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
        locale: str = "en-US",
        auth: Optional[Any] = None,
    ):
        super().__init__(user_data_dir=user_data_dir, headless=headless, auth=auth)
        self.locale = locale
        self._cached_chats = set()
        self.poll_freq = 0.25
        self.wa_elements = None
        self.qr_task = None
        self.current_state = None
        self.unread_messages_sleep = 1
        self._shutdown_event = asyncio.Event()
        self._consecutive_errors = 0
        self.last_qr_shown = None
        self.chat_manager = None
        self.state_manager = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Configura los manejadores de señales para un cierre limpio"""
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

    async def _handle_signal(self, signum):
        """Maneja las señales del sistema para un cierre limpio"""
        signame = (
            signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        )
        print(f"\nRecibida señal {signame}. Cerrando limpiamente...")
        self._shutdown_event.set()
        await self.stop()
        sys.exit(0)

    @property
    def running(self) -> bool:
        return getattr(self, "_is_running", False)

    async def stop(self):
        if not hasattr(self, "_is_running") or not self._is_running:
            return

        self._is_running = False
        try:
            if hasattr(self, "_page") and self._page:
                try:
                    await self._page.close()
                except Exception as e:
                    await self.emit("on_error", f"Error al cerrar la página: {e}")
                finally:
                    self._page = None
            await super().stop()
            if hasattr(self, "_browser") and self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    await self.emit("on_error", f"Error al cerrar el navegador: {e}")
                finally:
                    self._browser = None
            if hasattr(self, "playwright") and self.playwright:
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
        try:
            await super().start()
            self.wa_elements = WhatsAppElements(self._page)
            self.chat_manager = ChatManager(self)
            self.state_manager = StateManager(self)
            self._is_running = True
            await self._main_loop()
        except asyncio.CancelledError:
            await self.emit("on_info", "Operación cancelada")
            raise
        except Exception as e:
            await self.emit("on_error", f"Error en el bucle principal: {e}")
            raise
        finally:
            await self.stop()

    async def _main_loop(self) -> None:
        if not self._page:
            await self.emit("on_error", "No se pudo inicializar la página")
            return

        await self.emit("on_start")
        try:
            await self._page.screenshot(path="init_main.png", full_page=True)
        except Exception as e:
            await self.emit("on_warning", f"No se pudo tomar captura inicial: {e}")
        await self._run_main_loop()

    async def _run_main_loop(self) -> None:
        state = None
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
                else:
                    await self.state_manager._handle_same_state(curr_state)

                await self.emit("on_tick")
                await asyncio.sleep(self.poll_freq)

            except asyncio.CancelledError:
                await self.emit("on_info", "Bucle principal cancelado")
                raise
            except Exception as e:
                await self.emit("on_error", f"Error en la iteración del bucle: {e}")
                await asyncio.sleep(1)
                if self._consecutive_errors > 5:
                    await self.emit(
                        "on_warning",
                        "Demasiados errores consecutivos, intentando reconectar...",
                    )
                    try:
                        await self.reconnect()
                        self._consecutive_errors = 0
                    except Exception as reconnect_error:
                        await self.emit(
                            "on_error", f"Error al reconectar: {reconnect_error}"
                        )
                        break

    async def wait_until_logged_in(self, timeout: int = 60) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self.current_state == State.LOGGED_IN:
                return True
            await asyncio.sleep(self.poll_freq)
        await self.emit("on_error", "Tiempo de espera agotado para iniciar sesión")
        return False

    # Delegated methods to ChatManager
    async def close(self):
        return await self.chat_manager.close()

    async def open(self, chat_name: str, timeout: int = 10000, force_open: bool = False) -> bool:
        return await self.chat_manager.open(chat_name, timeout, force_open)

    async def search_conversations(self, query: str, close=True) -> List[Dict[str, Any]]:
        return await self.chat_manager.search_conversations(query, close)

    async def collect_messages(self) -> List[Union[Message, FileMessage]]:
        return await self.chat_manager.collect_messages()

    async def download_all_files(self, carpeta: Optional[str] = None):
        return await self.chat_manager.download_all_files(carpeta)

    async def download_file_by_index(self, index: int, carpeta: Optional[str] = None):
        return await self.chat_manager.download_file_by_index(index, carpeta)

    async def send_message(self, chat_query: str, message: str, force_open=True) -> bool:
        return await self.chat_manager.send_message(chat_query, message, force_open)

    async def send_file(self, chat_name, path):
        return await self.chat_manager.send_file(chat_name, path)

    async def new_group(self, group_name: str, members: list[str]):
        return await self.wa_elements.new_group(group_name, members)

    async def add_members_to_group(self, group_name: str, members: list[str]):
        return await self.wa_elements.add_members_to_group(group_name, members)
    async def del_members_from_group(self, group_name: str, members: list[str]):
        return await self.wa_elements.del_member_group(group_name, members)