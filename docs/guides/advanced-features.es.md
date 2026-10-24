# Guía: Funciones avanzadas

Además de enviar y recibir mensajes, WhatsPlay ofrece varias funciones avanzadas para ayudarte a gestionar tus chats, ejecutar operaciones de forma segura con concurrencia y mantener en buen estado los bots de larga duración.

## Abrir el chat correcto

`client.open()` devuelve `True` solo cuando se puede verificar que el chat que queda abierto es el que pediste. Nunca recurre al "primer resultado de búsqueda".

- **Títulos exactos:** el nombre solicitado debe coincidir exactamente con el título de un chat (se normalizan mayúsculas y acentos).
- **Los títulos ambiguos se rechazan:** si varios chats o resultados de búsqueda comparten el mismo título, `open()` devuelve `False` y registra un error.
- **Los números de teléfono coinciden por completo:** `"2235988856"` nunca coincide con `"+54 9 2235 98-8856"`; usa el número internacional completo.
- **Grupos frente a contactos:** pasa `is_group=True` o `is_group=False` para exigir uno u otro. WhatsPlay comprueba la etiqueta del cuadro de redacción ("…to group X" / "…para el grupo X").

```python
await client.open("Family", is_group=True)        # solo el grupo "Family"
await client.send_message("Family", "Hi!", is_group=False)  # solo el contacto "Family"
```

`send_message()` y `send_file()` aceptan los mismos parámetros `open_via_url` e `is_group`.

## Buscar conversaciones

Si tienes una lista de chats larga, puedes usar la función de búsqueda para encontrar contactos o grupos específicos.

```python
# Devuelve una lista de resultados coincidentes
results = await client.search_conversations("Project Alpha")

for result in results:
    print(f"Encontrado: {result['name']}")
    # Luego puedes abrirlo usando el nombre exacto
    await client.open(result["name"])
```

La búsqueda se interrumpe si el foco sale del cuadro de búsqueda mientras se escribe, por lo que nunca puede escribir en un chat ni coincidir con mensajes del chat abierto.

## Mensajes directos (no contactos)

Puedes enviar mensajes a números de teléfono que no están en tu lista de contactos, o que no son visibles en tu historial de chats, con `open_via_url=True`. Esto carga el chat mediante `web.whatsapp.com/send?phone=...`.

```python
# Número internacional completo, con código de país
phone_number = "5491123456789"

if await client.send_message(phone_number, "¡Hola, desconocido!", open_via_url=True):
    print("¡Mensaje enviado al número nuevo!")
```

Si el número pertenece a un contacto guardado, WhatsApp muestra el nombre del contacto en lugar del número; WhatsPlay lo acepta y el envío se realiza igualmente.

## Reaccionar a mensajes

Puedes reaccionar con emojis al último mensaje visible de un chat.

```python
await client.open("My Friend")

if await client.react_to_last_message("👍"):
    print("¡Reacción enviada correctamente!")
```

## Ejecutar operaciones de forma atómica

Cada operación pública sobre la página (`open`, `send_message`, `collect_messages`, ...) se ejecuta bajo un único lock reentrante de asyncio, de modo que los manejadores de eventos concurrentes nunca se intercalan dentro del navegador. La verificación de estado en segundo plano se omite mientras el lock está tomado.

Para ejecutar varias operaciones como una sola unidad (por ejemplo, abrir un chat y leerlo sin que otro manejador cambie de chat entre medio), toma tú mismo `client.page_lock`:

```python
async with client.page_lock:
    if await client.open("Work Chat"):
        messages = await client.collect_messages()
        await client.close()
```

El lock es reentrante, así que los métodos del cliente llamados dentro del bloque no se bloquean entre sí.

## Bots persistentes y memoria

El renderizador de WhatsApp Web crece tras horas de automatización. Dos herramientas lo mantienen bajo control:

- **`collect_messages(dispose=True)`** libera los handles del navegador de cada mensaje justo después de leerlo. Úsalo cuando solo necesites los datos; los mensajes liberados ya no pueden usar `react()` ni `download()`.
- **`client.refresh(timeout=180)`** recarga WhatsApp Web para liberar la memoria acumulada del renderizador, emite `on_refresh` y espera hasta que la sesión vuelva a estar iniciada. La sesión se conserva gracias al perfil del navegador, así que no se necesita un nuevo QR. Devuelve `False` si la recarga falla.

```python
import asyncio

async def periodic_refresh(client, every_seconds=6 * 60 * 60):
    while client.running:
        await asyncio.sleep(every_seconds)
        await client.refresh()
```

## Diálogos que bloquean

WhatsApp Web a veces muestra diálogos que bloquean la interfaz. WhatsPlay los cierra mediante su botón de cerrar (X), bajo el lock de la página. Un diálogo que no se puede cerrar produce un único evento `on_warning`.

## Extraer el historial de chats

Puedes combinar `open` y `collect_messages` para extraer el historial de un chat. WhatsPlay lee los mensajes cargados actualmente en el chat, así que para los mensajes muy antiguos primero hay que desplazarse hacia arriba.

```python
await client.open("Work Chat")

messages = await client.collect_messages()

for msg in messages:
    print(f"[{msg.timestamp}] {msg.sender}: {msg.text}")
```
