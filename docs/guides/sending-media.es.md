# Guía: Envío y Recepción de Archivos Multimedia

WhatsPlay hace fácil trabajar con multimedia como imágenes, videos y documentos. Esta guía cubre tanto el envío de archivos desde tu disco local como la descarga de medios de mensajes entrantes.

## Enviando Multimedia

El método principal para enviar cualquier tipo de archivo es `client.send_file()`. Necesitas proporcionar el destinatario (nombre de chat o ID) y la ruta local al archivo. WhatsPlay manejará el resto.

También puedes proporcionar un `caption` opcional para el medio.

### Ejemplo: Enviando una Imagen con una Leyenda

Este script envía un archivo de imagen local a un destinatario especificado.

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
        print("Cliente listo. Enviando una imagen...")
        
        recipient = "NUMERO_DE_TELEFONO_O_NOMBRE_DE_CONTACTO"
        
        # Asegúrate de tener una imagen en esta ruta
        # Por ejemplo: /home/user/pictures/mi_imagen.jpg
        file_path = Path("/path/to/your/image.jpg")
        caption = "¡Aquí hay una foto desde WhatsPlay! 🖼️"

        if not file_path.exists():
            print(f"Error: Archivo no encontrado en {file_path}")
            await client.stop()
            return

        success = await client.send_file(recipient, file_path, caption=caption)
        
        if success:
            print(f"Multimedia enviada exitosamente a {recipient}.")
        else:
            print(f"Falló el envío de multimedia a {recipient}.")
            
        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR para iniciar sesión.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(send_media_file())
```

Puedes usar el mismo método `client.send_file()` para cualquier tipo de archivo, incluyendo:
*   Imágenes (`.jpg`, `.png`, etc.)
*   Videos (`.mp4`, `.mov`, etc.)
*   Documentos (`.pdf`, `.docx`, `.zip`, etc.)
*   Archivos de audio (`.mp3`, `.ogg`, etc.)

## Descargando Multimedia

Cuando recibes un mensaje que contiene multimedia, el objeto `Message` proporciona una forma conveniente de descargarlo.

1.  Verifica si el mensaje contiene medios usando `message.is_media`.
2.  Si lo hace, llama al método `await message.download_media()`.

Este método descarga el archivo a una ubicación especificada. Si no se proporciona una ruta, puede usar un directorio por defecto.

### Ejemplo: Bot Auto-descargador

Este bot descarga automáticamente cualquier medio que recibe.

```python
import asyncio
from pathlib import Path
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.event import Message

async def media_downloader_bot():
    # Crear un directorio para guardar archivos descargados
    download_dir = Path("./media_downloads")
    download_dir.mkdir(exist_ok=True)
    
    print(f"Guardaré los medios descargados en: {download_dir.resolve()}")

    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Bot descargador iniciado. Esperando medios...")

    @client.event("on_message")
    async def handle_message(message: Message):
        if message.is_media:
            print(f"Recibí medio de tipo '{message.media_type}' de {message.sender.name or message.sender.id}.")
            
            # Definir una ruta para guardar el archivo
            # Puedes personalizar el nombre de archivo, aquí usamos el ID del mensaje
            save_path = download_dir / f"{message.id}-{message.media_filename or 'download'}"
            
            print(f"Descargando a {save_path}...")
            
            try:
                await message.download_media(save_path)
                print("¡Descarga exitosa!")
                await message.reply(f"¡Gracias! He guardado el archivo como {save_path.name}.")
            except Exception as e:
                print(f"Error descargando archivo: {e}")
                await message.reply("Lo siento, tuve un error intentando descargar tu archivo.")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR para iniciar sesión.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(media_downloader_bot())
```

Este bot escuchará mensajes entrantes, y si uno contiene multimedia, intentará descargarlo en la carpeta `media_downloads` en tu directorio de proyecto.