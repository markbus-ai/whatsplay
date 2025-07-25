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


async def main():
    # Configure auth with local profile in user's documents folder
    data_dir = os.path.abspath(
        os.path.join(os.path.expanduser("~"), "Documents", "whatsapp_data")
    )
    os.makedirs(data_dir, exist_ok=True)

    auth = LocalProfileAuth(data_dir)
    client = Client(auth=auth)

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

    @client.event("on_logged_in")
    async def on_logged_in():
        print("✅ Successfully logged in!")

        try:
            # Search for a chat

            success = await client.send_message(
                "5492234480402",  # Use raw chat title
                "Hello from WhatsPlay! 👋",
            )
            import time

            time.sleep(5)
            if success:
                print("✉️ Message sent successfully!")
            else:
                print("❌ Failed to send message")

                print("❌ Chat not found")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await client.stop()

    @client.event("on_error")
    async def on_error(error):
        print(f"❌ Error: {error}")

    # Start the client
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
