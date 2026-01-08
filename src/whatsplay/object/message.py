# models.py
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.async_api import Page, ElementHandle, Download
import asyncio

class Message:
    """
    Represents a WhatsApp message.

    This object encapsulates all data related to a single message in a chat,
    including its content, sender, timestamp, and interactivity methods.

    Attributes:
        page (Page): The Playwright Page object.
        sender (str): The name or phone number of the sender.
        timestamp (datetime): The time the message was received.
        text (str): The text content of the message.
        container (ElementHandle): The DOM element containing the message.
        is_outgoing (bool): True if the message was sent by the user, False otherwise.
        msg_id (str): The unique identifier of the message.
    """

    def __init__(self, page: Page, sender: str, timestamp: datetime, text: str, container: ElementHandle,
                 is_outgoing: bool = False, msg_id: str = ""):
        self.page = page
        self.sender = sender
        self.timestamp = timestamp
        self.text = text
        self.container = container
        self.is_outgoing = is_outgoing
        self.msg_id = msg_id

    @classmethod
    async def from_element(cls, elem: ElementHandle, page: Page) -> Optional["Message"]:
        """
        Create a Message instance from a DOM element.

        Args:
            elem: The message container element.
            page: The Playwright page.

        Returns:
            A new Message instance or None if parsing fails.
        """
        try:
            # 0) Direction (in/out) and ID if exists
            classes = (await elem.get_attribute("class")) or ""
            is_outgoing = "message-out" in classes  # incoming: message-in
            msg_id = (await elem.get_attribute("data-id")) or ""

            # 1) Sender
            sender = ""
            remitente_span = await elem.query_selector(
                'xpath=.//span[@aria-label and substring(@aria-label, string-length(@aria-label))=":"]'
            )
            if remitente_span:
                raw_label = await remitente_span.get_attribute("aria-label")
                if raw_label:
                    sender = raw_label.rstrip(":").strip()

            # 2) Timestamp
            timestamp = datetime.now()
            time_span = await elem.query_selector('xpath=.//span[contains(@class,"x16dsc37")]')
            if time_span:
                hora_text = (await time_span.inner_text()).strip().lower()
                # Expected formats: "10:30", "10:30 am", "10:30 p.m."
                match = re.match(r'(\d{1,2}):(\d{2})\s*(a\.?.m\.?|p\.?.m\.?|)?', hora_text)
                if match:
                    hh = int(match.group(1))
                    mm = int(match.group(2))
                    ampm = (match.group(3) or "").replace(".", "")

                    if ampm == 'pm' and hh != 12:
                        hh += 12
                    elif ampm == 'am' and hh == 12: # Midnight
                        hh = 0
                    
                    ahora = datetime.now()
                    timestamp = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)

            # 3) Text
            texto = ""
            cuerpo_div = await elem.query_selector('xpath=.//div[contains(@class,"copyable-text")]/div')
            if cuerpo_div:
                raw_inner = await cuerpo_div.inner_text()
                if raw_inner:
                    lineas = raw_inner.split("\n")
                    if len(lineas) > 1 and (lineas[0].strip().startswith(sender) or ":" in lineas[0]):
                        texto = "\n".join(lineas[1:]).strip()
                    else:
                        texto = raw_inner.strip()

            return cls(
                page=page, sender=sender, timestamp=timestamp, text=texto, container=elem,
                is_outgoing=is_outgoing, msg_id=msg_id
            )
        except Exception:
            return None
            
    async def react(self, emoji: str):
        """
        Reacts to this message with the given emoji.

        This method simulates the user interaction of hovering over the message,
        clicking the reaction button, and selecting an emoji.

        Args:
            emoji (str): The emoji character to react with (e.g., "👍", "❤️").
        """
 
        try:
            # 1. Hover over the message to make the action bar appear.
            await self.container.hover()
            
            # Take screenshot after hover
            # await self.container.screenshot(path="after_hover.png")
            # print("self.container: ", self.container)
            await asyncio.sleep(0.5)
            # input("presiona enter para continuar")

            # 2. Find reaction button
            reaction_bar = self.page.locator('[aria-label="Reaccionar"]')
            if not reaction_bar:
                # print("Error: No se encontró el botón '[aria-label="Reaccionar"]'.")
                return None
            await reaction_bar.click()

            # 3. Find "More reactions" button
            more_reactions_button_handle = self.page.locator('[aria-label="Más reacciones"]')
            if not more_reactions_button_handle:
                # print("Error: No se encontró el botón '[aria-label="Más reacciones"]'.")
                return None
            
            await more_reactions_button_handle.click()

            # 4. Find emoji in picker
            emoji_in_picker = self.page.locator(f'[data-emoji="{emoji}"]')

            # 5. Click emoji
            await emoji_in_picker.wait_for(state="visible", timeout=5000)
            await emoji_in_picker.click()

            # print(f"Successfully reacted with '{emoji}'")

        except Exception as e:
            print(f"An error occurred while reacting to message {self.msg_id}: {e}")


class FileMessage(Message):
    """
    Represents a message containing a downloadable file.

    Inherits from `Message` and adds specific functionality for handling
    media and document attachments.

    Attributes:
        filename (str): The name of the file (e.g., "document.pdf").
        download_icon (ElementHandle): The DOM element for the download button.
    """

    def __init__(
        self,
        page: Page,
        sender: str,
        timestamp: datetime,
        text: str,
        container: ElementHandle,
        filename: str,
        download_icon: ElementHandle,
    ):
        super().__init__(page, sender, timestamp, text, container)
        self.filename = filename
        self.download_icon = download_icon

    @classmethod
    async def from_element(cls, elem: ElementHandle, page: Page) -> Optional["FileMessage"]:
        """
        Create a FileMessage from a DOM element.

        Checks for the presence of a download icon and attempts to parse the filename.

        Args:
            elem: The message container element.
            page: The Playwright page.

        Returns:
            A new FileMessage instance or None if not a valid file message.
        """
        try:
            # 1) Check for download icon
            icon = await elem.query_selector('span[data-icon="audio-download"]')
            if not icon:
                return None

            # 2) Find filename
            filename = ""
            title_handle = await icon.evaluate_handle(
                """
                (node) => {
                    let curr = node;
                    while (curr) {
                        if (curr.title && curr.title.startsWith("Download")) {
                            return curr;
                        }
                        curr = curr.parentElement;
                    }
                    return null;
                }
            """
            )

            if title_handle:
                title_elem: ElementHandle = title_handle.as_element()
                if title_elem:
                    raw_title = await title_elem.get_attribute("title")
                    if raw_title and '"' in raw_title:
                        parts = raw_title.split('"')
                        if len(parts) >= 2:
                            filename = parts[1].strip()

            if not filename:
                return None

            # 3) Extract base message data
            base_msg = await Message.from_element(elem, page)
            if not base_msg:
                return None

            return cls(
                page=page,
                sender=base_msg.sender,
                timestamp=base_msg.timestamp,
                text=base_msg.text,
                container=elem,
                filename=filename,
                download_icon=icon,
            )

        except Exception:
            return None

    async def download(self, page: Page, downloads_dir: Path) -> Optional[Path]:
        """
        Download the attached file.

        Clicks the download icon and waits for the download to complete.

        Args:
            page: The Playwright Page object.
            downloads_dir: The directory where the file should be saved.

        Returns:
            The Path to the saved file, or None if the download failed.
        """
        try:
            # 1) Create directory
            downloads_dir.mkdir(parents=True, exist_ok=True)

            # 2) Wait for download
            async with page.expect_download() as evento:
                await self.download_icon.click()
            descarga: Download = await evento.value

            # 3) Get filename and path
            suggested = descarga.suggested_filename or self.filename
            destino = downloads_dir / suggested

            # 4) Save to disk
            await descarga.save_as(str(destino))
            return destino

        except Exception:
            return None
