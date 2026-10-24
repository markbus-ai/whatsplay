# Guide: Advanced Features

Beyond sending and receiving messages, WhatsPlay offers several advanced features to help you manage your chats, run safely under concurrency, and keep long-running bots healthy.

## Opening the Right Chat

`client.open()` returns `True` only when the chat that ends up open is verifiably the one you asked for. It never falls back to "the first search result".

- **Exact titles:** the requested name must match a chat title exactly (case and accents are normalized).
- **Ambiguous titles are refused:** if several chats or search results share the same title, `open()` returns `False` and logs an error.
- **Phone numbers match in full:** `"2235988856"` never matches `"+54 9 2235 98-8856"`; use the complete international number.
- **Groups vs. contacts:** pass `is_group=True` or `is_group=False` to require one or the other. WhatsPlay checks the composer label ("…to group X" / "…para el grupo X").

```python
await client.open("Family", is_group=True)        # only the group "Family"
await client.send_message("Family", "Hi!", is_group=False)  # only the contact "Family"
```

`send_message()` and `send_file()` accept the same `open_via_url` and `is_group` parameters.

## Searching for Conversations

If you have a long list of chats, you can use the search function to find specific contacts or groups.

```python
# Returns a list of matching results
results = await client.search_conversations("Project Alpha")

for result in results:
    print(f"Found: {result['name']}")
    # You can then open it using the exact name
    await client.open(result["name"])
```

The search aborts if focus leaves the search box while typing, so it can never type into a chat or match messages of the open chat.

## Direct Messaging (Non-Contacts)

You can message phone numbers that are not in your contact list, or not visible in your chat history, with `open_via_url=True`. This loads the chat through `web.whatsapp.com/send?phone=...`.

```python
# Full international number, country code included
phone_number = "5491123456789"

if await client.send_message(phone_number, "Hello stranger!", open_via_url=True):
    print("Message sent to new number!")
```

If the number belongs to a saved contact, WhatsApp shows the contact's name instead of the number; WhatsPlay accepts that and the send still goes through.

## Reacting to Messages

You can react to the last visible message in a chat using emojis.

```python
await client.open("My Friend")

if await client.react_to_last_message("👍"):
    print("Reacted successfully!")
```

## Running Operations Atomically

Every public page operation (`open`, `send_message`, `collect_messages`, ...) runs under one re-entrant asyncio lock, so concurrent event handlers never interleave inside the browser. The background state check skips itself while the lock is held.

To run several operations as one unit — for example, open a chat and read it without another handler switching chats in between — hold `client.page_lock` yourself:

```python
async with client.page_lock:
    if await client.open("Work Chat"):
        messages = await client.collect_messages()
        await client.close()
```

The lock is re-entrant, so the client methods called inside the block don't deadlock.

## Long-Running Bots and Memory

WhatsApp Web's renderer grows over hours of automation. Two tools keep it under control:

- **`collect_messages(dispose=True)`** releases each message's browser handles right after reading it. Use it when you only need the data; disposed messages can no longer `react()` or `download()`.
- **`client.refresh(timeout=180)`** reloads WhatsApp Web to free accumulated renderer memory, emits `on_refresh`, and waits until logged in again. The session survives through the browser profile, so no new QR is needed. It returns `False` if the reload fails.

```python
import asyncio

async def periodic_refresh(client, every_seconds=6 * 60 * 60):
    while client.running:
        await asyncio.sleep(every_seconds)
        await client.refresh()
```

## Blocking Dialogs

WhatsApp Web sometimes shows dialogs that block the UI. WhatsPlay closes them through their close (X) button, under the page lock. A dialog that cannot be closed produces a single `on_warning` event.

## Scraping Chat History

You can combine `open` and `collect_messages` to scrape chat history. WhatsPlay reads the messages currently loaded in the chat, so very old messages need scrolling first.

```python
await client.open("Work Chat")

messages = await client.collect_messages()

for msg in messages:
    print(f"[{msg.timestamp}] {msg.sender}: {msg.text}")
```
