"""
Simple example of using WhatsPlay
"""
import os
import sys
import asyncio

# Add the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from pathlib import Path
async def main():
    # Configure auth with local profile in user's documents folder
    user_data = Path(__file__).parent / "whatsapp_session"
    
    auth = LocalProfileAuth(user_data)
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
    
    @client.event("on_unread_chat")
    async def unread_chat(chats):
        print("evento unread")
        print("chat name: ", chats[0].get('name'))
        success = await client.send_message(chats[0].get('name'), "Hello!")
        if success:
            print("✅ Mensaje enviado con éxito")
        else:
            print("❌ Falló el envío del mensaje")
        success_file = await client.send_file(chats[0].get('name'), r'C:\Users\Educacion\Desktop\profesional.pdf')
        if success_file:
            print("✅ archivo enviado con éxito")
        else:
            print("❌ Falló el envío del archivo")


    @client.event("on_error")
    async def on_error(error):
        print(f"❌ Error: {error}")
    
    # Start the client
    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
