# Documentación del Proyecto WhatsPlay

## Descripción General
Este proyecto implementa un cliente automatizado para WhatsApp Web utilizando Playwright y herramientas de automatización en Python. Permite interactuar con WhatsApp Web para enviar mensajes, descargar archivos, manejar eventos, mostrar códigos QR, entre otras funcionalidades.

**Última actualización:** 2025-12-14

---

## Estructura de Carpetas y Archivos Principales

### Módulos Core
- **base_client.py**: Implementa la clase base para el cliente de WhatsApp Web, gestionando el ciclo de vida del navegador y la autenticación.
- **client.py**: Define la clase principal `Client` que hereda de `BaseWhatsAppClient` y expone los métodos de alto nivel para interactuar con WhatsApp Web (enviar mensajes, descargar archivos, buscar chats, etc).
- **chat_manager.py**: ✅ Gestiona operaciones relacionadas con chats individuales y detección de mensajes no leídos mediante heurísticas robustas.
- **state_manager.py**: Maneja los estados del cliente y transiciones entre diferentes estados de WhatsApp Web.
- **event.py**: Contiene la infraestructura para el manejo de eventos (listeners y triggers).
- **utils.py**: Utilidades auxiliares, por ejemplo, para mostrar el código QR.
- **wa_elements.py**: ✅ Métodos para interactuar con los elementos de la interfaz de WhatsApp Web, con soporte para múltiples estrategias de búsqueda y locators actualizados.

### Submódulos

#### auth/
- **auth.py**: Clase base abstracta para estrategias de autenticación
- **local_profile_auth.py**: Implementación de autenticación usando perfiles locales del navegador
- **no_auth.py**: Estrategia sin autenticación (requiere escaneo QR cada vez)

#### constants/
- **locator.py**: ✅ Definiciones de selectores XPath y CSS para elementos de WhatsApp Web (actualizados para versiones 2024-2025)
- **states.py**: Enumeración de estados posibles del cliente (AUTH, QR_AUTH, LOADING, LOGGED_IN)

#### events/
- **event_handler.py**: Manejador central de eventos del sistema
- **event_types.py**: Tipos de eventos soportados (on_start, on_auth, on_qr, on_unread_chat, etc.)

#### filters/
- **message_filter.py**: Sistema de filtrado de mensajes por contenido, remitente, tipo, etc.
- **filters.py**: Filtros adicionales para procesamiento de mensajes

#### object/
- **message.py**: Clases `Message` y `FileMessage` que representan mensajes de texto y archivos multimedia

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

### 1.1 chat_manager.py

#### Clase `ChatManager`
✅ Gestiona operaciones de chat y detección robusta de mensajes no leídos.

**Características principales:**
- Detección de chats no leídos mediante múltiples heurísticas (aria-labels, badges, font-weight)
- Soporte para scroll infinito en lista virtualizada de chats
- Manejo de grupos y chats individuales
- Apertura de chats por nombre o número de teléfono

**Métodos clave:**
- **_check_unread_chats(debug=True)**: Escanea la lista de chats y retorna aquellos con mensajes no leídos
- **row_is_unread(row_loc)**: Determina si un chat tiene mensajes no leídos usando múltiples estrategias
- **get_scroller_handle()**: Obtiene el contenedor scrolleable de la lista virtualizada
- **open(chat_name)**: Abre un chat específico por nombre o número
- **close()**: Cierra el chat actualmente abierto

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
✅ Utilidades para interactuar con los elementos de la interfaz de WhatsApp Web con soporte multi-versión.

**Características destacadas:**
- Múltiples estrategias de búsqueda con fallback automático
- Selectores actualizados para WhatsApp Web 2024-2025
- Detección automática de cambios en el DOM
- Soporte para búsqueda por CSS y XPath
- Manejo robusto de elementos dinámicos

**Métodos principales:**
- **__init__(page)**: Inicializa la clase con la página de Playwright.
- **get_state()**: Determina el estado actual de WhatsApp Web según los elementos visibles (LOGGED_IN, LOADING, QR_AUTH, AUTH).
- **wait_for_selector(selector, timeout=5000, state='visible')**: Espera a que un selector esté disponible con timeout configurable.
- **click_search_button()**: ✅ Intenta activar la búsqueda usando múltiples estrategias (selectores CSS nuevos de 2025, selectores legacy, selectores por aria-label).
- **verify_search_active()**: Verifica si la búsqueda está activa mediante detección de input textbox.
- **get_qr_code()**: Obtiene la imagen del código QR si está disponible para autenticación.
- **search_chats(query, close=True)**: Busca chats usando un término y retorna los resultados con soporte para resultados virtualizados.

---

## Notas de Uso y Extensión
- El proyecto está pensado para automatización y bots sobre WhatsApp Web.
- Los métodos asíncronos (`async`) requieren ser llamados desde un loop de eventos o usando `await`.
- La arquitectura basada en eventos permite extender funcionalidades fácilmente agregando nuevos listeners.

---

## Cambios Recientes (Últimos Commits)

### ✅ Actualización de Locators (2025-12-14)
- **Commit:** `5a6dd76` - Fix: Update chat filter button locators from `div` to `span` elements
- **Cambios:** Actualización de selectores de botones de filtro de chat para compatibilidad con WhatsApp Web 2024-2025
- **Archivos afectados:** `constants/locator.py`

### ✅ Refactorización de Búsqueda (2025-12-14)
- **Commit:** `270d6dd` - Refactor WhatsApp locators and enhance search functionality
- **Cambios:**
  - Mejora en la funcionalidad de búsqueda con múltiples estrategias
  - Selectores actualizados para el nuevo DOM de WhatsApp
  - Soporte para selectores CSS modernos (`span[data-icon="search-refreshed-thin"]`)
- **Archivos afectados:** `wa_elements.py`, `constants/locator.py`

### ✅ Mejora en Detección de Chats No Leídos
- **Commits:** `7451dc7`, `f61421d`, `5545d6e`
- **Cambios:**
  - Heurísticas robustas para detectar chats no leídos (aria-labels, badges, font-weight)
  - Soporte para lista virtualizada con scroll infinito
  - Mejor manejo de grupos vs chats individuales
- **Archivos afectados:** `chat_manager.py`, `client.py`

### 📦 Nuevos Ejemplos
- **open_example.py**: Ejemplo de apertura de chats específicos
- **search_example.py**: Ejemplo de búsqueda de conversaciones
- **wsp.py**: Ejemplo completo de uso del cliente

---

## Mejores Prácticas y Lecciones Aprendidas

### 1. Manejo de Selectores Dinámicos
WhatsApp Web actualiza frecuentemente su interfaz. Para mantener compatibilidad:
- Usar múltiples estrategias de selección con fallback
- Priorizar selectores semánticos (aria-labels) sobre clases CSS
- Mantener selectores legacy como fallback
- Implementar logging detallado para debugging

### 2. Detección de Mensajes No Leídos
La detección robusta requiere múltiples heurísticas:
1. Buscar aria-labels con "unread" o "mensaje(s) no leído"
2. Verificar presencia de badges de notificación
3. Comprobar font-weight del título (≥600 indica no leído)
4. Considerar el contexto del chat (grupo vs individual)

### 3. Listas Virtualizadas
WhatsApp usa listas virtualizadas para optimizar rendimiento:
- No todos los chats están en el DOM simultáneamente
- Implementar scroll programático para cargar más elementos
- Usar `role='grid'` y `role='row'` como selectores estables
- Detectar cuándo se alcanza el final de la lista

### 4. Búsqueda en WhatsApp Web
Para activar la búsqueda de forma confiable:
- Intentar selectores CSS modernos primero (`span[data-icon="search-refreshed-thin"]`)
- Usar selectores por aria-label como fallback
- Verificar que el input de búsqueda está activo antes de escribir
- Manejar timeouts con gracia

---

## Ejemplo de Uso Actualizado

```python
import asyncio
from pathlib import Path
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main() -> None:
    # Configurar autenticación persistente
    data_dir = Path.home() / "Documents" / "whatsapp_session"
    data_dir.mkdir(parents=True, exist_ok=True)

    auth = LocalProfileAuth(data_dir)
    client = Client(auth=auth, headless=False)

    @client.event("on_start")
    async def on_start():
        print("✅ Cliente iniciado")

    @client.event("on_auth")
    async def on_auth():
        print("📸 Mostrando QR en pantalla")

    @client.event("on_unread_chat")
    async def on_unread_chat(chat_name, messages):
        print(f"💬 Chat no leído: {chat_name} ({len(messages)} mensajes)")
        # Responder automáticamente
        await client.send_message(chat_name, "¡Mensaje recibido!")

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📚 Ejemplos Prácticos

El proyecto incluye varios ejemplos prácticos en la carpeta `/examples` que demuestran diferentes casos de uso de WhatsPlay.

### 1. simple_example.py - Ejemplo Básico con Eventos

**Propósito:** Demostrar el uso básico del cliente con sistema de eventos y detección de mensajes no leídos.

**Características:**
- ✅ Configuración de autenticación persistente con `LocalProfileAuth`
- ✅ Manejo completo de eventos: `on_start`, `on_auth`, `on_qr`, `on_loading`, `on_unread_chat`, `on_error`
- ✅ Detección automática de chats no leídos
- ✅ Envío de mensajes automático al recibir chats no leídos
- ✅ Acceso a metadata del chat (nombre, grupo, tipo de último mensaje)

**Uso:**
```bash
cd examples
python simple_example.py
```

**Código clave:**
```python
@client.event("on_unread_chat")
async def unread_chat(chats):
    chat = chats[0]
    print("Chat no leído:", chat.get("name"))
    print("Es grupo:", chat.get("group"))
    print("Tipo último mensaje:", chat.get("last_message_type"))
    await client.send_message(chat.get("name"), "Hello!")
```

**Casos de uso:**
- Bots de respuesta automática
- Monitoreo de mensajes entrantes
- Auto-respuesta para atención al cliente

---

### 2. open_example.py - Apertura de Chats Específicos

**Propósito:** Demostrar cómo abrir un chat específico programáticamente.

**Características:**
- ✅ Espera activa hasta login exitoso con `wait_until_logged_in()`
- ✅ Apertura de chat por nombre usando `client.open()`
- ✅ Configuración mediante variable de entorno `WP_OPEN_CHAT`
- ✅ Control de timeout y opciones de forzado
- ✅ Manejo robusto de errores y cleanup

**Uso:**
```bash
# Linux/Mac
export WP_OPEN_CHAT="Nombre del Contacto"
python open_example.py

# Windows
set WP_OPEN_CHAT=Nombre del Contacto
python open_example.py
```

**Código clave:**
```python
logged = await client.wait_until_logged_in(timeout=120)
if logged:
    ok = await client.open(chat_name, timeout=10000, force_open=False)
    print("✅ Abierto" if ok else "❌ No se pudo abrir")
```

**Casos de uso:**
- Automatización de navegación en WhatsApp Web
- Preparación de chats antes de enviar mensajes
- Testing de apertura de conversaciones

---

### 3. search_example.py - Búsqueda de Conversaciones

**Propósito:** Demostrar la funcionalidad de búsqueda de conversaciones con resultados detallados.

**Características:**
- ✅ Búsqueda de conversaciones con `client.search_conversations()`
- ✅ Configuración de búsqueda mediante variables de entorno
- ✅ Visualización detallada de resultados (nombre, grupo, último mensaje, no leídos, actividad)
- ✅ Opción de abrir primer resultado automáticamente
- ✅ Control de cierre de búsqueda con parámetro `close`

**Uso:**
```bash
# Búsqueda básica
export WP_SEARCH_QUERY="Juan"
python search_example.py

# Búsqueda y apertura automática del primer resultado
export WP_SEARCH_QUERY="Soporte"
export WP_OPEN_FIRST=1
python search_example.py
```

**Código clave:**
```python
results = await client.search_conversations(query, close=False)

for i, r in enumerate(results, start=1):
    print(f"[{i}] nombre: {r.get('name')}")
    print(f"    grupo: {r.get('group')}")
    print(f"    última actividad: {r.get('last_activity')}")
    print(f"    último mensaje: {r.get('last_message')}")
    print(f"    tipo último: {r.get('last_message_type')} | no leídos: {r.get('unread_count')}")
```

**Resultados incluyen:**
- `name`: Nombre del chat/contacto
- `group`: Nombre del grupo (si aplica)
- `last_message`: Texto del último mensaje
- `last_message_type`: Tipo de mensaje (texto, imagen, audio, etc.)
- `unread_count`: Cantidad de mensajes no leídos
- `last_activity`: Timestamp de última actividad

**Casos de uso:**
- Búsqueda de contactos o grupos
- Filtrado de conversaciones por término
- Navegación programática entre chats

---

### 4. wsp.py - Herramienta CLI para Envío Rápido

**Propósito:** Script tipo CLI para envío rápido de mensajes desde línea de comandos.

**Características:**
- ✅ Interfaz de línea de comandos con argumentos
- ✅ Soporte para perfil persistente personalizado
- ✅ Modo headless y modo con GUI (`--show`)
- ✅ Autenticación automática con `LocalProfileAuth`
- ✅ Envío y cierre automático
- ✅ Gestión de perfil en `~/.whatsplay/UserData` por defecto

**Uso:**
```bash
# Envío básico (headless por defecto)
python wsp.py "Juan Pérez" "Hola, ¿cómo estás?"

# Mostrar navegador durante el envío
python wsp.py --show "Soporte" "Necesito ayuda con mi pedido"

# Usar perfil personalizado
python wsp.py --profile ~/mi_perfil "Equipo" "Reunión a las 3pm"

# Mensajes multi-palabra
python wsp.py "Grupo Trabajo" Este mensaje tiene varias palabras
```

**Sintaxis:**
```
wsp [--show] [--profile RUTA] <contacto|grupo> <mensaje>
```

**Opciones:**
- `--show`: Muestra el navegador (útil para primera autenticación)
- `--profile RUTA`: Especifica directorio de perfil personalizado
- Por defecto usa modo headless y perfil en `~/.whatsplay/UserData`

**Código clave:**
```python
@client.event("on_logged_in")
async def on_logged_in():
    await client.send_message(to, text)
    print(f"✓ enviado a: {to}")
    await asyncio.sleep(2)
    await client.stop()
```

**Casos de uso:**
- Envío rápido desde terminal
- Integración con scripts de shell
- Notificaciones automáticas desde cronjobs
- Testing rápido de funcionalidades

**Ejemplo de integración con cron:**
```bash
# Enviar recordatorio diario a las 9am
0 9 * * * python /path/to/wsp.py "Equipo Ventas" "Buenos días! Reporte diario pendiente"
```

---

## Comparativa de Ejemplos

| Ejemplo | Complejidad | Caso de Uso Principal | Modo | Interacción |
|---------|-------------|----------------------|------|-------------|
| `simple_example.py` | ⭐ Básico | Aprender eventos y auto-respuesta | GUI | Reactivo |
| `open_example.py` | ⭐⭐ Intermedio | Abrir chats específicos | GUI | Programático |
| `search_example.py` | ⭐⭐ Intermedio | Búsqueda y navegación | GUI | Programático |
| `wsp.py` | ⭐⭐⭐ Avanzado | CLI para envío rápido | Headless/GUI | CLI |

---

## Variables de Entorno Soportadas

Los ejemplos usan variables de entorno para configuración:

- **`WP_OPEN_CHAT`**: Nombre del chat a abrir (open_example.py)
- **`WP_SEARCH_QUERY`**: Término de búsqueda (search_example.py)
- **`WP_OPEN_FIRST`**: "1" para abrir primer resultado (search_example.py)

---

## Arquitectura del Sistema

```
whatsplay/
├── Client (client.py)
│   ├── BaseWhatsAppClient (base_client.py)
│   ├── ChatManager (chat_manager.py)
│   ├── StateManager (state_manager.py)
│   ├── WhatsAppElements (wa_elements.py)
│   └── EventHandler (events/event_handler.py)
├── auth/
│   ├── Auth (interfaz base)
│   ├── LocalProfileAuth (persistente)
│   └── NoAuth (temporal)
├── filters/
│   └── MessageFilter (filtrado de mensajes)
└── object/
    ├── Message
    └── FileMessage
```

---

## Estado del Proyecto

### Funcionalidades Completadas ✅
- ✅ Autenticación mediante QR con persistencia de sesión
- ✅ Envío de mensajes de texto
- ✅ Recepción de mensajes
- ✅ Detección robusta de chats no leídos
- ✅ Sistema de eventos asíncrono
- ✅ Búsqueda de conversaciones
- ✅ Filtrado de mensajes
- ✅ Descarga de archivos multimedia
- ✅ Soporte para grupos y chats individuales
- ✅ Modo headless (sin GUI)
- ✅ Selectores actualizados para WhatsApp Web 2024-2025

### En Desarrollo 🚧
- Mejoras en la detección de tipos de mensajes (audio, video, documentos)
- Optimización de rendimiento en listas largas de chats
- Soporte para mensajes con reacciones
- API para envío de archivos multimedia

### Roadmap Futuro 🔮
- Soporte para llamadas de voz/video
- Integración con webhooks
- CLI interactivo
- Dashboard web de monitoreo
- Soporte para múltiples cuentas simultáneas

---

## Créditos y Licencia
Desarrollado por Markbusking y colaboradores. Licencia Apache 2.0.
Para contribuir, consulta el repositorio en GitHub: https://github.com/markbus-ai/whatsplay
