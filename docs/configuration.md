# Configuration

This guide details how to configure the `Client`, authentication strategies, and logging in WhatsPlay.

## Client Configuration

The `Client` class is the main entry point. You can configure it using the following parameters in its constructor.

```python
from whatsplay import Client

client = Client(
    auth=...,           # Authentication strategy
    headless=False,     # Run with visible browser window
)
```

### Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `auth` | `AuthBase` | `None` | The authentication strategy to use. See **Authentication** below. |
| `headless` | `bool` | `False` | If `True`, runs the browser in the background (no visible UI). Useful for servers or bots. |
| `user_data_dir` | `str` | `None` | A direct path to a Chrome user data directory. **Note:** prefer `LocalProfileAuth` instead of setting this directly. |
| `locale` | `str` | `"en-US"` | Browser locale, also sent as the `Accept-Language` header (e.g. `"es-AR"`). Use an English or Spanish locale: sending is only supported with those interface languages (see **Interface language**). |

## Authentication Strategies

WhatsPlay supports different ways to handle your WhatsApp session.

### 1. LocalProfileAuth (Recommended)

This strategy keeps your login session in a browser profile on disk, so you only need to scan the QR code once.

```python
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

# Save session to the "./my_session" folder
auth = LocalProfileAuth(data_dir="./my_session")

client = Client(auth=auth)
```

**Parameters:**

*   `data_dir` (str): The directory where session data is stored. It is created if it doesn't exist.
*   `profile` (str, default `"Default"`): The name of the profile subfolder. Useful to manage multiple accounts in the same `data_dir`.

### 2. NoAuth

This strategy does **not** save any session data. Every run starts a fresh browser and you need to scan the QR code again.

```python
from whatsplay.auth import NoAuth

auth = NoAuth()
client = Client(auth=auth)
```

## Logging

WhatsPlay uses Python's standard `logging` module. Every module logs under the `whatsplay` namespace (`whatsplay.client`, `whatsplay.chat_manager`, `whatsplay.wa_elements`, `whatsplay.state_manager`, `whatsplay.object.message`, ...), so one `setLevel()` on `"whatsplay"` controls everything.

- **If your application configures logging** (root logger has handlers), WhatsPlay records propagate to it like any other library — files, Sentry, `pytest`'s `caplog`, etc.
- **If it doesn't**, a compatibility handler prints `LEVEL: message` to stdout at `INFO`, so nothing is lost silently.

```python
import logging

# Quiet: only warnings and errors
logging.getLogger("whatsplay").setLevel(logging.WARNING)

# Detailed: state detection and DOM decisions
logging.getLogger("whatsplay.wa_elements").setLevel(logging.DEBUG)
```

State polling logs at `DEBUG`; each unread scan logs a single `INFO` summary line.

## Advanced Browser Configuration

WhatsPlay uses **Playwright** (Chromium) under the hood.

### Browser executable
If `/usr/bin/chromium` or `/usr/bin/google-chrome` exists, WhatsPlay launches it. Otherwise it uses the Chromium installed by `python -m playwright install chromium`.

### Viewport, locale & timezone
The browser launches with:
*   **Viewport:** 1280x720
*   **Locale:** the `locale` passed to `Client` (default `en-US`)
*   **Timezone:** UTC
*   **User Agent:** a standard Chrome/Windows user agent to prevent basic blocking.

Viewport, timezone, and user agent are constants in the base client to keep WhatsApp Web stable.

### Interface language
Sending relies on the composer's accessible label naming the target chat. WhatsApp Web interfaces in **Spanish and English** are supported; with any other interface language, sending is refused (it returns `False`) rather than risk typing into the wrong chat.

### Environment Variables
WhatsPlay has no environment variables of its own. Standard Playwright variables still apply:
*   `DEBUG=pw:api`: verbose logging for Playwright API calls.
*   `PLAYWRIGHT_BROWSERS_PATH`: custom path for browser binaries.
