# API Reference

This page provides an auto-generated API reference for the key components of the WhatsPlay library.

## Client
The `Client` is the main entry point for interacting with WhatsApp.

::: whatsplay.client.Client

---

## Events
These events are emitted by the `Client` and can be handled using the `@client.event` decorator.

| Event Name | Trigger Condition | Arguments |
| :--- | :--- | :--- |
| `on_start` | The client has successfully initialized and the browser page is open. | None |
| `on_auth` | The authentication screen (QR code page) is displayed. | None |
| `on_qr` | A new QR code is detected for the first time. | `qr_binary` (bytes) |
| `on_qr_change` | The displayed QR code has been refreshed/changed. | `qr_binary` (bytes) |
| `on_logged_in` | The client has successfully logged in to WhatsApp Web. | None |
| `on_loading` | The "Loading chats" screen is visible. | `is_loading` (bool) |
| `on_unread_chat` | Unread chats are detected in the sidebar. This check runs periodically. | `chats` (List[Dict]) |
| `on_stop` | The client is stopping and cleaning up resources. | None |
| `on_disconnect` | The client has lost connection to the browser/WhatsApp. | None |
| `on_reconnect` | The client has successfully reconnected. | None |
| `on_state_change` | The client's internal state (e.g., AUTH, LOGGED_IN) has changed. | `state` (State enum) |
| `on_tick` | Emitted on every iteration of the main event loop. | None |
| `on_error` | An error occurred. | `message` (str) |
| `on_warning` | A non-critical issue occurred. | `message` (str) |
| `on_info` | Informational message. | `message` (str) |

***Note:** The `on_message` event is reserved for future use. Currently, use `on_unread_chat` to detect new activity.*

---

## Event Objects
These are the objects passed to your event handlers.

### Message
The `Message` object represents a message retrieved from a chat (e.g., via `chat_manager.collect_messages()`).

::: whatsplay.object.message.Message

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