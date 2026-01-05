# Referencia de API

Este es un placeholder para la traducción al español.

This page provides an auto-generated API reference for the key components of the WhatsPlay library.

## Client
The `Client` is the main entry point for interacting with WhatsApp.

::: whatsplay.client.Client

---

## Event Objects
These are the objects passed to your event handlers.

### Message
The `Message` object is what you receive in `on_message` event handlers.

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
