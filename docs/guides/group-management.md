# Guide: Group Management

WhatsPlay provides robust functionality for managing WhatsApp groups, allowing you to create new groups and manage their members programmatically.

## Creating a New Group

You can create a new WhatsApp group by using the `client.new_group()` method. This method requires a group name and a list of contact names or phone numbers for the initial members.

**Important:** The contacts in the `members` list must already be in your WhatsApp contacts or be valid phone numbers (including country code, without '+' or '00').

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def create_my_group():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True) # Set headless=False if you want to see the browser

    @client.event("on_start")
    async def on_start():
        print("Client ready. Attempting to create a new group...")
        
        group_name = "My Awesome WhatsPlay Group"
        # Use existing contact names or phone numbers
        initial_members = ["Contact Name 1", "5491123456789"] # Example: "54911..." for Argentina mobile
        
        success = await client.new_group(group_name, initial_members)
        
        if success:
            print(f"Group '{group_name}' created successfully with initial members.")
        else:
            print(f"Failed to create group '{group_name}'.")
            
        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code to log in.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(create_my_group())
```

## Adding Members to an Existing Group

To add more members to an already existing group, use the `client.add_members_to_group()` method. You need to provide the name of the group and a list of members to add.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def add_members_to_existing_group():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Client ready. Attempting to add members to a group...")
        
        group_name = "My Awesome WhatsPlay Group" # Must be an existing group
        new_members = ["New Contact Name 1", "5491198765432"]
        
        success = await client.add_members_to_group(group_name, new_members)
        
        if success:
            print(f"Members added successfully to '{group_name}'.")
        else:
            print(f"Failed to add members to '{group_name}'.")
            
        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code to log in.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(add_members_to_existing_group())
```

## Removing Members from a Group

You can remove members from a group using the `client.del_members_from_group()` method. Provide the group name and a list of members to remove.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def remove_members_from_group():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Client ready. Attempting to remove members from a group...")
        
        group_name = "My Awesome WhatsPlay Group" # Must be an existing group
        members_to_remove = ["Contact Name To Remove", "5491112345678"]
        
        success = await client.del_members_from_group(group_name, members_to_remove)
        
        if success:
            print(f"Members removed successfully from '{group_name}'.")
        else:
            print(f"Failed to remove members from '{group_name}'.")
            
        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Please scan the QR code to log in.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(remove_members_from_group())
```

## Further Group Management Features (Under Consideration)

While WhatsPlay provides core group management capabilities, future enhancements could include:

*   **Promote/Demote Group Administrators:** Functionality to change a member's administrative status.
*   **Update Group Information:** Methods to change the group's subject (name) or description after creation.
*   **Retrieve Detailed Participant List:** A way to get a full list of group members along with their roles (admin/participant).

Stay tuned for updates as WhatsPlay evolves!