# Welcome to WhatsPlay

[![PyPI version](https://img.shields.io/pypi/v/whatsplay)](https://pypi.org/project/whatsplay/)
[![Downloads](https://img.shields.io/pypi/dm/whatsplay)](https://pypi.org/project/whatsplay/)
[![Python](https://img.shields.io/pypi/pyversions/whatsplay)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**WhatsPlay** is a modern Python library for automating WhatsApp Web using Playwright. It provides a stable, event-driven interface to interact with chats, send messages, manage groups, and handle media — without relying on the WhatsApp Business API.

Whether you want to build a bot, automate reports, collect messages, or integrate WhatsApp into your workflow, WhatsPlay gives you the tools to do it reliably.

## Key Features

- **Stable selectors** — uses attribute-based selectors (`data-pre-plain-text`, `aria-label`, `data-testid`), not fragile CSS class names that break on every WhatsApp Web update.
- **Safe sending** — a message is only typed into the chat you asked for, and `send_message()` returns `True` only after WhatsApp shows the new message with a delivery status.
- **Exact chat matching** — groups and contacts can be told apart with `is_group`, phone numbers must match in full, and ambiguous titles are refused instead of guessed.
- **Accurate message text** — text, captions, and replies are read from WhatsApp's own message model, with the DOM as a fallback.
- **Multi-language** — works with WhatsApp Web in Spanish and English out of the box.
- **Modern async API** — built with `asyncio`; every page operation is serialized by one re-entrant lock, so concurrent handlers never interleave.
- **Persistent sessions** — scan the QR code once; subsequent runs reuse the saved session.
- **File & media support** — send files and download documents, images, and voice messages (with codec detection).
- **Event-driven** — handle events like `on_logged_in`, `on_unread_chat`, `on_error`, and more.
- **Group management** — create groups, add and remove members programmatically.
- **Long-running bots** — `refresh()` and `collect_messages(dispose=True)` keep renderer memory under control.
- **Standard logging** — everything is logged through Python's `logging` under the `whatsplay` namespace.
- **Headless mode** — works on servers and CI without a GUI.

## Quick Example

Send a message with just a few lines:

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    auth = LocalProfileAuth("./whatsapp_session")
    client = Client(auth=auth, headless=False)

    @client.event("on_logged_in")
    async def on_logged_in():
        await client.send_message("ContactName", "Hello from WhatsPlay! 🚀")
        await client.stop()

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
```

> **First run:** A browser opens — scan the QR code with your phone.  
> **Subsequent runs:** Session persists automatically, no QR needed.

## Next Steps

- **[Getting Started](getting-started.md)** — installation and your first script.
- **[Configuration](configuration.md)** — client options, authentication, and logging.
- **[Handling Messages](guides/handling-messages.md)** — auto-reply bots and message filtering.
- **[Sending Media](guides/sending-media.md)** — send files and download received media.
- **[Group Management](guides/group-management.md)** — create and manage WhatsApp groups.
- **[Advanced Features](guides/advanced-features.md)** — search, direct numbers, concurrency, and long-running bots.
- **[API Reference](api-reference.md)** — full API documentation.
