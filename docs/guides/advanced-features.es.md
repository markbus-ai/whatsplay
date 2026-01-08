# Guía: Característica Avanzadas

Más allá de enviar y recibir mensajes, WhatsPlay ofrece varias características avanzadas para ayudarte a gestionar tus chats e interactuar de forma más natural.

## Buscando Conversaciones

Si tienes una larga lista de chats, puedes usar la función de búsqueda para encontrar contactos o grupos específicos.

```python
# Buscar un contacto o grupo
# Devuelve una lista de resultados coincidentes
results = await client.search_conversations("Proyecto Alpha")

for result in results:
    print(f"Encontrado: {result['name']}")
    # Luego puedes abrirlo usando el nombre exacto
    await client.open(result['name'])
```

## Mensajes Directos (No Contactos)

Puedes enviar mensajes a números de teléfono que no están en tu lista de contactos o que no son visibles actualmente en tu historial de chat usando el parámetro `open_via_url`.

```python
# El número de teléfono debe incluir el código de país, sin '+' ni '00'
numero_telefono = "1234567890" 

# Establecer open_via_url=True fuerza a WhatsApp Web a cargar el chat vía URL
success = await client.send_message(numero_telefono, "¡Hola extraño!", open_via_url=True)

if success:
    print("¡Mensaje enviado a número nuevo!")
```

## Reaccionando a Mensajes

Puedes reaccionar al último mensaje recibido en un chat usando emojis. Esto es genial para confirmar la recepción sin enviar un mensaje de texto completo.

```python
await client.open("Mi Amigo")

# Reaccionar con un pulgar arriba
success = await client.react_to_last_message("👍")

if success:
    print("¡Reacción enviada exitosamente!")
```

## Descargando Todos los Archivos

Si necesitas archivar multimedia o documentos de un chat, `download_all_files` te permite obtener todos los adjuntos visibles en la vista actual.

```python
await client.open("Grupo Familiar")

# Descargar todos los archivos visibles a una carpeta específica
saved_paths = await client.download_all_files(carpeta="./descargas/fotos_familia")

print(f"Descargados {len(saved_paths)} archivos.")
```

## Extrayendo Historial de Chat (Scraping)

Puedes combinar `open` y `collect_messages` para extraer el historial de chat. Ten en cuenta que WhatsPlay interactúa actualmente con el DOM visible.

```python
await client.open("Chat de Trabajo")

# Obtener todos los mensajes cargados actualmente
messages = await client.collect_messages()

for msg in messages:
    print(f"[{msg.timestamp}] {msg.sender.name}: {msg.text}")
```