"""
Chat management module for WhatsApp Web automation.

This module provides comprehensive chat management functionality including
opening chats, searching conversations, sending messages and files, and
detecting unread chats.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from playwright.async_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)

from .constants import locator as loc
from .object.message import FileMessage, Message

# Constants
DEFAULT_DOWNLOADS_DIR = Path.home() / "Downloads" / "WhatsAppFiles"
UNREAD_ARIA_PATTERN = r"(?:mensaje(?:s)?\s+no\s+le[ií]do|unread)"
MIN_VISIBLE_CHATS_THRESHOLD = 2
DEFAULT_WAIT_TIMEOUT = 10000


class ChatManager:
    """
    Manages chat operations for WhatsApp Web.

    This class handles all chat-related operations including:
    - Opening and closing chats
    - Searching for conversations
    - Sending messages and files
    - Detecting unread chats
    - Downloading files from chats
    - Managing group operations

    Attributes:
        client: Reference to the main WhatsApp client
        _page: Playwright page object for browser interactions
        wa_elements: WhatsApp Web elements helper
    """

    def __init__(self, client) -> None:
        """
        Initialize ChatManager with client reference.

        Args:
            client: The main WhatsApp client instance
        """
        self.client = client
        self._page = client._page
        self.wa_elements = client.wa_elements

    async def _check_unread_chats(self, debug: bool = True) -> List[Dict[str, Any]]:
        """
        Detect all unread chats in the sidebar.

        This method scans the chat list to identify unread messages using multiple
        heuristics including aria-labels, badges, and font weight detection.

        Args:
            debug: If True, prints debug information during execution

        Returns:
            List of dictionaries containing unread chat information

        Note:
            The method uses multiple detection strategies:
            1. aria-label matching for 'unread' or 'mensaje(s) no leído'
            2. Explicit unread badge detection
            3. Bold font weight detection on chat titles
        """
        unread_chats: List[Dict[str, Any]] = []
        await self.close()  # Ensure no chat is currently open

        def log(msg: str) -> None:
            """Log debug messages if debug mode is enabled."""
            if debug:
                print(msg)

        async def _wait_for_grid() -> None:
            """Wait for the chat grid to be present and hydrated."""
            try:
                await self._page.locator(loc.CHAT_LIST_GRID).wait_for(timeout=15000)
            except Exception:
                await self._page.wait_for_timeout(1000)

        async def _get_scroller_handle():
            """
            Get the ElementHandle of the actual scrolling container.

            Returns:
                ElementHandle for the virtualizable scrolling container
            """
            grid = self._page.locator(loc.CHAT_LIST_GRID)
            grid_h = await grid.element_handle()

            if not grid_h:
                return await self._page.locator("#pane-side").element_handle()

            return await grid_h.evaluate_handle(
                """(el) => {
                    let cur = el;
                    while (cur && cur !== document.body) {
                        const s = getComputedStyle(cur);
                        if ((s.overflowY === 'auto' || s.overflowY === 'scroll') &&
                            cur.clientHeight < cur.scrollHeight) return cur;
                        cur = cur.parentElement;
                    }
                    return document.querySelector('#pane-side');
                }"""
            )

        async def _is_row_unread(row_loc) -> bool:
            """
            Determine if a chat row represents an unread conversation.

            Uses multiple detection strategies:
            1. aria-label with 'unread' or 'mensaje(s) no leído'
            2. Explicit unread badge
            3. Bold font weight on title (>= 600)

            Args:
                row_loc: Locator for the chat row

            Returns:
                True if the chat is unread, False otherwise
            """
            try:
                # Strategy 1: Check aria-label for unread indicators
                has_aria = await row_loc.locator("[aria-label]").evaluate_all(
                    "(els, rx) => els.some(el => (el.getAttribute('aria-label')||'').match(new RegExp(rx,'i')))",
                    UNREAD_ARIA_PATTERN,
                )
                if has_aria:
                    return True

                # Strategy 2: Check for explicit unread badge
                try:
                    if await row_loc.locator(f"xpath={loc.UNREAD_BADGE}").count() > 0:
                        return True
                except Exception:
                    pass

                # Strategy 3: Check for bold font weight on title
                title = row_loc.locator(f"xpath={loc.SPAN_TITLE}")
                if await title.count() == 0:
                    return False

                is_bold = await title.evaluate(
                    """(el) => {
                        const w = getComputedStyle(el).fontWeight;
                        const n = parseInt(w, 10);
                        return isNaN(n) ? /bold/i.test(w) : n >= 600;
                    }"""
                )
                return bool(is_bold)

            except Exception:
                return False

        async def _parse_row(row_loc):
            """
            Parse a chat row into structured data.

            Args:
                row_loc: Locator for the chat row

            Returns:
                Dictionary with chat information or None if parsing fails
            """
            handle = await row_loc.element_handle()
            if not handle:
                return None
            return await self._parse_search_result(handle, "CHATS")

        try:
            # Step 0: Wait for UI to be ready
            await _wait_for_grid()

            # Step 1: Debug initial state
            try:
                total_rows_now = await self._page.locator(
                    f"xpath={loc.CHAT_LIST_ROWS}"
                ).count()
                log(f"DEBUG: Initially visible rows: {total_rows_now}")

                if total_rows_now <= MIN_VISIBLE_CHATS_THRESHOLD:
                    await self._page.locator(loc.ALL_CHATS_BUTTON).click()
                    log("DEBUG: Few chats visible, clicking 'All' button")
                    log("DEBUG: Taking screenshot of low chat count state")
                    await self._page.screenshot(path="pocos_chats_visibles.png")

            except Exception:
                log("DEBUG: Could not count initial rows")

            # Step 2: Get correct scroller for virtualized list
            scroller_h = await _get_scroller_handle()

            # Step 3: Sweep visible rows
            async def sweep(tag: str) -> None:
                """
                Scan visible chat rows for unread messages.

                Args:
                    tag: Label for this sweep operation (for debugging)
                """
                nonlocal unread_chats
                rows = self._page.locator(f"xpath={loc.CHAT_LIST_ROWS}")
                count = await rows.count()
                log(f"DEBUG: {tag}: Currently visible rows: {count}")

                for i in range(count):
                    row = rows.nth(i)
                    try:
                        if await _is_row_unread(row):
                            chat = await _parse_row(row)
                            if chat:
                                unread_chats.append(chat)
                                log(f"✓ Unread ({tag}): {chat.get('name', 'No name')}")
                    except Exception as e:
                        log(f"DEBUG: Error evaluating row {i} ({tag}): {e}")

            # Step 4: Initial sweep
            await sweep("initial")

            # Step 5: Deduplication
            def _get_chat_key(ch: Dict[str, Any]) -> tuple:
                """Generate a unique key for a chat to enable deduplication."""
                return ch.get("id") or (
                    ch.get("name"),
                    ch.get("last_message"),
                    ch.get("last_activity"),
                )

            seen = set()
            dedup = []
            for ch in unread_chats:
                k = _get_chat_key(ch)
                if k in seen:
                    continue
                seen.add(k)
                dedup.append(ch)
            unread_chats = dedup

        except Exception as e:
            await self.client.emit("on_warning", f"Error detecting unread chats: {e}")
            log(f"DEBUG: General error: {e}")

        # Step 6: Final summary
        log("\nDEBUG: ===== SUMMARY =====")
        log(f"Total unread chats found: {len(unread_chats)}")
        for i, chat in enumerate(unread_chats, 1):
            log(f"  {i}. {chat.get('name', 'No name')}")

        return unread_chats

    async def _parse_search_result(
        self, element, result_type: str = "CHATS"
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a search result element into structured data.

        Args:
            element: ElementHandle of the search result row
            result_type: Type of result (default: "CHATS")

        Returns:
            Dictionary containing parsed chat information or None if parsing fails

        Note:
            Handles two main layouts:
            - 3 components: Group chats (group name, title, last message)
            - 2 components: Direct chats (title, last message)
        """
        try:
            components = await element.query_selector_all(
                "xpath=.//div[@role='gridcell' and @aria-colindex='2']/parent::div/div"
            )
            count = len(components)

            # Extract unread count
            unread_el = await element.query_selector(
                f"xpath={loc.SEARCH_ITEM_UNREAD_MESSAGES}"
            )
            unread_count = await unread_el.inner_text() if unread_el else "0"

            # Check for audio message
            mic_span = await components[1].query_selector(
                'xpath=.//span[@data-icon="mic"]'
            )

            if count == 3:
                # Group chat layout
                span_title_0 = await components[0].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                group_title = (
                    await span_title_0.get_attribute("title") if span_title_0 else ""
                )

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = (
                    await datetime_children[1].text_content()
                    if len(datetime_children) > 1
                    else ""
                )

                span_title_1 = await components[1].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                title = (
                    await span_title_1.get_attribute("title") if span_title_1 else ""
                )

                info_text = (await components[2].text_content()) or ""
                info_text = info_text.replace("\n", "")

                # Skip invalid states
                if any(x in info_text for x in ["loading", "status-", "typing"]):
                    return None

                return {
                    "type": result_type,
                    "group": group_title,
                    "name": title,
                    "last_activity": datetime_text,
                    "last_message": info_text,
                    "last_message_type": "audio" if mic_span else "text",
                    "unread_count": unread_count,
                    "element": element,
                }

            elif count == 2:
                # Direct chat layout
                span_title_0 = await components[0].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                title = (
                    await span_title_0.get_attribute("title") if span_title_0 else ""
                )

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = (
                    await datetime_children[1].text_content()
                    if len(datetime_children) > 1
                    else ""
                )

                info_children = await components[1].query_selector_all("xpath=./*")
                info_text = (
                    await info_children[0].text_content()
                    if len(info_children) > 0
                    else ""
                ) or ""
                info_text = info_text.replace("\n", "")

                # Skip invalid states
                if any(x in info_text for x in ["loading", "status-", "typing"]):
                    return None

                return {
                    "type": result_type,
                    "name": title,
                    "last_activity": datetime_text,
                    "last_message": info_text,
                    "last_message_type": "audio" if mic_span else "text",
                    "unread_count": unread_count,
                    "element": element,
                    "group": None,
                }

            return None

        except Exception as e:
            print(f"Error parsing result: {e}")
            return None

    async def close(self) -> None:
        """
        Close the current chat or view by pressing Escape.

        This method safely closes any open chat window by simulating
        the Escape key press.
        """
        if self._page:
            try:
                await self._page.keyboard.press("Escape")
                await asyncio.sleep(0.5) # Allow UI to react
            except Exception as e:
                await self.client.emit(
                    "on_warning", f"Error trying to close chat with Escape: {e}"
                )

    async def open(
        self, chat_name: str, timeout: int = DEFAULT_WAIT_TIMEOUT, open_via_url: bool = False
    ) -> bool:
        """
        Open a chat by name.

        Args:
            chat_name: Name of the chat to open
            timeout: Maximum time to wait in milliseconds
            open_via_url: If True, forces opening via URL (for phone numbers)

        Returns:
            True if chat was opened successfully, False otherwise
        """
        return await self.wa_elements.open(chat_name, timeout, open_via_url=open_via_url)

    async def search_conversations(
        self, query: str, close: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for conversations by term.

        Args:
            query: Search term
            close: If True, closes the search after completion

        Returns:
            List of matching conversations
        """
        if not await self.client.wait_until_logged_in():
            return []
        try:
            return await self.wa_elements.search_chats(query, close)
        except Exception as e:
            await self.client.emit("on_error", f"Search error: {e}")
            return []

    async def collect_messages(self) -> List[Union[Message, FileMessage]]:
        """
        Collect all currently visible messages in the active chat.

        Scans all visible message containers (message-in/message-out) and
        returns a list of Message or FileMessage instances.

        Returns:
            List of Message or FileMessage objects
        """
        results: List[Union[Message, FileMessage]] = []
        msg_elements = await self._page.query_selector_all(
            'div[class*="message-in"], div[class*="message-out"]'
        )

        for elem in msg_elements:
            # Try to parse as FileMessage first
            file_msg = await FileMessage.from_element(elem)
            if file_msg:
                results.append(file_msg)
                continue

            # Fall back to regular Message
            simple_msg = await Message.from_element(elem)
            if simple_msg:
                results.append(simple_msg)

        return results

    async def download_all_files(
        self, carpeta: Optional[str] = None
    ) -> List[Path]:
        """
        Download all file attachments from the current chat.

        Args:
            carpeta: Optional custom download directory path

        Returns:
            List of Path objects where files were saved
        """
        if not await self.client.wait_until_logged_in():
            return []

        downloads_dir = (
            Path(carpeta) if carpeta else DEFAULT_DOWNLOADS_DIR
        )

        saved_files: List[Path] = []
        messages = await self.collect_messages()

        for msg in messages:
            if isinstance(msg, FileMessage):
                file_path = await msg.download(self._page, downloads_dir)
                if file_path:
                    saved_files.append(file_path)

        return saved_files

    async def download_file_by_index(
        self, index: int, carpeta: Optional[str] = None
    ) -> Optional[Path]:
        """
        Download a specific file by its index in the message list.

        Args:
            index: Zero-based index of the file to download
            carpeta: Optional custom download directory path

        Returns:
            Path to the downloaded file or None if failed
        """
        if not await self.client.wait_until_logged_in():
            return None

        downloads_dir = (
            Path(carpeta) if carpeta else DEFAULT_DOWNLOADS_DIR
        )

        messages = await self.collect_messages()
        files = [m for m in messages if isinstance(m, FileMessage)]

        if index < 0 or index >= len(files):
            return None

        return await files[index].download(self._page, downloads_dir)

    async def send_message(
        self, chat_query: str, message: str, open_via_url: bool = False
    ) -> bool:
        """
        Send a text message to a chat.

        Args:
            chat_query: Name or identifier of the chat
            message: Text message to send
            open_via_url: If True, opens the chat via URL before sending

        Returns:
            True if message was sent successfully, False otherwise
        """
        print("Sending message...")
        if not await self.client.wait_until_logged_in():
            return False

        try:
            opened = await self.open(chat_query, open_via_url=open_via_url)
            if not opened:
                await self.client.emit(
                    "on_error", f"Could not open chat: {chat_query}"
                )
                return False
            print(f"✓ Chat '{chat_query}' opened, sending message")

            await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=DEFAULT_WAIT_TIMEOUT)
            input_box = await self._page.wait_for_selector(
                loc.CHAT_INPUT_BOX, timeout=DEFAULT_WAIT_TIMEOUT
            )

            if not input_box:
                await self.client.emit(
                    "on_error",
                    "Could not find text input box for sending message",
                )
                return False

            await input_box.click()
            await input_box.fill(message)
            await self._page.keyboard.press("Enter")
            
            # Add a short delay to allow the message to be processed by WhatsApp Web UI
            await asyncio.sleep(2)
            
            return True

        except Exception as e:
            await self._page.screenshot(path="send_message_error.png")
            await self.client.emit("on_error", f"Error sending message: {e}")
            return False
        finally:
            await self.close()

    async def send_file(self, chat_name: str, path: str) -> bool:
        """
        Send a file attachment to a chat.

        Args:
            chat_name: Name of the chat to send the file to
            path: Absolute path to the file to send

        Returns:
            True if file was sent successfully, False otherwise
        """
        try:
            if not os.path.isfile(path):
                msg = f"File does not exist: {path}"
                await self.client.emit("on_error", msg)
                return False

            if not await self.client.wait_until_logged_in():
                msg = "Could not log in"
                await self.client.emit("on_error", msg)
                return False

            if not await self.open(chat_name):
                msg = f"Could not open chat: {chat_name}"
                await self.client.emit("on_error", msg)
                return False

            await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=DEFAULT_WAIT_TIMEOUT)

            attach_btn = await self._page.wait_for_selector(
                loc.ATTACH_BUTTON, timeout=5000
            )
            await attach_btn.click()

            input_files = await self._page.query_selector_all(loc.FILE_INPUT)
            if not input_files:
                msg = "Could not find input[type='file']"
                await self.client.emit("on_error", msg)
                return False

            await input_files[0].set_input_files(path)
            await asyncio.sleep(1)

            send_btn = await self._page.wait_for_selector(
                loc.SEND_BUTTON, timeout=DEFAULT_WAIT_TIMEOUT
            )
            await send_btn.click()

            return True

        except Exception as e:
            msg = f"Unexpected error in send_file: {str(e)}"
            await self.client.emit("on_error", msg)
            await self._page.screenshot(path="send_file_error.png")
            return False
        finally:
            await self.close()

    async def new_group(self, group_name: str, members: List[str]) -> bool:
        """
        Create a new WhatsApp group.

        Args:
            group_name: Name for the new group
            members: List of member names to add to the group

        Returns:
            True if group was created successfully, False otherwise
        """
        return await self.wa_elements.new_group(group_name, members)

    async def add_members_to_group(
        self, group_name: str, members: List[str]
    ) -> bool:
        """
        Add members to an existing group.

        Args:
            group_name: Name of the group
            members: List of member names to add

        Returns:
            True if members were added successfully, False otherwise
        """
        try:
            if not await self.open(group_name):
                await self.client.emit(
                    "on_error", f"Could not open group '{group_name}'"
                )
                return False

            success = await self.wa_elements.add_members_to_group(group_name, members)
            return success

        except Exception as e:
            await self.client.emit(
                "on_error", f"Error adding members to group '{group_name}': {e}"
            )
            return False
