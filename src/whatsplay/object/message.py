# models.py
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.async_api import Page, ElementHandle, Download
import asyncio

class Message:
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
        try:
            # 0) Dirección (in/out) e ID si existe
            classes = (await elem.get_attribute("class")) or ""
            is_outgoing = "message-out" in classes  # entrante: message-in
            msg_id = (await elem.get_attribute("data-id")) or ""

            # 1) remitente
            sender = ""
            remitente_span = await elem.query_selector(
                'xpath=.//span[@aria-label and substring(@aria-label, string-length(@aria-label))=":"]'
            )
            if remitente_span:
                raw_label = await remitente_span.get_attribute("aria-label")
                if raw_label:
                    sender = raw_label.rstrip(":").strip()

            # 2) hora
            timestamp = datetime.now()
            time_span = await elem.query_selector('xpath=.//span[contains(@class,"x16dsc37")]')
            if time_span:
                hora_text = (await time_span.inner_text()).strip().lower()
                # Formatos esperados: "10:30", "10:30 am", "10:30 p.m."
                match = re.match(r'(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?|)?', hora_text)
                if match:
                    hh = int(match.group(1))
                    mm = int(match.group(2))
                    ampm = (match.group(3) or "").replace(".", "")

                    if ampm == 'pm' and hh != 12:
                        hh += 12
                    elif ampm == 'am' and hh == 12: # Medianoche
                        hh = 0
                    
                    ahora = datetime.now()
                    timestamp = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)

            # 3) texto
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
        Reacts to this message with the given emoji, following the user-verified workflow.
        """
 
        try:
            # 1. Hover over the message to make the action bar appear.
            await self.container.hover()
            
            # Take screenshot after hover
            await self.container.screenshot(path="after_hover.png")
            print("self.container: ", self.container)
            await asyncio.sleep(1.5)
            input("presiona enter para continuar")

            # 2. The user confirmed a button with aria-label="Reaccionar" appears first.
            # We wait for it to ensure the hover menu is open.
            # This is likely the default reaction button, but it makes the '+' button visible.
            reaction_bar = self.page.locator('[aria-label="Reaccionar"]')
            if not reaction_bar:
                print("Error: No se encontró el botón '[aria-label=\"Reaccionar\"]'.")
                return None
            await reaction_bar.click()

            # 3. The user confirmed they must then click a button with aria-label="Más reacciones" to open the picker.
            more_reactions_button_handle = self.page.locator('[aria-label="Más reacciones"]')
            if not more_reactions_button_handle:
                print("Error: No se encontró el botón '[aria-label=\"Más reacciones\"]'.")
                return None
            
            await more_reactions_button_handle.click()

            # 4. The emoji picker appears on the main page. We now use the main page object.
            # We also use the correct selector for emojis, which is their aria-label.
            
            # The selector finds the picker and then the specific emoji inside it.
            emoji_in_picker = self.page.locator(f'[data-emoji="{emoji}"]')

            # 5. Wait for the emoji to be visible and click it.
            await emoji_in_picker.wait_for(state="visible", timeout=5000)
            await emoji_in_picker.click()

            print(f"Successfully reacted with '{emoji}'")

        except Exception as e:
            print(f"An error occurred while reacting to message {self.msg_id}: {e}")





class FileMessage(Message):
    """
    Representa un mensaje que contiene un archivo descargable.
    Extiende a Message y añade:
      - filename: nombre real del archivo (p.ej. "SoftwareDeveloper_JeanRoa_ES.pdf")
      - download_icon: ElementHandle apuntando al <span data-icon="audio-download">
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
        Dado el <div> que engloba un mensaje completo, intenta:
          1) Localizar un <span data-icon="audio-download"> dentro de `elem`.
          2) Si existe, determina el filename leyendo el atributo title del ancestro más cercano
             que tenga algo como title="Download \"NombreDelArchivo.ext\"".
          3) Llama internamente a Message.from_element para extraer remitente, timestamp y texto.
          4) Si todo OK, retorna FileMessage; de lo contrario, retorna None.
        """
        try:
            # 1) ¿HAY ICONO DE DESCARGA?
            icon = await elem.query_selector('span[data-icon="audio-download"]')
            if not icon:
                return None

            # 2) BUSCAR NOMBRE DE ARCHIVO
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

            # 3) EXTRAER DATOS BASE DEL MENSAJE
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
        Hace clic en self.download_icon y espera el evento de descarga.
        Luego guarda el archivo en `downloads_dir/filename` y retorna la Path resultante.
        Si algo falla, devuelve None.
        """
        try:
            # 1) CREAR DIRECTORIO SI NO EXISTE
            downloads_dir.mkdir(parents=True, exist_ok=True)

            # 2) ESPERAR DESCARGA
            async with page.expect_download() as evento:
                await self.download_icon.click()
            descarga: Download = await evento.value

            # 3) OBTENER NOMBRE SUGERIDO
            suggested = descarga.suggested_filename or self.filename
            destino = downloads_dir / suggested

            # 4) GUARDAR EN DISCO
            await descarga.save_as(str(destino))
            return destino

        except Exception:
            return None