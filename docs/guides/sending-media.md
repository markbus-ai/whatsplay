# Guide: Sending and Receiving Media

WhatsPlay makes it easy to work with media like images, videos, and documents. This guide covers both sending files from your local disk and downloading media from incoming messages.

## Sending Media

The primary method for sending any kind of file is `client.send_file()`. You need to provide the recipient (chat name or ID) and the local path to the file. WhatsPlay will handle the rest.

You can also provide an optional `caption` for the media.

### Example: Sending an Image with a Caption

This script sends a local image file to a specified recipient.

```python
import asyncio
from pathlib import Path
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def send_media_file():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Client ready. Sending an image...")
        
        recipient = "PHONE_NUMBER_OR_CONTACT_NAME"
        
        # Ensure you have an image at this path
        # For example: /home/user/pictures/my_image.jpg
        file_path = Path("/path/to/your/image.jpg")
        caption = "Here is a picture from WhatsPlay! 🖼️"

        if not file_path.exists():
            print(f"Error: File not found at {file_path}")
            await client.stop()
            return

        success = await client.send_file(recipient, file_path, caption=caption)
        
        if success:
            print(f"Media sent successfully to {recipient}.")
        else:
            print(f"Failed to send media to {recipient}.")
            
        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code to log in.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(send_media_file())
```

You can use the same `client.send_file()` method for any file type, including:
*   Images (`.jpg`, `.png`, etc.)
*   Videos (`.mp4`, `.mov`, etc.)
*   Documents (`.pdf`, `.docx`, `.zip`, etc.)
*   Audio files (`.mp3`, `.ogg`, etc.)

## Downloading Media

When you receive a message that contains media, the `Message` object provides a convenient way to download it.

### Using `message.download_media()`

This is the standard way to download a specific media message.

1.  Check if the message contains media using `message.is_media`.
2.  If it does, call the `await message.download_media()` method.

This method downloads the file to a specified location. If no path is provided, it may use a default directory.

#### Example: Auto-downloader Bot

This bot automatically downloads any media it receives.

```python
import asyncio
from pathlib import Path
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.event import Message

async def media_downloader_bot():
    # Create a directory to save downloaded files
    download_dir = Path("./media_downloads")
    download_dir.mkdir(exist_ok=True)
    
    print(f"Will save downloaded media to: {download_dir.resolve()}")

    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Downloader bot started. Waiting for media...")

    @client.event("on_unread_chat")
    async def on_unread_chat(chats):
        for chat in chats:
            if await client.open(chat['name']):
                messages = await client.collect_messages()
                for message in messages:
                    if message.is_media:
                        # Define a path to save the file
                        save_path = download_dir / f"{message.id}-{message.media_filename or 'download'}"
                        
                        try:
                            await message.download_media(save_path)
                            print(f"Downloaded: {save_path.name}")
                        except Exception as e:
                            print(f"Error: {e}")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code to log in.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(media_downloader_bot())
```

### Using `client.download_file_by_index()`

If you want to download a file based on its position in the list of currently visible messages (e.g., "download the last file sent"), you can use `client.download_file_by_index()`.

*   `index=0`: The first visible file (oldest).
*   `index=-1`: The last visible file (newest).

```python
# Open the chat first
await client.open("My Group")

# Download the most recent file
file_path = await client.download_file_by_index(index=-1, carpeta="./downloads")

if file_path:
    print(f"Last file saved to: {file_path}")
```