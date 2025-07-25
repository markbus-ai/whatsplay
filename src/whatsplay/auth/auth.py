"""Base class for authentication strategies"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from playwright.async_api import BrowserContext


class AuthBase(ABC):
    """Base class for all authentication methods"""

    def __init__(self):
        pass

    @abstractmethod
    def get_browser_args(self) -> Dict[str, Any]:
        """Get browser launch arguments for auth method"""
        pass

    @abstractmethod
    async def setup_context(self, context: BrowserContext) -> None:
        """Configure the browser context with authentication settings"""
        pass

    @abstractmethod
    async def save_session(self) -> bool:
        """Save the current session if supported"""
        pass

    @abstractmethod
    async def load_session(self) -> bool:
        """Load a previously saved session if available"""
        pass
