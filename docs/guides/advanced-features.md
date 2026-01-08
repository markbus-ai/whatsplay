# Guide: Advanced Features

Beyond sending and receiving messages, WhatsPlay offers several advanced features to help you manage your chats and interact more naturally.

## Searching for Conversations

If you have a long list of chats, you can use the search function to find specific contacts or groups.

```python
# Search for a contact or group
# Returns a list of matching results
results = await client.search_conversations("Project Alpha")

for result in results:
    print(f"Found: {result['name']}")
    # You can then open it using the exact name
    await client.open(result['name'])
```

## Reacting to Messages

You can react to the last received message in a chat using emojis. This is great for acknowledging receipt without sending a full text message.

```python
await client.open("My Friend")

# React with a thumbs up
success = await client.react_to_last_message("👍")

if success:
    print("Reacted successfully!")
```

## Downloading All Files

If you need to archive media or documents from a chat, `download_all_files` allows you to grab every visible attachment in the current view.

```python
await client.open("Family Group")

# Download all visible files to a specific folder
saved_paths = await client.download_all_files(carpeta="./downloads/family_photos")

print(f"Downloaded {len(saved_paths)} files.")
```

## Scraping Chat History

You can combine `open` and `collect_messages` to scrape chat history. Note that WhatsPlay currently interacts with the visible DOM, so you may need to implement scrolling logic if you need to fetch very old messages (though basic scrolling is handled by the browser interaction).

```python
await client.open("Work Chat")

# Get all currently loaded messages
messages = await client.collect_messages()

for msg in messages:
    print(f"[{msg.timestamp}] {msg.sender.name}: {msg.text}")
```
