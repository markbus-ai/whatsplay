# Referencia de API

Esta página proporciona una referencia de API generada automáticamente para los componentes clave de la biblioteca WhatsPlay.

## Client
El `Client` es el punto de entrada principal para interactuar con WhatsApp.

| Método | Devuelve | Notas |
| :--- | :--- | :--- |
| `start()` / `stop()` | `None` | `start()` ejecuta el bucle principal hasta que se llama a `stop()`. |
| `wait_until_logged_in(timeout=60)` | `bool` | |
| `refresh(timeout=180)` | `bool` | Recarga WhatsApp Web para liberar memoria del renderizador; emite `on_refresh`. |
| `open(chat_name, timeout=10000, open_via_url=False, is_group=None)` | `bool` | `True` solo cuando se puede verificar que el chat abierto es el solicitado. |
| `close()` | `None` | Cierra el chat actual. |
| `search_conversations(query, close=True)` | `List[Dict]` | |
| `collect_messages(own_push_names=None, dispose=False)` | `List[Message]` | Incluye elementos `FileMessage` y `VoiceMessage`. |
| `send_message(chat_query, message, open_via_url=False, is_group=None)` | `bool` | `True` solo después de que WhatsApp muestra el nuevo mensaje con un estado de entrega. |
| `send_file(chat_name, path, open_via_url=False, is_group=None)` | `bool` | La misma confirmación que `send_message`. |
| `react_to_last_message(emoji)` | `bool` | |
| `download_all_files(carpeta=None, detect_codecs=True)` | `List[Dict]` | Cada dict: `path`, `type` y `codec` (cuando se detecta). |
| `download_file_by_index(index, carpeta=None)` | `Optional[Dict]` | Dict con `path` y `type`. |
| `new_group(group_name, members)` | `bool` | |
| `add_members_to_group(group_name, members)` | `bool` | |
| `del_members_from_group(group_name, members)` | `bool` | |
| `page_lock` (propiedad) | `ReentrantLock` | `async with client.page_lock:` para ejecutar varias operaciones de forma atómica. |
| `running` (propiedad) | `bool` | |

WhatsPlay no define excepciones propias: los fallos se informan como `False`, `[]` o `None`, junto con un evento `on_error` y un registro de log.

::: whatsplay.client.Client

---

## Eventos
Estos eventos son emitidos por el `Client` y se pueden manejar usando el decorador `@client.event`.

| Evento | Condición de disparo | Argumentos |
| :--- | :--- | :--- |
| `on_start` | El cliente se inicializó y la página del navegador está abierta. | Ninguno |
| `on_auth` | Se muestra la pantalla de autenticación (página del código QR). | Ninguno |
| `on_qr` | Se detecta un nuevo código QR por primera vez. | `qr_binary` (bytes) |
| `on_qr_change` | El código QR mostrado se actualizó o cambió. | `qr_binary` (bytes) |
| `on_logged_in` | El cliente inició sesión correctamente en WhatsApp Web. | Ninguno |
| `on_loading` | La pantalla "Cargando chats" está visible. | `is_loading` (bool) |
| `on_unread_chat` | Se detectan chats no leídos en la barra lateral (se verifica periódicamente). | `chats` (List[Dict]) |
| `on_refresh` | `client.refresh()` recargó la página. | Ninguno |
| `on_stop` | El cliente se está deteniendo y liberando recursos. | Ninguno |
| `on_disconnect` | El cliente perdió la conexión con el navegador/WhatsApp. | Ninguno |
| `on_reconnect` | El cliente se reconectó correctamente. | Ninguno |
| `on_state_change` | El estado de la conexión cambió (por ejemplo, `CONNECTING`). | `state` (State enum) |
| `on_tick` | Se emite en cada iteración del bucle principal de eventos. | Ninguno |
| `on_error` | Ocurrió un error. | `message` (str) |
| `on_warning` | Ocurrió un problema no crítico (por ejemplo, un diálogo que no se pudo cerrar). | `message` (str) |
| `on_info` | Mensaje informativo. | `message` (str) |

El contenido de `on_unread_chat` se describe en [Manejo de mensajes](guides/handling-messages.md#estructura-del-payload).

***Nota:** el evento `on_message` está reservado para uso futuro. Por ahora, usa `on_unread_chat` para detectar nueva actividad.*

---

## Objetos de mensaje
`client.collect_messages()` devuelve estos objetos.

### Message
Un mensaje de texto. Atributos principales: `text`, `sender` (str), `timestamp` (datetime), `is_outgoing` (bool), `msg_id`, `direction_signal`, `sender_inherited`. Usa `is_from_self(own_push_names)` para comprobar si lo enviaste tú, `react(emoji)` para reaccionar y `dispose()` para liberar sus handles del navegador.

::: whatsplay.object.message.Message

### FileMessage
Un documento o archivo adjunto. Añade `filename` y `download(page, downloads_dir)`.

::: whatsplay.object.message.FileMessage

### VoiceMessage
Una nota de voz. Añade `duration` y `download(page, downloads_dir)`.

::: whatsplay.object.message.VoiceMessage

---

## Gestores (managers)
Gestores internos que manejan diferentes aspectos de la funcionalidad del cliente.

### Chat Manager
Responsable de buscar y gestionar chats.

::: whatsplay.chat_manager.ChatManager

### State Manager
Responsable de gestionar el estado interno del cliente.

::: whatsplay.state_manager.StateManager

---

## Autenticación
Los manejadores de autenticación se usan para gestionar la sesión de WhatsApp.

### Local Profile Auth
El manejador recomendado para guardar tu sesión localmente y evitar escaneos de QR repetidos.

::: whatsplay.auth.local_profile_auth.LocalProfileAuth

### No Auth
Un manejador que no guarda ningún dato de sesión, por lo que requiere un nuevo inicio de sesión en cada ejecución.

::: whatsplay.auth.no_auth.NoAuth

---

## Filtros
El módulo `filters` proporciona clases e instancias para filtrar eventos.

### Filtros de mensaje predefinidos
Una colección de filtros listos para usar con el evento `on_message`.

::: whatsplay.filters.message_filter

### Clase base de filtro personalizado
Hereda de esta clase para crear tus propios filtros potentes y reutilizables.

::: whatsplay.filters.filters.CustomFilter
