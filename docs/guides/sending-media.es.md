# Guía: Envío y recepción de multimedia

WhatsPlay facilita el trabajo con archivos como imágenes, videos, documentos y notas de voz. Esta guía cubre tanto el envío de archivos desde tu disco local como la descarga de multimedia desde un chat.

## Enviar multimedia

Usa `client.send_file()` para enviar cualquier tipo de archivo. Indica el destinatario (nombre del chat o número de teléfono) y la ruta local del archivo.

```python
await client.send_file(chat_name, path, open_via_url=False, is_group=None)
```

Al igual que `send_message()`, devuelve `True` solo cuando WhatsApp muestra el nuevo mensaje con un estado de entrega, y `False` en caso contrario (el motivo queda registrado).

### Ejemplo: enviar una imagen

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
        recipient = "NUMERO_DE_TELEFONO_O_NOMBRE_DE_CONTACTO"
        file_path = Path("/path/to/your/image.jpg")

        if not file_path.exists():
            print(f"Error: no se encontró el archivo en {file_path}")
            await client.stop()
            return

        if await client.send_file(recipient, str(file_path)):
            print(f"Multimedia enviada a {recipient}.")
        else:
            print(f"No se pudo confirmar el envío de multimedia a {recipient}.")

        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Escanea el código QR para iniciar sesión.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(send_media_file())
```

Puedes usar el mismo método `client.send_file()` para cualquier tipo de archivo, incluidos:
*   Imágenes (`.jpg`, `.png`, etc.)
*   Videos (`.mp4`, `.mov`, etc.)
*   Documentos (`.pdf`, `.docx`, `.zip`, etc.)
*   Archivos de audio (`.mp3`, `.ogg`, etc.)

## Descargar multimedia

Las descargas funcionan sobre el chat que está abierto, así que primero llama a `client.open()`.

### Usar `client.download_all_files()`

Descarga todos los archivos y notas de voz cargados en el chat abierto a `carpeta` (por defecto: `~/Downloads/WhatsAppFiles`). Devuelve una lista de diccionarios:

*   `path` (`Path`): dónde se guardó el archivo.
*   `type` (str): `"FileMessage"` o `"VoiceMessage"`.
*   `codec` (str): el códec de audio detectado, cuando `detect_codecs=True` y se encuentra uno.

```python
await client.open("Family Group")

files = await client.download_all_files(carpeta="./downloads/family")

for info in files:
    print(info["type"], info["path"], info.get("codec"))
```

### Usar `client.download_file_by_index()`

Descarga un archivo según su posición entre los archivos cargados en el chat abierto:

*   `index=0`: el primer archivo (el más antiguo).
*   `index=-1`: el último archivo (el más reciente).

Devuelve un diccionario con `path` y `type`, o `None` si no se descargó nada.

```python
await client.open("My Group")

result = await client.download_file_by_index(index=-1, carpeta="./downloads")

if result:
    print(f"Último archivo guardado en: {result['path']}")
```

### Descargar desde los mensajes recopilados

`collect_messages()` devuelve objetos `FileMessage` y `VoiceMessage` para los archivos adjuntos y las notas de voz. Puedes descargarlos de forma individual:

```python
from pathlib import Path
from whatsplay import FileMessage, VoiceMessage

await client.open("My Group")
messages = await client.collect_messages()

for msg in messages:
    if isinstance(msg, VoiceMessage):
        print(f"Nota de voz: {msg.duration}")
    if isinstance(msg, (FileMessage, VoiceMessage)):
        saved = await msg.download(msg.page, Path("./downloads"))
        print(f"Guardado: {saved}")
```

> **Nota:** no pases `dispose=True` a `collect_messages()` si piensas descargar esos mensajes o reaccionar a ellos: `dispose` libera los handles del navegador que necesitan.
