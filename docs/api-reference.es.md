# Referencia de API

Esta página proporciona una referencia de API generada automáticamente para los componentes clave de la biblioteca WhatsPlay.

## Client
El `Client` es el punto de entrada principal para interactuar con WhatsApp.

::: whatsplay.client.Client

---

## Eventos
Estos eventos son emitidos por el `Client` y pueden ser manejados usando el decorador `@client.event`.

| Evento | Condición de Disparo | Argumentos |
| :--- | :--- | :--- |
| `on_start` | El cliente se ha inicializado correctamente y la página del navegador está abierta. | Ninguno |
| `on_auth` | Se muestra la pantalla de autenticación (página del código QR). | Ninguno |
| `on_qr` | Se detecta un nuevo código QR por primera vez. | `qr_binary` (bytes) |
| `on_qr_change` | El código QR mostrado se ha actualizado/cambiado. | `qr_binary` (bytes) |
| `on_logged_in` | El cliente ha iniciado sesión exitosamente en WhatsApp Web. | Ninguno |
| `on_loading` | La pantalla "Cargando chats" es visible. | `is_loading` (bool) |
| `on_unread_chat` | Se detectan chats no leídos en la barra lateral. Verificación periódica. | `chats` (List[Dict]) |
| `on_stop` | El cliente se está deteniendo y limpiando recursos. | Ninguno |
| `on_disconnect` | El cliente ha perdido la conexión con el navegador/WhatsApp. | Ninguno |
| `on_reconnect` | El cliente se ha reconectado exitosamente. | Ninguno |
| `on_state_change` | El estado interno del cliente (ej. AUTH, LOGGED_IN) ha cambiado. | `state` (State enum) |
| `on_tick` | Emitido en cada iteración del bucle principal de eventos. | Ninguno |
| `on_error` | Ha ocurrido un error. | `message` (str) |
| `on_warning` | Ha ocurrido un problema no crítico. | `message` (str) |
| `on_info` | Mensaje informativo. | `message` (str) |

***Nota:** El evento `on_message` está reservado para uso futuro. Actualmente, use `on_unread_chat` para detectar nueva actividad.*

---

## Objetos de Evento
Estos son los objetos que se pasan a sus manejadores de eventos.

### Message
El objeto `Message` representa un mensaje recuperado de un chat (por ejemplo, vía `chat_manager.collect_messages()`).

::: whatsplay.object.message.Message

---

## Gestores (Managers)
Gestores internos que manejan diferentes aspectos de la funcionalidad del cliente.

### Chat Manager
Responsable de buscar y gestionar chats.

::: whatsplay.chat_manager.ChatManager

### State Manager
Responsable de gestionar el estado interno del cliente.

::: whatsplay.state_manager.StateManager

---

## Autenticación
Los manejadores de autenticación se utilizan para gestionar la sesión de WhatsApp.

### Local Profile Auth
El manejador recomendado para guardar su sesión localmente y evitar escaneos QR repetidos.

::: whatsplay.auth.local_profile_auth.LocalProfileAuth

### No Auth
Un manejador que no guarda ningún dato de sesión, requiriendo un nuevo inicio de sesión en cada ejecución.

::: whatsplay.auth.no_auth.NoAuth

---

## Filtros
El módulo `filters` proporciona clases e instancias para filtrar eventos.

### Filtros de Mensaje Predefinidos
Una colección de filtros listos para usar para el evento `on_message`.

::: whatsplay.filters.message_filter

### Clase Base de Filtro Personalizado
Herede de esta clase para crear sus propios filtros potentes y reutilizables.

::: whatsplay.filters.filters.CustomFilter