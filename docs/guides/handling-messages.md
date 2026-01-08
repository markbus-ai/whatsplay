# Guide: Handling Incoming Messages

WhatsPlay uses an active polling mechanism to detect new messages. Instead of passively waiting for a message event, the client periodically checks for "unread" indicators in your chat list.

This gives you full control over when and how you process new conversations.

## The `on_unread_chat` Event

This is the primary event for detecting new activity. It is triggered whenever WhatsPlay finds one or more chats with unread messages.

### Payload Structure

The event handler receives a list of dictionaries. Each dictionary represents an unread chat and contains the following keys:

*   **`name`** (str): The visible name of the chat (contact name, group title, or phone number).
*   **`unread_count`** (str): The number of unread messages (e.g., "3").
*   **`last_message`** (str): A preview of the last message shown in the sidebar.
*   **`last_activity`** (str): The time or date of the last message (e.g., "10:30 PM", "Yesterday").
*   **`type`** (str): Usually "CHATS".
*   **`group`** (str or None): The group name if it's a group chat, or empty if it's a direct message.
*   **`last_message_type`** (str): "text" or "audio" depending on the icon visible.

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
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Bot started! Watching for new messages...")

    @client.event("on_unread_chat")
    async def on_unread_chat(chats):
        """
        Triggered when there are unread chats.
        'chats' is a list of dicts: [{'name': 'John', 'unread_count': '2', ...}, ...]
        """
        print(f"Found {len(chats)} chats with new messages.")

        for chat_info in chats:
            chat_name = chat_info.get('name')
            print(f"Processing chat: {chat_name}")

            # 1. Open the chat to load messages
            if await client.open(chat_name):
                
                # 2. Collect visible messages
                messages = await client.collect_messages()
                
                if messages:
                    last_message = messages[-1]
                    sender = last_message.sender.name or "Unknown"
                    text = last_message.text
                    
                    print(f"  Last message from {sender}: {text}")

                    # 3. Simple Auto-reply Logic
                    if text and "hello" in text.lower():
                        await client.send_message(chat_name, "Hello! I am a WhatsPlay bot. 🤖")
                        print(f"  -> Replied to {chat_name}")
                    
                    # Optional: Mark as read or archive (logic depends on your needs)
                    # Currently, opening the chat marks it as read in WhatsApp.
            else:
                print(f"  Failed to open chat: {chat_name}")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(auto_reply_bot())
```

## Processing Messages

The `client.collect_messages()` method returns a list of `Message` objects. These are the same objects described in the API Reference.

### Common `Message` Attributes

*   `message.text`: The text content.
*   `message.timestamp`: Time the message was received.
*   `message.sender.name`: Name of the sender.
*   `message.is_media`: `True` if it's an image, video, etc.

### Filtering

Since you get a list of messages (usually the last few visible ones), you might want to filter them. While `on_message` filters (mentioned in other contexts) are for future streaming APIs, you can easily filter the list manually or using Python's built-in tools.

```python
# Example: Get only messages from today containing "urgent"
relevant_messages = [
    m for m in messages 
    if "urgent" in (m.text or "").lower()
]
```

## Note on `on_message`

You might see references to an `on_message` event in the source code. This event is currently **reserved for future use** and is not emitted automatically by the main loop. Please use the `on_unread_chat` pattern described above for building bots and automation tools.