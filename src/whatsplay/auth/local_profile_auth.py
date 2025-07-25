"""Local profile authentication implementation"""

import os
from typing import Dict, Any
from .auth import AuthBase
from playwright.async_api import BrowserContext


class LocalProfileAuth(AuthBase):
    """Authentication using a local browser profile"""

    def __init__(self, data_dir: str, profile: str = "Default"):
        super().__init__()
        self.data_dir = os.path.abspath(data_dir)
        self.profile = profile
        self.profile_path = os.path.join(self.data_dir, self.profile)
        os.makedirs(self.profile_path, exist_ok=True)

    def get_browser_args(self) -> Dict[str, Any]:
        """Get browser launch arguments for profile"""
        return {
            "headless": False,  # Profile persistence doesn't work well in headless mode
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        }

    async def setup_context(self, context: BrowserContext) -> None:
        """Configure browser context with profile settings"""
        await context.storage_state(path=os.path.join(self.profile_path, "state.json"))

    async def save_session(self) -> bool:
        """Save browser session state"""
        try:
            os.makedirs(self.profile_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False

    async def load_session(self) -> bool:
        """Check if profile exists and has state"""
        state_file = os.path.join(self.profile_path, "state.json")
        return os.path.exists(self.profile_path) and os.path.exists(state_file)
