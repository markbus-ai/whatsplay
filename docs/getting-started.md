# Getting Started with WhatsPlay

This guide will walk you through installing WhatsPlay and writing your first script to send a WhatsApp message.

## 1. Installation

WhatsPlay requires Python 3.8 or newer. You can install it directly from PyPI. We also recommend installing Playwright's browser dependencies.

First, install the library:

```bash
pip install whatsplay
```

Next, install the necessary browser binaries for Playwright (this will download a browser like Chromium):

```bash
playwright install
```

## 2. Your First Script: Sending a Message

Let's create a simple script that logs into WhatsApp and sends a message.

Create a new Python file, for example `send_hello.py`, and add the following code.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    """
    Main function to initialize the client, send a message, and stop.
    """
    
    # --- Step 1: Set up Authentication ---
    # This tells WhatsPlay to save session data in a folder named "whatsapp_session".
    # This way, you only need to scan the QR code once.
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    
    # --- Step 2: Initialize the Client ---
    # We run in headless=False for the first time to make it easy to scan the QR code.
    # You can set it to headless=True later for background execution.
    client = Client(auth=auth, headless=False)

    # --- Step 3: Define Event Handlers ---
    # `on_start` is triggered once the client is logged in and ready.
    @client.event("on_start")
    async def on_start():
        print("Client is ready! Preparing to send a message...")
        
        # Define your recipient and message
        # IMPORTANT: Replace with a real phone number or contact name.
        # For phone numbers, use the format with country code but no '+' or '00'.
        recipient = "1234567890" 
        message = "This is my first message from WhatsPlay! 🎉"
        
        # Send the message
        success = await client.send_message(recipient, message)
        
        if success:
            print(f"Message sent successfully to {recipient}!")
        else:
            print(f"Oops! Failed to send message to {recipient}.")
            
        # Stop the client after the job is done
        print("Work complete. Shutting down...")
        await client.stop()

    # `on_qr` is triggered if a QR scan is needed.
    @client.event("on_qr")
    async def on_qr(qr):
        print("Login required. A browser window should open for you to scan the QR code.")

    # `on_auth` is triggered if authentication is required
    @client.event("on_auth")
    async def on_auth():
        print("Authentication is required.")

    # `on_error` catches potential errors during execution
    @client.event("on_error")
    async def on_error(error):
        print(f"An error occurred: {error}")
        await client.stop()

    # --- Step 4: Start the Client ---
    # This call starts the browser and begins the login process.
    await client.start()
    print("Script has finished executing.")

# --- Run the main function ---
if __name__ == "__main__":
    asyncio.run(main())
```

### How to Run It

1.  **Save the code:** Save the script as `send_hello.py`.
2.  **Modify the recipient:** Change `"1234567890"` to a real phone number or a contact name saved in your WhatsApp.
3.  **Execute from your terminal:**
    ```bash
    python send_hello.py
    ```
4.  **First-time Login:** A browser window will open. Scan the WhatsApp Web QR code with your phone.
5.  **Subsequent Runs:** The script will reuse the session and should log in automatically. The message will be sent, and the script will exit.
