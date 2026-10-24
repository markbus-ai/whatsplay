# Getting Started with WhatsPlay

This guide will walk you through installing WhatsPlay and writing your first script to send a WhatsApp message.

## 1. Installation

WhatsPlay requires Python 3.8 or newer. Install it from PyPI:

```bash
pip install whatsplay
```

Then download the Chromium browser used by Playwright:

```bash
python -m playwright install chromium
```

> **Note:** if a system Chromium (`/usr/bin/chromium`) or Google Chrome (`/usr/bin/google-chrome`) is installed, WhatsPlay launches it instead of Playwright's bundled browser.

## 2. Your First Script: Sending a Message

Let's create a simple script that logs into WhatsApp and sends a message.

Create a new Python file, for example `send_hello.py`, and add the following code.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    # --- Step 1: Set up Authentication ---
    # Session data is saved in the "whatsapp_session" folder,
    # so you only need to scan the QR code once.
    auth = LocalProfileAuth(data_dir="./whatsapp_session")

    # --- Step 2: Initialize the Client ---
    # Use headless=False the first time so you can scan the QR code.
    # Switch to headless=True later for background execution.
    client = Client(auth=auth, headless=False)

    # --- Step 3: Define Event Handlers ---
    # `on_logged_in` fires once the client is logged in and ready.
    @client.event("on_logged_in")
    async def on_logged_in():
        # Replace with a real contact name, group name, or phone number.
        # Phone numbers need the full international number (country code included).
        recipient = "5491123456789"
        message = "This is my first message from WhatsPlay! 🎉"

        # True only when WhatsApp shows the new message with a delivery status.
        if await client.send_message(recipient, message, open_via_url=True):
            print(f"Message sent to {recipient}!")
        else:
            print(f"Could not confirm the message to {recipient}. Check the logs.")

        await client.stop()

    # `on_qr` fires when a QR scan is needed.
    @client.event("on_qr")
    async def on_qr(qr):
        print("Scan the QR code shown in the browser window.")

    # `on_error` reports failures (WhatsPlay returns False/None instead of raising).
    @client.event("on_error")
    async def on_error(error):
        print(f"An error occurred: {error}")

    # --- Step 4: Start the Client ---
    # Starts the browser and runs the main loop until client.stop() is called.
    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### How to Run It

1.  **Save the code** as `send_hello.py`.
2.  **Change the recipient** to a real phone number (with `open_via_url=True`) or to a contact or group name exactly as it appears in WhatsApp (without `open_via_url`).
3.  **Run it:**
    ```bash
    python send_hello.py
    ```
4.  **First-time login:** a browser window opens. Scan the WhatsApp Web QR code with your phone.
5.  **Subsequent runs:** the saved session is reused and the client logs in automatically.

## 3. What to Expect from `send_message()`

`send_message()` is deliberately strict. It returns `False` (and logs why) instead of guessing when:

- the chat cannot be opened, or more than one chat has the same title;
- the message composer does not belong to the requested chat;
- the composer does not hold exactly the text you passed;
- no new message with a delivery status appears after pressing Enter.

When you need to target a group or a contact with the same name, pass `is_group=True` or `is_group=False`. See [Advanced Features](guides/advanced-features.md) for details.

## 4. Seeing What Happens

WhatsPlay logs through Python's standard `logging` module. If your application doesn't configure logging, WhatsPlay prints `INFO` messages to stdout. To see more detail:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("whatsplay").setLevel(logging.DEBUG)
```

See [Configuration › Logging](configuration.md#logging) for more.
