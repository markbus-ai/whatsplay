# Guía: Manejo de Mensajes Entrantes

WhatsPlay utiliza un mecanismo de sondeo (polling) activo para detectar nuevos mensajes. En lugar de esperar pasivamente un evento de mensaje, el cliente verifica periódicamente si hay indicadores de "no leído" en tu lista de chats.

Esto te da control total sobre cuándo y cómo procesas nuevas conversaciones.

## El Evento `on_unread_chat`

Este es el evento principal para detectar nueva actividad. Se dispara cada vez que WhatsPlay encuentra uno o más chats con mensajes no leídos.

El manejador del evento recibe una lista de diccionarios, donde cada diccionario contiene información básica sobre el chat no leído (nombre, vista previa del último mensaje, contador de no leídos, etc.).

### Patrón Básico: Detectar, Abrir y Leer

Para leer el contenido real de los mensajes, necesitas:
1.  Escuchar el evento `on_unread_chat`.
2.  Iterar a través de los chats detectados.
3.  **Abrir** cada chat usando `client.open()`.
4.  **Recolectar** los mensajes usando `client.collect_messages()`.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def auto_reply_bot():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("¡Bot iniciado! Buscando nuevos mensajes...")

    @client.event("on_unread_chat")
    async def on_unread_chat(chats):
        """
        Se dispara cuando hay chats no leídos.
        'chats' es una lista de dicts: [{'name': 'Juan', 'unread_count': '2', ...}, ...]
        """
        print(f"Se encontraron {len(chats)} chats con nuevos mensajes.")

        for chat_info in chats:
            chat_name = chat_info.get('name')
            print(f"Procesando chat: {chat_name}")

            # 1. Abrir el chat para cargar los mensajes
            if await client.open(chat_name):
                
                # 2. Recolectar mensajes visibles
                messages = await client.collect_messages()
                
                if messages:
                    last_message = messages[-1]
                    sender = last_message.sender.name or "Desconocido"
                    text = last_message.text
                    
                    print(f"  Último mensaje de {sender}: {text}")

                    # 3. Lógica simple de Auto-respuesta
                    if text and "hola" in text.lower():
                        await client.send_message(chat_name, "¡Hola! Soy un bot de WhatsPlay. 🤖")
                        print(f"  -> Respondido a {chat_name}")
                    
                    # Opcional: Marcar como leído o archivar (la lógica depende de tus necesidades)
                    # Actualmente, abrir el chat lo marca como leído en WhatsApp.
            else:
                print(f"  Falló al abrir el chat: {chat_name}")

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(auto_reply_bot())
```

## Procesando Mensajes

El método `client.collect_messages()` devuelve una lista de objetos `Message`. Estos son los mismos objetos descritos en la Referencia de la API.

### Atributos Comunes de `Message`

*   `message.text`: El contenido de texto.
*   `message.timestamp`: Hora en que se recibió el mensaje.
*   `message.sender.name`: Nombre del remitente.
*   `message.is_media`: `True` si es una imagen, video, etc.

### Filtrado

Dado que obtienes una lista de mensajes (usualmente los últimos visibles), podrías querer filtrarlos. Aunque los filtros de `on_message` (mencionados en otros contextos) son para futuras APIs de streaming, puedes filtrar fácilmente la lista manualmente o usando herramientas integradas de Python.

```python
# Ejemplo: Obtener solo mensajes que contengan "urgente"
mensajes_relevantes = [
    m for m in messages 
    if "urgente" in (m.text or "").lower()
]
```

## Nota sobre `on_message`

Podrías ver referencias a un evento `on_message` en el código fuente. Este evento está actualmente **reservado para uso futuro** y no es emitido automáticamente por el bucle principal. Por favor, utiliza el patrón `on_unread_chat` descrito anteriormente para construir bots y herramientas de automatización.
