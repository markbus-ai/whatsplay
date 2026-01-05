# Welcome to WhatsPlay

WhatsPlay is a Python library for automating WhatsApp Web using Playwright. It provides a simple, event-driven interface to interact with chats, send messages, manage groups, and much more.

Whether you want to build a bot, automate your daily reports, or scrape chat data, WhatsPlay gives you the tools to do it efficiently.

## Key Features

*   **Event-Driven:** Easily handle events like incoming messages, QR scans, or when the client is ready.
*   **Modern Async API:** Built with `asyncio` for high performance.
*   **Session Management:** Saves your session locally so you don't have to scan the QR code every time.
*   **Group Management:** Create groups, add/remove members, and more.
*   **File & Media Support:** Send images, documents, and other files with ease.

## A Quick Example

Here's a simple script to send a message to a contact:

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    auth = LocalProfileAuth("./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Client started! Sending message...")
        
        # Use a phone number (e.g., "1234567890") or a saved contact name
        # For phone numbers, include the country code without '+' or '00'
        recipient = "PHONE_NUMBER_OR_CONTACT_NAME"
        message = "Hello from WhatsPlay! 🚀"
        
        success = await client.send_message(recipient, message)
        
        if success:
            print(f"Message sent successfully to {recipient}.")
        else:
            print(f"Failed to send message to {recipient}.")
            
        await client.stop()

    # This event is triggered if you need to scan the QR code
    @client.event("on_qr")
    async def on_qr(qr):
        print("QR code scan is required. Please scan the QR in the browser.")

    await client.start()
    print("Script finished.")

if __name__ == "__main__":
    asyncio.run(main())
```
