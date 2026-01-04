"""
Example of sending a message to a new contact using the open_via_url parameter.
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

    @client.event("on_logged_in")
    async def on_logged_in():
        """
        This event is triggered when the client is logged in and ready to be used.
        """
        print("✅ Client is logged in and ready!")

        # --- How to send a message to a new number ---
        # 1. Replace this with the target phone number.
        #    Include the country code, without the '+' or any spaces/dashes.
        #    For example: "5491122334455" for a number in Argentina.
        phone_number = "5492234480402"  # <--- CHANGED TO USER'S NUMBER

        # 2. This is the message you want to send.
        message = "Hello! This is a pre-programmed message from WhatsPlay."  # <--- CHANGE THIS

        print(f"Attempting to send message to {phone_number}...")

        # 3. Call send_message with open_via_url=True
        #    This forces whatsplay to open the chat using a URL,
        #    which works for numbers that are not in your contacts.
        success = await client.send_message(
            phone_number,
            message,
            open_via_url=True
        )

        if success:
            print(f"✅ Message sent successfully to {phone_number}")
        else:
            print(f"❌ Failed to send message to {phone_number}. "
                  "Check if the number is correct and has WhatsApp.")

        # Now that the library handles internal delays, we can stop the client
        # automatically after the operation is complete.
        print("Operation complete. Stopping client...")
        await client.stop()

    @client.event("on_error")
    async def on_error(error):
        print(f"❌ Error: {error}")

    # Start the client
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
