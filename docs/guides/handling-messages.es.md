# Guía: Manejo de Mensajes Entrantes

Este es un placeholder para la traducción al español.

WhatsPlay's event-driven architecture makes it easy to react to incoming messages in real-time. This guide will show you how to set up handlers for messages and how to filter them.

## The `on_message` Event

The core of handling incoming messages is subscribing to the `on_message` event. Your handler function will receive a `message` object which contains all the details about the incoming message.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.event import Message

async def basic_message_handler():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Client ready. Waiting for messages...")

    # This handler will be called for every incoming message
    @client.event("on_message")
    async def handle_any_message(message: Message):
        print(f"Received a message!")
        print(f"  From: {message.sender.name or message.sender.id}")
        print(f"  Chat: {message.chat.name or message.chat.id}")
        print(f"  Text: {message.text}")
        
        # Example: Reply to the sender
        if message.text and "hello" in message.text.lower():
            await message.reply("Hello there! How can I help you?")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code to log in.")

    # Keep the client running indefinitely to listen for messages
    await client.start()
    # You might want to add client.run_forever() here if your script is only for listening
    # However, for simple examples, client.start() is sufficient if you don't call client.stop() immediately.

if __name__ == "__main__":
    asyncio.run(basic_message_handler())
```

## Filtering Messages

WhatsPlay provides powerful filtering capabilities to help you process only the messages you care about. You can pass a filter object to the `on_message` event decorator.

### Using Predefined Filters

The `whatsplay.filters` module offers several ready-to-use filters.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.event import Message
from whatsplay.filters import message_filter

async def filtered_message_handler():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Client ready. Waiting for filtered messages...")

    # Only handle messages that are text (not media, etc.)
    @client.event("on_message", message_filter.text)
    async def handle_text_message(message: Message):
        print(f"Received a TEXT message from {message.sender.name or message.sender.id}: {message.text}")

    # Only handle messages from a specific sender (by name or ID)
    @client.event("on_message", message_filter.sender("John Doe"))
    async def handle_message_from_john(message: Message):
        print(f"Received a message from John Doe: {message.text}")

    # Only handle messages matching a regular expression
    @client.event("on_message", message_filter.regex(r"^\/command"))
    async def handle_command_message(message: Message):
        print(f"Received a command: {message.text}")
        await message.reply("Command received!")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code to log in.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(filtered_message_handler())
```

### Creating Custom Filters

You can also define your own custom filter functions or classes for more complex logic. A filter function should accept a `message` object and return `True` if the message should be processed by the handler, `False` otherwise.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.event import Message
from whatsplay.filters import CustomFilter

# Custom filter function
def my_custom_filter(message: Message) -> bool:
    # Only process messages that contain "important" and are from a specific chat type
    return message.text and "important" in message.text.lower() and message.chat.is_group

# Or a CustomFilter class (more powerful for reusable, stateful filters)
class MyChatIdFilter(CustomFilter):
    def __init__(self, chat_id_to_match: str):
        self.chat_id_to_match = chat_id_to_match

    def __call__(self, message: Message) -> bool:
        return message.chat.id == self.chat_id_to_match


async def custom_filtered_message_handler():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Client ready. Waiting for custom filtered messages...")

    # Using the custom filter function
    @client.event("on_message", my_custom_filter)
    async def handle_custom_filtered_message(message: Message):
        print(f"Received an 'important' message in a group from {message.sender.name}: {message.text}")

    # Using the custom filter class
    target_chat_id = "1234567890@g.us" # Replace with a real chat ID
    @client.event("on_message", MyChatIdFilter(target_chat_id))
    async def handle_specific_chat_message(message: Message):
        print(f"Received message in specific chat ({target_chat_id}): {message.text}")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code to log in.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(custom_filtered_message_handler())
```

## Accessing Message Data

The `Message` object passed to your handler contains a wealth of information about the incoming message. Some key attributes include:

*   `message.id`: Unique ID of the message.
*   `message.text`: The text content of the message (if any).
*   `message.sender`: A `User` object representing the sender (with `name` and `id`).
*   `message.chat`: A `Chat` object representing the conversation (with `name`, `id`, `is_group`, `is_user`).
*   `message.timestamp`: When the message was sent.
*   `message.is_media`: Boolean, `True` if the message contains media (image, video, etc.).
*   `message.media_type`: Type of media, e.g., 'image', 'video', 'document'.
*   `message.download_media()`: An awaitable method to download attached media.
*   `message.reply(text)`: An awaitable method to reply directly to this message.

This guide provides the foundation for building interactive and responsive WhatsPlay applications. Combine message handling with filters to create powerful automation scenarios!
