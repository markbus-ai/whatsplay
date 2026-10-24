<div align="center">

# WhatsPlay 🚀

**Modern WhatsApp Web automation with Playwright and Python**

[![PyPI version](https://img.shields.io/pypi/v/whatsplay)](https://pypi.org/project/whatsplay/)
[![Downloads](https://img.shields.io/pypi/dm/whatsplay)](https://pypi.org/project/whatsplay/)
[![Python](https://img.shields.io/pypi/pyversions/whatsplay)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://markbus-ai.github.io/whatsplay/)

📖 **Documentation:** <https://markbus-ai.github.io/whatsplay/>

</div>

---

## ✨ Features

- **Stable selectors** — attribute-based (`data-pre-plain-text`, `aria-label`, `data-testid`), not minified CSS classes that break on every WA update
- **Safe sending** — text is only typed into the chat you asked for, and `send_message()` returns `True` only once WhatsApp shows the new message with a delivery status
- **Exact chat matching** — `is_group` tells groups from contacts, phone numbers match in full, ambiguous titles are refused instead of guessed
- **Accurate message text** — read from WhatsApp's own message model (captions and replies included), with the DOM as fallback
- **Multi-language** — works with WhatsApp Web in Spanish and English out of the box
- **Voice messages** — duration, download, and codec detection
- **Persistent sessions** — scan QR once, reuse the session
- **Unread chat detection** — scans from the top of the *All* filter every time
- **File & media support** — send any file; download documents, images, and voice notes
- **Event-driven** — `on_logged_in`, `on_unread_chat`, `on_error`, `on_refresh`, etc.
- **Concurrency-safe** — every page operation runs under one re-entrant lock (`client.page_lock`)
- **Long-running bots** — `client.refresh()` and `collect_messages(dispose=True)` keep renderer memory in check
- **Standard logging** — everything goes through `logging` under the `whatsplay` namespace
- **Headless mode** — works on servers without GUI

---

## Quick Start

```bash
pip install whatsplay
python -m playwright install chromium
```

```python
import asyncio
from pathlib import Path
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    auth = LocalProfileAuth(Path.home() / "whatsapp_session")
    client = Client(auth=auth, headless=False)

    @client.event("on_unread_chat")
    async def on_unread_chat(chats):
        for chat in chats:
            await client.send_message(chat["name"], "🤖 Automated with WhatsPlay!")

    await client.start()

asyncio.run(main())
```

---

## 📦 Installation

### From PyPI

```bash
pip install whatsplay
```

After installing, download the Playwright browser:

```bash
python -m playwright install chromium
```

If a system Chromium (`/usr/bin/chromium`) or Google Chrome (`/usr/bin/google-chrome`) is installed, WhatsPlay uses it instead.

### From source

```bash
git clone https://github.com/markbus-ai/whatsplay.git
cd whatsplay
pip install -e .
python -m playwright install chromium
```

---

## 📖 Usage Guide

### Basic connection

```python
from pathlib import Path
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

auth = LocalProfileAuth(data_dir=Path.home() / "whatsapp_session")
client = Client(auth=auth, headless=False)
```

### Events

```python
@client.event("on_logged_in")
async def on_logged_in():
    print("✅ Logged in")

@client.event("on_qr")
async def on_qr(qr_bytes):
    print("📸 Scan the QR code")

@client.event("on_unread_chat")
async def on_unread_chat(chats):
    # chats: [{"name": ..., "unread_count": ..., "last_message": ..., ...}, ...]
    for chat in chats:
        print(f"📩 {chat['unread_count']} unread in {chat['name']}")

@client.event("on_error")
async def on_error(message):
    print(f"❌ {message}")
```

### Reading messages

```python
if await client.open("My Group", is_group=True):
    messages = await client.collect_messages()
    for msg in messages:
        direction = "→" if msg.is_outgoing else "←"
        print(f"{direction} [{msg.timestamp}] {msg.sender}: {msg.text}")
    await client.close()
```

### Sending messages

```python
# By chat name (exact title)
await client.send_message("My Group", "Hello!", is_group=True)

# By phone number (full international number)
await client.send_message("5491123456789", "Direct message", open_via_url=True)

# Files
await client.send_file("My Group", "/path/to/report.pdf")
```

Both return `True` only after WhatsApp shows the new message with a delivery status. On failure they return `False` and log why — WhatsPlay never raises custom exceptions.

### Voice messages and files

```python
from whatsplay import VoiceMessage

await client.open("My Friend")

for msg in await client.collect_messages():
    if isinstance(msg, VoiceMessage):
        print(f"🎤 Voice message: {msg.duration}")

# Download every file and voice note in the open chat
files = await client.download_all_files(carpeta="./downloads")
for info in files:
    print(info["type"], info["path"], info.get("codec"))
```

### Running several operations atomically

```python
async with client.page_lock:
    await client.open("Work Chat")
    messages = await client.collect_messages()
    await client.close()
```

### Long-running bots

```python
messages = await client.collect_messages(dispose=True)  # release browser handles right away
await client.refresh()  # reload WhatsApp Web to free renderer memory; no new QR needed
```

### Logging

```python
import logging

logging.getLogger("whatsplay").setLevel(logging.WARNING)            # quiet
logging.getLogger("whatsplay.wa_elements").setLevel(logging.DEBUG)  # DOM detail
```

If your app doesn't configure logging, WhatsPlay prints `INFO` messages to stdout.

---

## 📚 Examples

The `examples/` directory includes ready-to-run scripts:

| File | Description |
|------|-------------|
| `simple_example.py` | Basic event-driven auto-reply |
| `collect_messages_event.py` | Collect messages from a chat after login |
| `open_example.py` | Open a specific chat programmatically |
| `search_example.py` | Search conversations with detailed results |
| `send_file.py` | Send a file to a chat |
| `react.py` | React to a collected message |
| `wsp.py` | CLI tool for quick message sending |
| `verify_selectors.py` | E2E validation of selectors against live WA Web |
| `investigate_voice.py` | Live DOM investigation for voice message structure |

---

## 🛠 Development

### Setup

```bash
pip install -e . pytest pytest-asyncio
python -m playwright install chromium
```

### Running tests

```bash
pytest tests/ -v
```

### Documentation

The docs live in `docs/` (English and Spanish) and are built with MkDocs Material. They are deployed to GitHub Pages on every push to `main`.

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

---

## 🗺 Roadmap

### Completed ✅
- Async event system
- Persistent session (QR once)
- Message sending / receiving with delivery confirmation
- File & media support, codec detection
- Voice message detection, duration & download
- Unread chat detection
- Search with exact, unambiguous matching
- Stable attribute-based selectors (no more fragile CSS classes)
- Multi-language (Spanish / English)
- Group management (create, add / remove members)
- Reactions (`react_to_last_message()`, `Message.react()`)
- Structured logging
- Page lock for concurrent handlers
- Memory management for long-running bots (`refresh()`, `dispose`)

### In progress 🚧
- Real `on_message` event (no more manual open + collect polling)
- Selector health check that warns loudly when WhatsApp Web changes its DOM

### Planned 🔮
- Send results that explain why a send failed (ambiguous chat, wrong composer, no delivery status)
- Reading older chat history by scrolling
- Warning for unsupported (non English / Spanish) locales

---

## ❓ FAQ

**Is it safe?**
It uses WhatsApp Web's official interface — as safe as using WhatsApp in a browser.

**Can WhatsApp detect it?**
There's always risk with automation. Use responsibly.

**Does it work headless?**
Yes, Playwright's headless mode is supported.

**Does it work in Spanish?**
Yes. WhatsApp Web interfaces in Spanish and English are supported; with any other interface language, sending is refused instead of risking the wrong chat.

**Why did `send_message()` return `False`?**
The chat couldn't be verified (wrong or ambiguous title), the composer belonged to another chat, or no delivery status appeared. Check the `whatsplay` logs — see [Troubleshooting](https://markbus-ai.github.io/whatsplay/troubleshooting/).

---

## 🐞 Report a bug

Open an [issue](https://github.com/markbus-ai/whatsplay/issues) with:

- Problem description
- Reproduction steps
- Python version and dependencies
- Relevant logs (`logging.getLogger("whatsplay").setLevel(logging.DEBUG)`)

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feature/amazing`)
3. Commit using [Conventional Commits](https://www.conventionalcommits.org/) (`git commit -m 'feat: add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📄 License

**Apache 2.0** — see [LICENSE](LICENSE).

---

<div align="center">

**[⭐ Star on GitHub](https://github.com/markbus-ai/whatsplay)** if you find it useful

Made with ❤️ by [@markbus-ai](https://github.com/markbus-ai)

</div>
