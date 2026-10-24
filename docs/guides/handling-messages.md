# Guide: Handling Incoming Messages

WhatsPlay uses an active polling mechanism to detect new messages. Instead of passively waiting for a message event, the client periodically checks for "unread" indicators in your chat list.

This gives you full control over when and how you process new conversations.

## The `on_unread_chat` Event

This is the primary event for detecting new activity. It is triggered whenever WhatsPlay finds one or more chats with unread messages.

Each scan first selects the **All** filter and scrolls the chat list to the top, so unread chats are found no matter where the list was left. The first scan runs about 10 seconds after login.

### Payload Structure

The event handler receives a list of dictionaries. Each dictionary represents an unread chat and contains the following keys:

*   **`name`** (str): The visible name of the chat (contact name, group title, or phone number).
*   **`unread_count`** (str): The number of unread messages (e.g., "3").
*   **`last_message`** (str): A preview of the last message shown in the sidebar.
*   **`last_activity`** (str): The time or date of the last message (e.g., "10:30 PM", "Yesterday").
*   **`type`** (str): Usually "CHATS".
*   **`group`** (str or None): The group name if it's a group chat, or empty if it's a direct message.
*   **`last_message_type`** (str): `"audio"` for voice notes, otherwise `"text"`.

The payload holds plain data only — no browser handles.

### Basic Pattern: Detect, Open, and Read

To read the actual content of the messages, you need to:
1.  Listen for `on_unread_chat`.
2.  Iterate through the detected chats.
3.  **Open** each chat using `client.open()`.
4.  **Collect** the messages using `client.collect_messages()`.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def auto_reply_bot():
    auth = LocalProfileAuth(data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_logged_in")
    async def on_logged_in():
        print("Bot started! Watching for new messages...")

    @client.event("on_unread_chat")
    async def on_unread_chat(chats):
        """'chats' is a list of dicts: [{'name': 'John', 'unread_count': '2', ...}, ...]"""
        for chat_info in chats:
            chat_name = chat_info["name"]

            # 1. Open the chat (False if it can't be verified or the title is ambiguous).
            #    Pass is_group=True/False when a group and a contact may share a name.
            if not await client.open(chat_name):
                print(f"Failed to open chat: {chat_name}")
                continue

            # 2. Collect the loaded messages
            messages = await client.collect_messages()
            incoming = [m for m in messages if not m.is_outgoing]

            if incoming:
                last = incoming[-1]
                print(f"  Last message from {last.sender or 'Unknown'}: {last.text}")

                # 3. Simple auto-reply logic
                if last.text and "hello" in last.text.lower():
                    await client.send_message(chat_name, "Hello! I am a WhatsPlay bot. 🤖")

            # Opening the chat marks it as read in WhatsApp.
            await client.close()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(auto_reply_bot())
```

## Processing Messages

`client.collect_messages()` returns a list of `Message` objects. Documents and attachments are `FileMessage` instances and voice notes are `VoiceMessage` instances (both subclasses of `Message`).

### Common `Message` Attributes

*   `message.text`: The text content. It is read from WhatsApp's own message model, so it includes image captions and the text of a reply (not the quoted message). A document's file name is **not** treated as text.
*   `message.timestamp`: A `datetime` with the date and time shown by WhatsApp (both 24h and 12h formats are parsed).
*   `message.sender`: Name (or number) of the sender, as a string.
*   `message.is_outgoing`: `True` if you sent the message.
*   `message.msg_id`: WhatsApp's message id.
*   `message.filename`: Only on `FileMessage`.
*   `message.duration`: Only on `VoiceMessage`.

### Message direction

`is_outgoing` is decided by a chain of signals: the bubble tail, a delivery status (only your own messages have one), CSS classes and ids, group sender inheritance, bubble position, and finally the sender name. The signal that decided is stored in `message.direction_signal`.

If your own messages show up with your push name as sender, pass it so they are recognised:

```python
messages = await client.collect_messages(own_push_names=["My Name"])
mine = [m for m in messages if m.is_from_self(["My Name"])]
```

### Filtering

You get a list of messages (usually the last ones loaded), so you can filter them with plain Python:

```python
# Example: messages containing "urgent"
relevant_messages = [
    m for m in messages
    if "urgent" in (m.text or "").lower()
]
```

## Note on `on_message`

You might see references to an `on_message` event in the source code. This event is currently **reserved for future use** and is not emitted automatically by the main loop. Please use the `on_unread_chat` pattern described above for building bots and automation tools.
