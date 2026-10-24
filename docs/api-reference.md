# API Reference

This page provides an auto-generated API reference for the key components of the WhatsPlay library.

## Client
The `Client` is the main entry point for interacting with WhatsApp.

| Method | Returns | Notes |
| :--- | :--- | :--- |
| `start()` / `stop()` | `None` | `start()` runs the main loop until `stop()` is called. |
| `wait_until_logged_in(timeout=60)` | `bool` | |
| `refresh(timeout=180)` | `bool` | Reloads WhatsApp Web to release renderer memory; emits `on_refresh`. |
| `open(chat_name, timeout=10000, open_via_url=False, is_group=None)` | `bool` | `True` only when the open chat is verifiably the requested one. |
| `close()` | `None` | Closes the current chat. |
| `search_conversations(query, close=True)` | `List[Dict]` | |
| `collect_messages(own_push_names=None, dispose=False)` | `List[Message]` | Includes `FileMessage` and `VoiceMessage` items. |
| `send_message(chat_query, message, open_via_url=False, is_group=None)` | `bool` | `True` only after WhatsApp shows the new message with a delivery status. |
| `send_file(chat_name, path, open_via_url=False, is_group=None)` | `bool` | Same confirmation as `send_message`. |
| `react_to_last_message(emoji)` | `bool` | |
| `download_all_files(carpeta=None, detect_codecs=True)` | `List[Dict]` | Each dict: `path`, `type`, and `codec` (when detected). |
| `download_file_by_index(index, carpeta=None)` | `Optional[Dict]` | Dict with `path` and `type`. |
| `new_group(group_name, members)` | `bool` | |
| `add_members_to_group(group_name, members)` | `bool` | |
| `del_members_from_group(group_name, members)` | `bool` | |
| `page_lock` (property) | `ReentrantLock` | `async with client.page_lock:` to run several operations atomically. |
| `running` (property) | `bool` | |

WhatsPlay does not define custom exceptions: failures are reported as `False`, `[]`, or `None`, plus an `on_error` event and a log record.

::: whatsplay.client.Client

---

## Events
These events are emitted by the `Client` and can be handled using the `@client.event` decorator.

| Event Name | Trigger Condition | Arguments |
| :--- | :--- | :--- |
| `on_start` | The client has initialized and the browser page is open. | None |
| `on_auth` | The authentication screen (QR code page) is displayed. | None |
| `on_qr` | A new QR code is detected for the first time. | `qr_binary` (bytes) |
| `on_qr_change` | The displayed QR code has been refreshed/changed. | `qr_binary` (bytes) |
| `on_logged_in` | The client has successfully logged in to WhatsApp Web. | None |
| `on_loading` | The "Loading chats" screen is visible. | `is_loading` (bool) |
| `on_unread_chat` | Unread chats are detected in the sidebar (checked periodically). | `chats` (List[Dict]) |
| `on_refresh` | `client.refresh()` reloaded the page. | None |
| `on_stop` | The client is stopping and cleaning up resources. | None |
| `on_disconnect` | The client has lost connection to the browser/WhatsApp. | None |
| `on_reconnect` | The client has successfully reconnected. | None |
| `on_state_change` | The connection state changed (e.g. `CONNECTING`). | `state` (State enum) |
| `on_tick` | Emitted on every iteration of the main event loop. | None |
| `on_error` | An error occurred. | `message` (str) |
| `on_warning` | A non-critical issue occurred (e.g. a dialog that could not be closed). | `message` (str) |
| `on_info` | Informational message. | `message` (str) |

The `on_unread_chat` payload is described in [Handling Messages](guides/handling-messages.md#payload-structure).

***Note:** The `on_message` event is reserved for future use. Currently, use `on_unread_chat` to detect new activity.*

---

## Message Objects
`client.collect_messages()` returns these objects.

### Message
A text message. Main attributes: `text`, `sender` (str), `timestamp` (datetime), `is_outgoing` (bool), `msg_id`, `direction_signal`, `sender_inherited`. Use `is_from_self(own_push_names)` to check whether you sent it, `react(emoji)` to react, and `dispose()` to release its browser handles.

::: whatsplay.object.message.Message

### FileMessage
A document or media attachment. Adds `filename` and `download(page, downloads_dir)`.

::: whatsplay.object.message.FileMessage

### VoiceMessage
A voice note. Adds `duration` and `download(page, downloads_dir)`.

::: whatsplay.object.message.VoiceMessage

---

## Managers
Internal managers that handle different aspects of the client's functionality.

### Chat Manager
Responsible for finding and managing chats.

::: whatsplay.chat_manager.ChatManager

### State Manager
Responsible for managing the client's internal state.

::: whatsplay.state_manager.StateManager

---

## Authentication
Authentication handlers are used to manage the WhatsApp session.

### Local Profile Auth
The recommended handler for saving your session locally to avoid repeated QR scans.

::: whatsplay.auth.local_profile_auth.LocalProfileAuth

### No Auth
A handler that does not save any session data, requiring a new login on every run.

::: whatsplay.auth.no_auth.NoAuth

---

## Filters
The `filters` module provides classes and instances to filter events.

### Predefined Message Filters
A collection of ready-to-use filters for the `on_message` event.

::: whatsplay.filters.message_filter

### Custom Filter Base Class
Inherit from this class to create your own powerful, reusable filters.

::: whatsplay.filters.filters.CustomFilter
