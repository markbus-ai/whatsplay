"""No authentication strategy implementation"""

from typing import Dict, Any
from .auth import AuthBase
from playwright.async_api import BrowserContext


class NoAuth(AuthBase):
    """Authentication strategy that doesn't persist any data"""

    def __init__(self):
        super().__init__()

    def get_browser_args(self) -> Dict[str, Any]:
        """Get browser launch arguments"""
        return {"headless": False}

    async def setup_context(self, context: BrowserContext) -> None:
        """No special configuration needed"""
        pass

    async def save_session(self) -> bool:
        """No session to save"""
        return False

    async def load_session(self) -> bool:
        """No session to load"""
        return False
