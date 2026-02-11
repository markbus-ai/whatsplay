"""
Simple example of using WhatsPlay
"""

import os
import sys
import asyncio

# Add the src directory to Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.filters import CustomFilter
from pathlib import Path


async def main():
    # Configure auth with local profile in user's documents folder
    user_data = Path(__file__).parent / "whatsapp_session"

    auth = LocalProfileAuth(user_data)
    client = Client(auth=auth, headless=False)

    @client.event("on_start")
    async def on_start():
        print("🚀 Client started")

    @client.event("on_auth")
    async def on_auth():
        print("📱 Authentication required")

    @client.event("on_qr")
    async def on_qr(qr):
        print("🔄 Scan QR code to login")

    @client.event("on_loading")
    async def on_loading(loading_chats):
        if loading_chats:
            print("⌛ Loading chats...")

    @client.event("on_unread_chat")
    async def unread_chat(chats):
        await client.send_file(chats[0].get("name"), r"/home/markbusking/Downloads/TUUQZZ88.txt")

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
