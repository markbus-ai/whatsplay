# Troubleshooting

This guide addresses common issues you might encounter while using WhatsPlay and how to resolve them.

## Installation Issues

### `playwright: command not found`
If you get this error after installing WhatsPlay, you likely need to install Playwright's browser binaries manually.

**Solution:**
```bash
pip install playwright
playwright install
```

### `Error: EACCES: permission denied` (Linux/Mac)
If you encounter permission errors when running the script or installing dependencies.

**Solution:**
Ensure you have read/write access to your current directory and the `user_data_dir` you specified. Avoid running scripts with `sudo` unless necessary, as it can mess up file ownership.

---

## Connection & Login Issues

### QR Code Not Showing
If the browser opens but the QR code never loads, or if you only see a loading spinner.

**Causes:**
1.  **Slow Internet:** WhatsApp Web loads a lot of resources.
2.  **Headless Mode:** In some environments, headless mode might behave differently.

**Solution:**
Try running with `headless=False` first to visually inspect what's happening.
```python
client = Client(auth=auth, headless=False)
```

### Session Not Saving
You scan the QR code, but next time you run the script, it asks for a scan again.

**Solution:**
Ensure you are using `LocalProfileAuth` and providing a valid path.
```python
auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
```
Also, ensure the script stops gracefully (using `await client.stop()`) so the browser context can save the profile data correctly.

---

## Runtime Errors

### `ElementHandle.click: Timeout 30000ms exceeded`
This is the most common error in web automation. It means WhatsPlay tried to find an element (like a chat or a button) but couldn't find it within the time limit.

**Causes:**
1.  **WhatsApp Web Updated:** WhatsApp frequently updates its DOM (HTML structure), breaking selectors.
2.  **Chat Not Visible:** You tried to open a chat that isn't in the loaded list.
3.  **Language Mismatch:** Some selectors depend on text (e.g., "Type a message").

**Solution:**
1.  **Check for Updates:** Run `pip install --upgrade whatsplay` to get the latest selectors.
2.  **Use Search:** Instead of relying on a chat being visible, use `client.search_conversations()` or `client.open(..., open_via_url=True)` for phone numbers.
3.  **Increase Timeout:** Some methods accept a `timeout` parameter.

### `Target closed` or `Browser closed`
The browser window was closed unexpectedly.

**Causes:**
1.  **Manual Intervention:** You closed the browser window manually while the script was running.
2.  **Crash:** Chromium crashed due to low memory.

---

## Headless Mode Issues on Server/Docker

Running WhatsPlay on a server (CI/CD, VPS) without a screen requires special attention.

**Solution:**
1.  **Install Dependencies:** Ensure all system dependencies for Playwright are installed.
    ```bash
    playwright install-deps
    ```
2.  **User Agent:** Sometimes WhatsApp Web blocks headless browsers. WhatsPlay tries to handle this, but you might need to try different configurations or run in a "headed" mode using `xvfb`.

## Still Having Issues?

If you've tried these solutions and still face problems:

1.  **Enable Debugging:** Add print statements to your events (`on_error`, `on_warning`) to get more details.
2.  **Report a Bug:** Open an issue on our GitHub repository with the error log and a screenshot if possible.
