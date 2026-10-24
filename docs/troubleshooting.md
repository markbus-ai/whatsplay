# Troubleshooting

This guide addresses common issues you might encounter while using WhatsPlay and how to resolve them.

## Installation Issues

### `playwright: command not found`
If you get this error after installing WhatsPlay, you likely need to install Playwright's browser binaries manually.

**Solution:**
```bash
python -m playwright install chromium
```

### `Error: EACCES: permission denied` (Linux/Mac)
If you encounter permission errors when running the script or installing dependencies.

**Solution:**
Ensure you have read/write access to your current directory and the `data_dir` you passed to `LocalProfileAuth`. Avoid running scripts with `sudo` unless necessary, as it can mess up file ownership.

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
auth = LocalProfileAuth(data_dir="./whatsapp_session")
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

### `send_message()` / `send_file()` returns `False`
WhatsPlay only reports success when WhatsApp shows the new message with a delivery status. It returns `False` (and logs the reason) when:

1.  **The chat could not be opened:** the name doesn't match exactly, or more than one chat has that title. Use the exact title, pass `is_group=True/False`, or use a full phone number with `open_via_url=True`.
2.  **The composer belongs to another chat:** WhatsPlay refuses to type into a chat you didn't ask for.
3.  **The interface language is not Spanish or English:** the composer label can't be verified, so sending is refused.
4.  **No delivery status appeared:** the message may still be pending (e.g. no connection on the phone). Check WhatsApp before retrying, to avoid duplicates.

### `open()` returns `False`
`open()` refuses instead of guessing. Check the logs (`whatsplay.wa_elements`) for "ambiguous" errors, and remember phone numbers must match the full international number.

### Memory keeps growing in long-running bots
WhatsApp Web's renderer accumulates memory over time. Use `collect_messages(dispose=True)` when you only need message data, and call `await client.refresh()` periodically (e.g. every few hours). See [Advanced Features](guides/advanced-features.md#long-running-bots-and-memory).

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

1.  **Enable Debug Logging:** `logging.getLogger("whatsplay").setLevel(logging.DEBUG)` shows state detection and DOM decisions. Also handle `on_error` and `on_warning`. See [Configuration › Logging](configuration.md#logging).
2.  **Report a Bug:** Open an issue on our GitHub repository with the error log and a screenshot if possible.
