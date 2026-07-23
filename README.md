<div align="center">

# WhatsPlay 🚀

**Modern WhatsApp Web automation with Playwright and Python**

[![PyPI version](https://img.shields.io/pypi/v/whatsplay)](https://pypi.org/project/whatsplay/)
[![Downloads](https://img.shields.io/pypi/dm/whatsplay)](https://pypi.org/project/whatsplay/)
[![Python](https://img.shields.io/pypi/pyversions/whatsplay)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests](https://img.shields.io/badge/tests-34%20passing-brightgreen)]()

</div>

---

## ✨ Features

- **Stable selectors** — attribute-based (`data-pre-plain-text`, `aria-label`, `data-testid`), not minified CSS classes that break on every WA update
- **Multi-language** — works with WhatsApp Web in Spanish and English out of the box
- **Voice messages** — duration and download support
- **Persistent sessions** — scan QR once, reuse the session
- **Unread chat detection** — multiple heuristics (badges, font-weight, aria-labels)
- **Message filtering** — filter by sender, text, or custom rules
- **File & media support** — images, audio, documents
- **Event-driven** — `on_start`, `on_message`, `on_unread_chat`, etc.
- **Headless mode** — works on servers without GUI
- **14k+ downloads** on PyPI — battle-tested selectors

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
    async def on_unread_chat(chat_name, messages):
        await client.send_message(chat_name, "🤖 Automatizado con WhatsPlay!")

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

data_dir = Path.home() / "whatsapp_session"
data_dir.mkdir(parents=True, exist_ok=True)

auth = LocalProfileAuth(data_dir)
client = Client(auth=auth, headless=False)
```

### Events

```python
@client.event("on_start")
async def on_start():
    print("✅ Client started")

@client.event("on_auth")
async def on_auth():
    print("📸 Scan the QR code")

@client.event("on_unread_chat")
async def on_unread_chat(chat_name, messages):
    print(f"📩 Unread messages in {chat_name}")
    for msg in messages:
        print(f"  {msg.sender}: {msg.text}")
```

### Sending messages

```python
# By chat name
await client.send_message("Mi Grupo", "Hola!")

# By phone number (with country code)
await client.send_message("+5491123456789", "Mensaje directo")
```

### Voice messages

```python
@client.event("on_unread_chat")
async def handler(chat_name, messages):
    for msg in messages:
        if msg.type == "voice":
            print(f"🎤 Voice message: {msg.duration}s")
            # Download the audio
            audio = await client.download_audio(msg)
```

---

## 📚 Examples

The `examples/` directory includes ready-to-run scripts:

| File | Description |
|------|-------------|
| `simple_example.py` | Basic event-driven auto-reply |
| `open_example.py` | Open a specific chat programmatically |
| `search_example.py` | Search conversations with detailed results |
| `verify_selectors.py` | E2E validation of all selectors against live WA Web |
| `investigate_voice.py` | Live DOM investigation for voice message structure |
| `wsp.py` | CLI tool for quick message sending |

---

## 📊 PyPI Stats

| Period | Downloads |
|--------|-----------|
| **All time** | 14,700+ |
| **Last month** | 2,300+ |
| **Last week** | 190+ |

---

## 🛠 Development

### Setup

```bash
pip install -e ".[dev]"
python -m playwright install chromium
```

### Running tests

```bash
pytest tests/ -v
```

34 tests passing with 0 warnings.

---

## 🗺 Roadmap

### Completed ✅
- Async event system
- Persistent session (QR once)
- Message sending / receiving
- File & media support
- Voice message detection & duration
- Unread chat detection with multiple heuristics
- Search with fallback strategies
- Stable attribute-based selectors (no more fragile CSS classes)
- Multi-language (Spanish / English)
- Filter system (`MessageFilter`)
- Virtualized list support

### In progress 🚧
- Message reactions API
- Group management API
- Webhook integration

### Planned 🔮
- Multi-account simultaneous support
- Monitoring dashboard
- Native TypeScript definitions

---

## ❓ FAQ

**Is it safe?**
It uses WhatsApp Web's official interface — as safe as using WhatsApp in a browser.

**Can WhatsApp detect it?**
There's always risk with automation. Use responsibly.

**Does it work headless?**
Yes, Playwright's headless mode is supported.

**Does it work in Spanish?**
Yes, all selectors handle both Spanish and English WhatsApp Web locales.

---

## 🐞 Report a bug

Open an [issue](https://github.com/markbus-ai/whatsplay/issues) with:

- Problem description
- Reproduction steps
- Python version and dependencies
- Relevant logs

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feature/amazing`)
3. Commit (`git commit -am 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📄 License

**Apache 2.0**

---

<div align="center">

**[⭐ Star on GitHub](https://github.com/markbus-ai/whatsplay)** if you find it useful

Made with ❤️ by [@markbus-ai](https://github.com/markbus-ai)

</div>
