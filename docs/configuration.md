# Configuration

This guide details how to configure the `Client` and authentication strategies in WhatsPlay.

## Client Configuration

The `Client` class is the main entry point. You can configure it using the following parameters in its constructor.

```python
from whatsplay import Client

client = Client(
    auth=...,           # Authentication strategy
    headless=False,     # Run with visible browser window
    locale="en-US",     # Browser language
    user_data_dir=...   # (Optional) Direct path to browser profile
)
```

### Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `auth` | `AuthBase` | `None` | The authentication strategy to use. See **Authentication** below. |
| `headless` | `bool` | `False` | If `True`, runs the browser in the background (no visible UI). Useful for servers or bots. If `False`, a browser window will open. |
| `locale` | `str` | `"en-US"` | The language locale code for the browser (e.g., `"es-ES"`, `"pt-BR"`). This affects how WhatsApp Web renders text. |
| `user_data_dir` | `str` | `None` | A direct path to a Chrome user data directory. **Note:** It is recommended to use `LocalProfileAuth` instead of setting this directly. |

## Authentication Strategies

WhatsPlay supports different ways to handle your WhatsApp session.

### 1. LocalProfileAuth (Recommended)

This strategy saves your login session (cookies, local storage) to a folder on your disk. This means you only need to scan the QR code once.

```python
from whatsplay.auth import LocalProfileAuth

# Save session to the "./my_session" folder
auth = LocalProfileAuth(data_dir="./my_session")

client = Client(auth=auth)
```

**Parameters:**

*   `data_dir` (str): The directory where session data will be stored. If it doesn't exist, it will be created.
*   `profile` (str, default `"Default"`): The name of the profile subfolder. Useful if you want to manage multiple accounts in the same `data_dir`.

### 2. NoAuth

This strategy does **not** save any session data. Every time you run the script, a fresh browser instance is created, and you will need to scan the QR code again.

```python
from whatsplay.auth import NoAuth

auth = NoAuth()
client = Client(auth=auth)
```

## Advanced Browser Configuration

WhatsPlay uses **Playwright** (Chromium) under the hood.

### Viewport & Timezone
By default, the browser launches with:
*   **Viewport:** 1280x720
*   **Timezone:** UTC
*   **User Agent:** A standard Chrome/Windows user agent to prevent basic blocking.

These are currently set as constants in the base client to ensure stability with WhatsApp Web.

### Environment Variables
Since WhatsPlay relies on Playwright, standard Playwright environment variables apply:
*   `DEBUG=pw:api`: Enable verbose logging for Playwright API calls.
*   `PLAYWRIGHT_BROWSERS_PATH`: Custom path for browser binaries.
