# Guía: Manejo de Mensajes Entrantes

La arquitectura basada en eventos de WhatsPlay hace fácil reaccionar a mensajes entrantes en tiempo real. Esta guía te mostrará cómo configurar manejadores para mensajes y cómo filtrarlos.

## El Evento `on_message`

El núcleo del manejo de mensajes entrantes es suscribirse al evento `on_message`. Tu función manejadora recibirá un objeto `message` que contiene todos los detalles sobre el mensaje entrante.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.event import Message

async def basic_message_handler():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Cliente listo. Esperando mensajes...")

    # Este manejador será llamado para cada mensaje entrante
    @client.event("on_message")
    async def handle_any_message(message: Message):
        print(f"¡Recibí un mensaje!")
        print(f"  De: {message.sender.name or message.sender.id}")
        print(f"  Chat: {message.chat.name or message.chat.id}")
        print(f"  Texto: {message.text}")
        
        # Ejemplo: Responder al remitente
        if message.text and "hola" in message.text.lower():
            await message.reply("¡Hola! ¿Cómo puedo ayudarte?")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR para iniciar sesión.")

    # Mantén el cliente corriendo indefinidamente para escuchar mensajes
    await client.start()
    # Podrías querer añadir client.run_forever() aquí si tu script es solo para escuchar
    # Sin embargo, para ejemplos simples, client.start() es suficiente si no llamas a client.stop() inmediatamente.

if __name__ == "__main__":
    asyncio.run(basic_message_handler())
```

## Filtrando Mensajes

WhatsPlay proporciona capacidades de filtrado potentes para ayudarte a procesar solo los mensajes que te interesan. Puedes pasar un objeto filtro al decorador del evento `on_message`.

### Usando Filtros Predefinidos

El módulo `whatsplay.filters` ofrece varios filtros listos para usar.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.event import Message
from whatsplay.filters import message_filter

async def filtered_message_handler():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Cliente listo. Esperando mensajes filtrados...")

    # Solo manejar mensajes que son texto (no multimedia, etc.)
    @client.event("on_message", message_filter.text)
    async def handle_text_message(message: Message):
        print(f"Recibí un mensaje de TEXTO de {message.sender.name or message.sender.id}: {message.text}")

    # Solo manejar mensajes de un remitente específico (por nombre o ID)
    @client.event("on_message", message_filter.sender("Juan Pérez"))
    async def handle_message_from_john(message: Message):
        print(f"Recibí un mensaje de Juan Pérez: {message.text}")

    # Solo manejar mensajes que coincidan con una expresión regular
    @client.event("on_message", message_filter.regex(r"^\/comando"))
    async def handle_command_message(message: Message):
        print(f"Recibí un comando: {message.text}")
        await message.reply("¡Comando recibido!")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR para iniciar sesión.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(filtered_message_handler())
```

### Creando Filtros Personalizados

También puedes definir tus propias funciones de filtro o clases para lógica más compleja. Una función de filtro debe aceptar un objeto `message` y devolver `True` si el mensaje debe ser procesado por el manejador, `False` en caso contrario.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth
from whatsplay.event import Message
from whatsplay.filters import CustomFilter

# Función de filtro personalizada
def my_custom_filter(message: Message) -> bool:
    # Solo procesar mensajes que contengan "importante" y sean de un tipo de chat específico
    return message.text and "importante" in message.text.lower() and message.chat.is_group

# O una clase CustomFilter (más potente para filtros reutilizables y con estado)
class MyChatIdFilter(CustomFilter):
    def __init__(self, chat_id_to_match: str):
        self.chat_id_to_match = chat_id_to_match

    def __call__(self, message: Message) -> bool:
        return message.chat.id == self.chat_id_to_match


async def custom_filtered_message_handler():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Cliente listo. Esperando mensajes filtrados personalizados...")

    # Usando la función de filtro personalizada
    @client.event("on_message", my_custom_filter)
    async def handle_custom_filtered_message(message: Message):
        print(f"Recibí un mensaje 'importante' en un grupo de {message.sender.name}: {message.text}")

    # Usando la clase de filtro personalizada
    target_chat_id = "1234567890@g.us" # Reemplaza con un ID de chat real
    @client.event("on_message", MyChatIdFilter(target_chat_id))
    async def handle_specific_chat_message(message: Message):
        print(f"Recibí mensaje en chat específico ({target_chat_id}): {message.text}")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR para iniciar sesión.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(custom_filtered_message_handler())
```

## Accediendo a Datos del Mensaje

El objeto `Message` pasado a tu manejador contiene una gran cantidad de información sobre el mensaje entrante. Algunos atributos clave incluyen:

*   `message.id`: ID único del mensaje.
*   `message.text`: El contenido de texto del mensaje (si hay).
*   `message.sender`: Un objeto `User` representando al remitente (con `name` e `id`).
*   `message.chat`: Un objeto `Chat` representando la conversación (con `name`, `id`, `is_group`, `is_user`).
*   `message.timestamp`: Cuándo fue enviado el mensaje.
*   `message.is_media`: Booleano, `True` si el mensaje contiene multimedia (imagen, video, etc.).
*   `message.media_type`: Tipo de medio, ej., 'image', 'video', 'document'.
*   `message.download_media()`: Un método "awaitable" para descargar medios adjuntos.
*   `message.reply(text)`: Un método "awaitable" para responder directamente a este mensaje.

¡Esta guía proporciona la base para construir aplicaciones de WhatsPlay interactivas y receptivas. Combina el manejo de mensajes con filtros para crear escenarios de automatización potentes!