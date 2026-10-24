# Guía: Manejo de mensajes entrantes

WhatsPlay usa un mecanismo de sondeo (polling) activo para detectar nuevos mensajes. En lugar de esperar pasivamente un evento de mensaje, el cliente verifica periódicamente si hay indicadores de "no leído" en tu lista de chats.

Esto te da control total sobre cuándo y cómo procesas las nuevas conversaciones.

## El evento `on_unread_chat`

Este es el evento principal para detectar nueva actividad. Se dispara cada vez que WhatsPlay encuentra uno o más chats con mensajes no leídos.

Cada escaneo primero selecciona el filtro **Todos** y desplaza la lista de chats hasta arriba, de modo que los chats no leídos se encuentran sin importar dónde quedó la lista. El primer escaneo se ejecuta unos 10 segundos después de iniciar sesión.

### Estructura del payload

El manejador del evento recibe una lista de diccionarios. Cada diccionario representa un chat no leído y contiene las siguientes claves:

*   **`name`** (str): el nombre visible del chat (nombre del contacto, título del grupo o número de teléfono).
*   **`unread_count`** (str): el número de mensajes no leídos (por ejemplo, "3").
*   **`last_message`** (str): una vista previa del último mensaje mostrado en la barra lateral.
*   **`last_activity`** (str): la hora o fecha del último mensaje (por ejemplo, "10:30 PM", "Ayer").
*   **`type`** (str): normalmente "CHATS".
*   **`group`** (str o None): el nombre del grupo si es un chat grupal, o vacío si es un mensaje directo.
*   **`last_message_type`** (str): `"audio"` para notas de voz; de lo contrario, `"text"`.

El payload contiene solo datos simples, sin handles del navegador.

### Patrón básico: detectar, abrir y leer

Para leer el contenido real de los mensajes, necesitas:
1.  Escuchar `on_unread_chat`.
2.  Recorrer los chats detectados.
3.  **Abrir** cada chat usando `client.open()`.
4.  **Recopilar** los mensajes usando `client.collect_messages()`.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def auto_reply_bot():
    auth = LocalProfileAuth(data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_logged_in")
    async def on_logged_in():
        print("¡Bot iniciado! Esperando mensajes nuevos...")

    @client.event("on_unread_chat")
    async def on_unread_chat(chats):
        """'chats' es una lista de dicts: [{'name': 'John', 'unread_count': '2', ...}, ...]"""
        for chat_info in chats:
            chat_name = chat_info["name"]

            # 1. Abrir el chat (False si no se puede verificar o el título es ambiguo).
            #    Pasa is_group=True/False cuando un grupo y un contacto pueden compartir nombre.
            if not await client.open(chat_name):
                print(f"No se pudo abrir el chat: {chat_name}")
                continue

            # 2. Recopilar los mensajes cargados
            messages = await client.collect_messages()
            incoming = [m for m in messages if not m.is_outgoing]

            if incoming:
                last = incoming[-1]
                print(f"  Último mensaje de {last.sender or 'Desconocido'}: {last.text}")

                # 3. Lógica simple de respuesta automática
                if last.text and "hola" in last.text.lower():
                    await client.send_message(chat_name, "¡Hola! Soy un bot de WhatsPlay. 🤖")

            # Abrir el chat lo marca como leído en WhatsApp.
            await client.close()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Escanea el código QR.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(auto_reply_bot())
```

## Procesar mensajes

`client.collect_messages()` devuelve una lista de objetos `Message`. Los documentos y archivos adjuntos son instancias de `FileMessage` y las notas de voz son instancias de `VoiceMessage` (ambas subclases de `Message`).

### Atributos comunes de `Message`

*   `message.text`: el contenido de texto. Se lee del propio modelo de mensajes de WhatsApp, por lo que incluye los pies de foto de las imágenes y el texto de una respuesta (no el del mensaje citado). El nombre de archivo de un documento **no** se trata como texto.
*   `message.timestamp`: un `datetime` con la fecha y hora que muestra WhatsApp (se interpretan los formatos de 24 h y de 12 h).
*   `message.sender`: nombre (o número) del remitente, como cadena.
*   `message.is_outgoing`: `True` si enviaste tú el mensaje.
*   `message.msg_id`: el id del mensaje en WhatsApp.
*   `message.filename`: solo en `FileMessage`.
*   `message.duration`: solo en `VoiceMessage`.

### Dirección del mensaje

`is_outgoing` se decide mediante una cadena de señales: la cola de la burbuja, un estado de entrega (solo tus propios mensajes lo tienen), clases e ids de CSS, la herencia del remitente en grupos, la posición de la burbuja y, por último, el nombre del remitente. La señal que decidió se guarda en `message.direction_signal`.

Si tus propios mensajes aparecen con tu nombre de perfil (push name) como remitente, pásalo para que se reconozcan:

```python
messages = await client.collect_messages(own_push_names=["My Name"])
mine = [m for m in messages if m.is_from_self(["My Name"])]
```

### Filtrado

Obtienes una lista de mensajes (normalmente los últimos cargados), así que puedes filtrarlos con Python simple:

```python
# Ejemplo: mensajes que contienen "urgente"
relevant_messages = [
    m for m in messages
    if "urgente" in (m.text or "").lower()
]
```

## Nota sobre `on_message`

Es posible que veas referencias a un evento `on_message` en el código fuente. Este evento está actualmente **reservado para uso futuro** y el bucle principal no lo emite automáticamente. Usa el patrón `on_unread_chat` descrito arriba para construir bots y herramientas de automatización.
