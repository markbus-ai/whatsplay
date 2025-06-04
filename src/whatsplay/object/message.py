# models.py
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Union
from playwright.async_api import Page, ElementHandle, Download


class Message:
    """
    Representa un mensaje genérico de WhatsApp Web.
    Extrae:
      - sender: el remitente (ej. “Mom”, “Marcos”, etc.)
      - timestamp: hora (y fecha aproximada, usando la hora del sistema)
      - text: cuerpo textual del mensaje (si existe)
      - container: el propio ElementHandle del <div class="message-in/out ...">
    """
    def __init__(
        self,
        sender: str,
        timestamp: datetime,
        text: str,
        container: ElementHandle
    ):
        self.sender = sender
        self.timestamp = timestamp
        self.text = text
        self.container = container

    @classmethod
    async def from_element(cls, elem: ElementHandle) -> Optional["Message"]:
        """
        Crea un Message a partir del <div> que engloba TODO el mensaje.
        - Busca dentro de `elem` un <span aria-label="X:"> para extraer `sender`.
        - Busca <span class*="x16dsc37"> para extraer la hora (formato HH:MM).
        - El texto del mensaje (texto libre) se obtiene con inner_text,
          limpiando la primera línea si coincide con el remitente/hora.
        Si no logra extraer nada relevante, retorna None.
        """
        try:
            # 1) EXTRAER REMITENTE
            sender = ""
            remitente_span = await elem.query_selector('span[aria-label$=":"]')
            if remitente_span:
                raw_label = await remitente_span.get_attribute("aria-label")  # e.g. "Mom:"
                if raw_label:
                    sender = raw_label.rstrip(":").strip()

            # 2) EXTRAER HORA
            timestamp = datetime.now()
            time_span = await elem.query_selector('span[class*="x16dsc37"]')
            if time_span:
                hora_text = (await time_span.inner_text()).strip()  # e.g. "13:40"
                if ":" in hora_text:
                    ahora = datetime.now()
                    hh, mm = [int(x) for x in hora_text.split(":")]
                    timestamp = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)

            # 3) EXTRAER TEXTO DEL MENSAJE
            #    inner_text normalmente trae primera línea “[Mom:]” y luego el cuerpo real.
            texto = ""
            raw_inner = await elem.inner_text()
            if raw_inner:
                lineas = raw_inner.split("\n")
                # Si la primera línea contiene el remitente o la hora, la descartamos
                if len(lineas) > 1:
                    texto = "\n".join(lineas[1:]).strip()
                else:
                    texto = ""

            # 4) Retornar instancia
            return cls(sender=sender, timestamp=timestamp, text=texto, container=elem)

        except Exception:
            return None


class FileMessage(Message):
    """
    Representa un mensaje que contiene un archivo descargable.
    Extiende a Message y añade:
      - filename: nombre real del archivo (p.ej. "SoftwareDeveloper_JeanRoa_ES.pdf")
      - download_icon: ElementHandle apuntando al <span data-icon="audio-download">
    """
    def __init__(
        self,
        sender: str,
        timestamp: datetime,
        text: str,
        container: ElementHandle,
        filename: str,
        download_icon: ElementHandle
    ):
        super().__init__(sender, timestamp, text, container)
        self.filename = filename
        self.download_icon = download_icon

    @classmethod
    async def from_element(cls, elem: ElementHandle) -> Optional["FileMessage"]:
        """
        Dado el <div> que engloba un mensaje completo, intenta:
          1) Localizar un <span data-icon="audio-download"> dentro de `elem`.
          2) Si existe, determina el filename leyendo el atributo title del ancestro más cercano
             que tenga algo como title="Download \"NombreDelArchivo.ext\"".
          3) Llama internamente a Message.from_element para extraer remitente, timestamp y texto.
          4) Si todo OK, retorna FileMessage; de lo contrario, retorna None.
        """
        try:
            # 1) ¿Hay icono de descarga en este mensaje?
            icon = await elem.query_selector('span[data-icon="audio-download"]')
            if not icon:
                return None

            # 2) BUSCAR NOMBRE DE ARCHIVO (dentro de un ancestro con atributo title="Download ...")
            filename = ""
            # Subimos por los ancestros hasta encontrar un nodo con atributo title que comience por "Download"
            title_handle = await icon.evaluate_handle(
                """(node) => {
                    let curr = node;
                    while (curr) {
                        if (curr.title && curr.title.startsWith("Download")) {
                            return curr;
                        }
                        curr = curr.parentElement;
                    }
                    return null;
                }"""
            )
            if title_handle:
                title_elem: ElementHandle = title_handle.as_element()
                if title_elem:
                    raw_title = await title_elem.get_attribute("title")
                    # raw_title = 'Download "SoftwareDeveloper_JeanRoa_ES.pdf"'
                    if raw_title and '"' in raw_title:
                        parts = raw_title.split('"')
                        if len(parts) >= 2:
                            filename = parts[1].strip()

            # Si no obtuvimos filename, abortamos
            if not filename:
                return None

            # 3) Extraer el mensaje base
            base_msg = await Message.from_element(elem)
            if not base_msg:
                return None

            return cls(
                sender=base_msg.sender,
                timestamp=base_msg.timestamp,
                text=base_msg.text,
                container=elem,
                filename=filename,
                download_icon=icon
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
            # 1) Preparamos carpeta
            downloads_dir.mkdir(parents=True, exist_ok=True)

            # 2) Escuchar la descarga
            async with page.expect_download() as evento:
                await self.download_icon.click()
            descarga: Download = await evento.value

            # 3) Determinar nombre final (si el servidor sugiere distinto, lo usamos)
            suggested = descarga.suggested_filename or self.filename
            destino = downloads_dir / suggested

            # 4) Guardar en disco
            await descarga.save_as(str(destino))
            return destino

        except Exception:
            return None
