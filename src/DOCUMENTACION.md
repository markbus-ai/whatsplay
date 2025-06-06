# Documentación del Proyecto WhatsPlay

## Descripción General
Este proyecto implementa un cliente automatizado para WhatsApp Web utilizando Playwright y herramientas de automatización en Python. Permite interactuar con WhatsApp Web para enviar mensajes, descargar archivos, manejar eventos, mostrar códigos QR, entre otras funcionalidades.

---

## Estructura de Carpetas y Archivos Principales

- **base_client.py**: Implementa la clase base para el cliente de WhatsApp Web, gestionando el ciclo de vida del navegador y la autenticación.
- **client.py**: Define la clase principal `Client` que hereda de `BaseWhatsAppClient` y expone los métodos de alto nivel para interactuar con WhatsApp Web (enviar mensajes, descargar archivos, buscar chats, etc).
- **event.py**: Contiene la infraestructura para el manejo de eventos (listeners y triggers).
- **utils.py**: Utilidades auxiliares, por ejemplo, para mostrar el código QR.
- **wa_elements.py**: Métodos para interactuar con los elementos de la interfaz de WhatsApp Web.

---

## Descripción de Clases y Métodos

### 1. base_client.py

#### Clase `BaseWhatsAppClient`
Cliente base para WhatsApp Web. Gestiona el ciclo de vida del navegador y eventos principales.

- **__init__(user_data_dir=None, headless=False, auth=None)**: Inicializa el cliente, configurando directorio de usuario, modo sin cabeza y autenticación.
- **_get_browser_args()**: Devuelve los argumentos de configuración para lanzar el navegador.
- **_initialize_browser()**: Inicializa el navegador y el contexto de usuario.
- **_cleanup()**: Libera los recursos del navegador y guarda el estado si corresponde.
- **start()**: Inicia el cliente y abre WhatsApp Web.
- **stop()**: Detiene el cliente y limpia recursos.
- **reconnect()**: Intenta reconectar el cliente tras una desconexión.

### 2. client.py

#### Clase `Client`
Cliente principal de WhatsApp Web. Hereda de `BaseWhatsAppClient` y expone métodos de alto nivel.

- **__init__(user_data_dir=None, headless=False, locale='en-US', auth=None)**: Inicializa el cliente con opciones de idioma, autenticación, etc.
- **running**: Propiedad que indica si el cliente está activo.
- **start()**: Inicia el cliente y el ciclo principal de interacción.
- **stop()**: Detiene el cliente y cierra ventanas.
- **_main_loop()**: Implementa el ciclo principal de interacción con WhatsApp Web.
- **_get_state()**: Obtiene el estado actual de la sesión de WhatsApp.
- **open(chat_name)**: Abre un chat específico por nombre.
- **search_conversations(query, close=True)**: Busca conversaciones por término.
- **collect_messages()**: Recorre todos los mensajes visibles y los devuelve como objetos `Message` o `FileMessage`.
- **download_all_files(carpeta=None)**: Descarga todos los archivos adjuntos en los mensajes visibles.
- **download_file_by_index(index, carpeta=None)**: Descarga un archivo adjunto específico por índice.
- **send_message(chat_query, message)**: Envía un mensaje de texto a un chat.

### 3. event.py

- **EVENT_LIST**: Lista de eventos soportados (`on_start`, `on_auth`, `on_qr`, etc).

#### Clase `Event`
Permite registrar y disparar listeners para eventos personalizados.
- **register_listener(func)**: Registra un listener.
- **add_listener(func)**: Añade un listener.
- **remove_listener(func)**: Elimina un listener.
- **trigger(*args)**: Dispara el evento y ejecuta todos los listeners.

#### Clase `EventHandler`
Gestiona múltiples eventos y listeners.
- **add_event(event_type)**: Agrega un nuevo evento.
- **event(event_type)**: Devuelve un decorador para registrar listeners.
- **trigger_event(event_type, *args)**: Dispara un evento específico.

### 4. utils.py

- **show_qr_window(qr_image_bytes)**: Muestra el código QR para autenticación.

### 5. wa_elements.py

#### Clase `WhatsAppElements`
Utilidades para interactuar con los elementos de la interfaz de WhatsApp Web.
- **__init__(page)**: Inicializa la clase con la página de Playwright.
- **get_state()**: Determina el estado actual de WhatsApp Web según los elementos visibles.
- **wait_for_selector(selector, timeout=5000, state='visible')**: Espera a que un selector esté disponible.
- **click_search_button()**: Intenta activar la búsqueda en la interfaz.
- **verify_search_active()**: Verifica si la búsqueda está activa.
- **get_qr_code()**: Obtiene la imagen del código QR si está disponible.
- **search_chats(query, close=True)**: Busca chats usando un término y retorna los resultados.

---

## Notas de Uso y Extensión
- El proyecto está pensado para automatización y bots sobre WhatsApp Web.
- Los métodos asíncronos (`async`) requieren ser llamados desde un loop de eventos o usando `await`.
- La arquitectura basada en eventos permite extender funcionalidades fácilmente agregando nuevos listeners.

---

## Ejemplo de Uso
```python
from whatsplay.client import Client

client = Client(user_data_dir='ruta/perfil', headless=True)
await client.start()
await client.send_message('Nombre del chat', '¡Hola desde el bot!')
await client.stop()
```

---

## Créditos y Licencia
Desarrollado por el equipo de WhatsPlay. Consulta el archivo LICENSE para detalles de licencia.
