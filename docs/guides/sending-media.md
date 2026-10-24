# Guide: Sending and Receiving Media

WhatsPlay makes it easy to work with files like images, videos, documents, and voice notes. This guide covers both sending files from your local disk and downloading media from a chat.

## Sending Media

Use `client.send_file()` to send any kind of file. Provide the recipient (chat name or phone number) and the local path to the file.

```python
await client.send_file(chat_name, path, open_via_url=False, is_group=None)
```

Like `send_message()`, it returns `True` only when WhatsApp shows the new message with a delivery status, and `False` otherwise (the reason is logged).

### Example: Sending an Image

```python
import asyncio
from pathlib import Path
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def send_media_file():
    auth = LocalProfileAuth(data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_logged_in")
    async def on_logged_in():
        recipient = "PHONE_NUMBER_OR_CONTACT_NAME"
        file_path = Path("/path/to/your/image.jpg")

        if not file_path.exists():
            print(f"Error: File not found at {file_path}")
            await client.stop()
            return

        if await client.send_file(recipient, str(file_path)):
            print(f"Media sent to {recipient}.")
        else:
            print(f"Could not confirm the media to {recipient}.")

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

Downloads work on the chat that is currently open, so call `client.open()` first.

### Using `client.download_all_files()`

Downloads every file and voice note loaded in the open chat to `carpeta` (default: `~/Downloads/WhatsAppFiles`). It returns a list of dictionaries:

*   `path` (`Path`): where the file was saved.
*   `type` (str): `"FileMessage"` or `"VoiceMessage"`.
*   `codec` (str): the detected audio codec, when `detect_codecs=True` and one is found.

```python
await client.open("Family Group")

files = await client.download_all_files(carpeta="./downloads/family")

for info in files:
    print(info["type"], info["path"], info.get("codec"))
```

### Using `client.download_file_by_index()`

Downloads one file by its position among the files loaded in the open chat:

*   `index=0`: the first (oldest) file.
*   `index=-1`: the last (newest) file.

It returns a dictionary with `path` and `type`, or `None` if nothing was downloaded.

```python
await client.open("My Group")

result = await client.download_file_by_index(index=-1, carpeta="./downloads")

if result:
    print(f"Last file saved to: {result['path']}")
```

### Downloading from collected messages

`collect_messages()` returns `FileMessage` and `VoiceMessage` objects for attachments and voice notes. You can download them individually:

```python
from pathlib import Path
from whatsplay import FileMessage, VoiceMessage

await client.open("My Group")
messages = await client.collect_messages()

for msg in messages:
    if isinstance(msg, VoiceMessage):
        print(f"Voice note: {msg.duration}")
    if isinstance(msg, (FileMessage, VoiceMessage)):
        saved = await msg.download(msg.page, Path("./downloads"))
        print(f"Saved: {saved}")
```

> **Note:** don't pass `dispose=True` to `collect_messages()` if you plan to download or react to those messages — disposing releases the browser handles they need.
