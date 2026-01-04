"""
Base client implementation for WhatsApp Web.

This module provides the foundational client class that handles browser
initialization, authentication, and lifecycle management.
"""

from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .constants.states import State
from .events.event_handler import EventHandler
from .events.event_types import EVENT_LIST

# Constants
USER_AGENT_CHROME_114_WIN10 = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.5735.91 Safari/537.36"
)

DEFAULT_VIEWPORT = {"width": 1280, "height": 720}
DEFAULT_LOCALE = "en-US"
DEFAULT_TIMEZONE = "UTC"
WHATSAPP_WEB_URL = "https://web.whatsapp.com"


class BaseWhatsAppClient(EventHandler):
    """
    Base client for WhatsApp Web that handles basic lifecycle and events.

    This class provides the foundational functionality for managing a
    WhatsApp Web session including browser initialization, context
    management, and authentication.

    Attributes:
        user_data_dir: Optional directory for persistent browser profile
        headless: Run browser in headless mode
        auth: Optional authentication provider
        _page: Playwright Page instance
        _browser: Playwright Browser instance
        _context: Playwright BrowserContext instance
        _is_running: Flag indicating if the client is active
        playwright: Playwright instance

    Example:
        >>> auth = LocalProfileAuth("./session")
        >>> client = BaseWhatsAppClient(auth=auth, headless=False)
        >>> await client.start()
    """

    def __init__(
        self,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
        auth: Optional[Any] = None,
    ) -> None:
        """
        Initialize the base WhatsApp client.

        Args:
            user_data_dir: Directory for browser profile data
            headless: Run browser in headless mode
            auth: Authentication provider instance
        """
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
        """
        Get browser launch arguments.

        Retrieves browser configuration either from the auth provider
        or uses default settings.

        Returns:
            Dictionary containing browser launch arguments
        """
        if self.auth and hasattr(self.auth, "get_browser_args"):
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
        """
        Initialize browser and configure context.

        Sets up Playwright, launches the browser, and configures the
        browser context with appropriate settings for WhatsApp Web.

        Raises:
            Exception: If browser initialization fails
        """
        try:
            self.playwright = await async_playwright().start()
            browser_type = self.playwright.chromium

            launch_args = self._get_browser_args()
            user_data_dir = self._determine_user_data_dir()

            if user_data_dir:
                await self._init_persistent_context(browser_type, user_data_dir, launch_args)
            else:
                await self._init_regular_context(browser_type, launch_args)

            await self._configure_context()
            self._page = await self._context.new_page()

            if self.auth:
                await self.auth.setup_context(self._context)

        except Exception as e:
            await self.emit("on_error", f"Browser initialization error: {e}")
            await self._cleanup()
            raise

    def _determine_user_data_dir(self) -> Optional[str]:
        """
        Determine the user data directory to use.

        Returns:
            User data directory path or None
        """
        if self.auth and hasattr(self.auth, "data_dir"):
            return self.auth.data_dir
        return self.user_data_dir

    async def _init_persistent_context(
        self,
        browser_type,
        user_data_dir: str,
        launch_args: Dict[str, Any]
    ) -> None:
        """
        Initialize a persistent browser context.

        Args:
            browser_type: Playwright browser type
            user_data_dir: Directory for browser profile data
            launch_args: Browser launch arguments
        """
        self._context = await browser_type.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=self.headless,
            args=launch_args.get("args", []),
            locale=DEFAULT_LOCALE,
            timezone_id=DEFAULT_TIMEZONE,
            viewport=DEFAULT_VIEWPORT,
            user_agent=USER_AGENT_CHROME_114_WIN10,
        )
        self._browser = self._context.browser

    async def _init_regular_context(
        self,
        browser_type,
        launch_args: Dict[str, Any]
    ) -> None:
        """
        Initialize a regular (non-persistent) browser context.

        Args:
            browser_type: Playwright browser type
            launch_args: Browser launch arguments
        """
        self._browser = await browser_type.launch(**launch_args)
        self._context = await self._browser.new_context(
            locale=DEFAULT_LOCALE,
            timezone_id=DEFAULT_TIMEZONE,
            viewport=DEFAULT_VIEWPORT,
            user_agent=USER_AGENT_CHROME_114_WIN10,
        )

    async def _configure_context(self) -> None:
        """
        Configure the browser context with additional settings.

        Sets up HTTP headers and anti-detection scripts.
        """
        # Set Accept-Language header
        await self._context.set_extra_http_headers(
            {"Accept-Language": f"{DEFAULT_LOCALE},en;q=0.9"}
        )

        # Basic webdriver detection evasion
        await self._context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            """
        )

    async def _cleanup(self) -> None:
        """
        Clean up browser resources.

        Properly closes context, browser, and Playwright instances
        while handling authentication state if needed.
        """
        try:
            if self._context and self.auth:
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
        Start the WhatsApp Web client.

        Initializes the browser and navigates to WhatsApp Web.

        Raises:
            Exception: If startup fails
        """
        try:
            await self._initialize_browser()
            self._is_running = True
            await self.emit("on_start")

            await self._page.goto(WHATSAPP_WEB_URL)
            await self.emit("on_state_change", State.CONNECTING)

        except Exception as e:
            await self.emit("on_error", f"Start error: {e}")
            await self._cleanup()
            raise

    async def stop(self) -> None:
        """
        Stop the client and clean up resources.

        Gracefully stops the client and releases all browser resources.
        """
        self._is_running = False
        await self._cleanup()
        await self.emit("on_disconnect")

    async def reconnect(self) -> None:
        """
        Attempt to reconnect to WhatsApp Web.

        Cleans up current session and reinitializes the browser.

        Raises:
            Exception: If reconnection fails
        """
        try:
            await self._cleanup()
            await self._initialize_browser()
            await self._page.goto(WHATSAPP_WEB_URL)
            await self.emit("on_reconnect")
        except Exception as e:
            await self.emit("on_error", f"Reconnection error: {e}")
            raise
