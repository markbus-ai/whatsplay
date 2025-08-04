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

        

    def unread_filter(chat):
        """
        Example filter function.
        Only allows chats that are not groups.
        """
        return chat.get("group") is None

    @client.event("on_unread_chat", filter_obj=CustomFilter(unread_filter))
    async def unread_chat(chats):
        
        print("evento unread")
        print("chat: ", chats[0])
        print("chat name: ", chats[0].get("name"))
        print("chat group: ", chats[0].get("group"))
        print("chat type message", chats[0].get("last_message_type"))
        success = await client.send_message(chats[0].get("name"), "Hello!")
        # if success:
        #     print("✅ Mensaje enviado con éxito")
        # else:
        #     print("❌ Falló el envío del mensaje")
        # success_file = await client.send_file(
        #     chats[0].get("name"), r"/home/markusking/Descargas/Plan-de-Estudios-2010.pdf"
        # )
        # if success_file:
        #     print("✅ archivo enviado con éxito")
        # else:
        #     print("❌ Falló el envío del archivo")

    @client.event("on_error")
    async def on_error(error):
        print(f"❌ Error: {error}")

    # Start the client
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
