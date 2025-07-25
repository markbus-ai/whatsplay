"""
Base client implementation for WhatsApp Web
"""

from typing import Optional, Any, Dict
from playwright.async_api import Page, Browser, BrowserContext, async_playwright

from .events.event_handler import EventHandler
from .events.event_types import EVENT_LIST
from .constants.states import State

# User Agent para Chrome 114 en Windows 10
USER_AGENT_CHROME_114_WIN10 = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.5735.91 Safari/537.36"
)


class BaseWhatsAppClient(EventHandler):
    """
    Cliente base para WhatsApp Web que maneja el ciclo de vida básico
    y la gestión de eventos
    """

    def __init__(
        self,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
        auth: Optional[Any] = None,
    ):
        super().__init__(EVENT_LIST)
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.auth = auth
        self._page: Optional[Page] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._is_running = False
        self.playwright = None

    def _get_browser_args(self) -> Dict[str, Any]:
        """Get browser launch arguments"""
        if self.auth and hasattr(self.auth, "get_browser_args"):
            # Use auth provider configuration if available
            return self.auth.get_browser_args()
        # Default configuration
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
        ]
        if self.headless:
            args.append("--headless=new")
        return {"headless": self.headless, "args": args}

    async def _initialize_browser(self) -> None:
        """Initialize browser and configure context"""
        try:
            self.playwright = await async_playwright().start()
            browser_type = self.playwright.chromium

            # Get browser launch configuration
            launch_args = self._get_browser_args()
            user_data_dir = None

            if self.auth and hasattr(self.auth, "data_dir"):
                user_data_dir = self.auth.data_dir
            elif self.user_data_dir:
                user_data_dir = self.user_data_dir

            if user_data_dir:
                # Use persistent context when we have a user data directory
                self._context = await browser_type.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=self.headless,
                    args=launch_args.get("args", []),
                    locale="en-US",
                    timezone_id="UTC",
                    viewport={"width": 1280, "height": 720},
                    user_agent=USER_AGENT_CHROME_114_WIN10,
                )
                self._browser = self._context.browser
            else:
                # Use regular launch for no profile
                self._browser = await browser_type.launch(**launch_args)
                self._context = await self._browser.new_context(
                    locale="en-US",
                    timezone_id="UTC",
                    viewport={"width": 1280, "height": 720},
                    user_agent=USER_AGENT_CHROME_114_WIN10,
                )

            # Set Accept-Language header
            await self._context.set_extra_http_headers(
                {"Accept-Language": "en-US,en;q=0.9"}
            )

            # Evitar detección básica de webdriver
            await self._context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """
            )

            self._page = await self._context.new_page()

            if self.auth:
                await self.auth.setup_context(self._context)

        except Exception as e:
            await self.emit("on_error", f"Browser initialization error: {e}")
            await self._cleanup()
            raise

    async def _cleanup(self) -> None:
        """Cleanup browser resources"""
        try:
            if self._context and self.auth:
                # Guardar estado del contexto antes de cerrar
                await self.auth.save_session()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            await self.emit("on_error", f"Cleanup error: {e}")

    async def start(self) -> None:
        """
        Start the WhatsApp Web client
        """
        try:
            await self._initialize_browser()
            self._is_running = True
            await self.emit("on_start")

            await self._page.goto("https://web.whatsapp.com")
            await self.emit("on_state_change", State.CONNECTING)

        except Exception as e:
            await self.emit("on_error", f"Start error: {e}")
            await self._cleanup()
            raise

    async def stop(self) -> None:
        """Stop the client and cleanup"""
        self._is_running = False
        await self._cleanup()
        await self.emit("on_disconnect")

    async def reconnect(self) -> None:
        """Attempt to reconnect"""
        try:
            await self._cleanup()
            await self._initialize_browser()
            await self._page.goto("https://web.whatsapp.com")
            await self.emit("on_reconnect")
        except Exception as e:
            await self.emit("on_error", f"Reconnection error: {e}")
            raise
