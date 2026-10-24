# Configuración

Esta guía detalla cómo configurar el `Client`, las estrategias de autenticación y el logging en WhatsPlay.

## Configuración del cliente

La clase `Client` es el punto de entrada principal. Puedes configurarla usando los siguientes parámetros en su constructor.

```python
from whatsplay import Client

client = Client(
    auth=...,           # Estrategia de autenticación
    headless=False,     # Ejecutar con ventana de navegador visible
)
```

### Parámetros

| Parámetro | Tipo | Por defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `auth` | `AuthBase` | `None` | La estrategia de autenticación a usar. Consulta **Estrategias de autenticación** más abajo. |
| `headless` | `bool` | `False` | Si es `True`, ejecuta el navegador en segundo plano (sin interfaz visible). Útil para servidores o bots. |
| `user_data_dir` | `str` | `None` | Una ruta directa a un directorio de datos de usuario de Chrome. **Nota:** es preferible usar `LocalProfileAuth` en lugar de establecer esto directamente. |
| `locale` | `str` | `"en-US"` | Configuración regional del navegador; también se envía como cabecera `Accept-Language` (por ejemplo, `"es-AR"`). Usa una configuración regional en inglés o en español: el envío solo es compatible con esos idiomas de interfaz (consulta **Idioma de la interfaz**). |

## Estrategias de autenticación

WhatsPlay admite diferentes formas de manejar tu sesión de WhatsApp.

### 1. LocalProfileAuth (recomendada)

Esta estrategia conserva tu sesión en un perfil de navegador en disco, así que solo necesitas escanear el código QR una vez.

```python
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

# Guardar la sesión en la carpeta "./my_session"
auth = LocalProfileAuth(data_dir="./my_session")

client = Client(auth=auth)
```

**Parámetros:**

*   `data_dir` (str): el directorio donde se almacenan los datos de sesión. Se crea si no existe.
*   `profile` (str, por defecto `"Default"`): el nombre de la subcarpeta del perfil. Útil para gestionar varias cuentas en el mismo `data_dir`.

### 2. NoAuth

Esta estrategia **no** guarda ningún dato de sesión. Cada ejecución inicia un navegador nuevo y necesitas escanear el código QR otra vez.

```python
from whatsplay.auth import NoAuth

auth = NoAuth()
client = Client(auth=auth)
```

## Registros

WhatsPlay usa el módulo estándar `logging` de Python. Cada módulo registra bajo el espacio de nombres `whatsplay` (`whatsplay.client`, `whatsplay.chat_manager`, `whatsplay.wa_elements`, `whatsplay.state_manager`, `whatsplay.object.message`, ...), de modo que un solo `setLevel()` sobre `"whatsplay"` lo controla todo.

- **Si tu aplicación configura el logging** (el logger raíz tiene handlers), los registros de WhatsPlay se propagan a él como los de cualquier otra biblioteca: archivos, Sentry, `caplog` de `pytest`, etc.
- **Si no lo hace**, un handler de compatibilidad imprime `LEVEL: message` en stdout con nivel `INFO`, para que nada se pierda en silencio.

```python
import logging

# Silencioso: solo advertencias y errores
logging.getLogger("whatsplay").setLevel(logging.WARNING)

# Detallado: detección de estado y decisiones sobre el DOM
logging.getLogger("whatsplay.wa_elements").setLevel(logging.DEBUG)
```

El sondeo de estado registra en `DEBUG`; cada escaneo de chats no leídos registra una única línea de resumen en `INFO`.

## Configuración avanzada del navegador

WhatsPlay usa **Playwright** (Chromium) internamente.

### Ejecutable del navegador
Si existe `/usr/bin/chromium` o `/usr/bin/google-chrome`, WhatsPlay lo usa. De lo contrario, usa el Chromium instalado con `python -m playwright install chromium`.

### Viewport, configuración regional y zona horaria
El navegador se inicia con:
*   **Viewport:** 1280x720
*   **Configuración regional:** el `locale` pasado a `Client` (por defecto `en-US`)
*   **Zona horaria:** UTC
*   **User Agent:** un user agent estándar de Chrome/Windows para evitar bloqueos básicos.

El viewport, la zona horaria y el user agent son constantes en el cliente base para mantener estable WhatsApp Web.

### Idioma de la interfaz
El envío depende de que la etiqueta accesible del cuadro de redacción nombre el chat de destino. Se admiten interfaces de WhatsApp Web en **español e inglés**; con cualquier otro idioma de interfaz, el envío se rechaza (devuelve `False`) en lugar de arriesgarse a escribir en el chat equivocado.

### Variables de entorno
WhatsPlay no tiene variables de entorno propias. Las variables estándar de Playwright siguen aplicándose:
*   `DEBUG=pw:api`: logging detallado de las llamadas a la API de Playwright.
*   `PLAYWRIGHT_BROWSERS_PATH`: ruta personalizada para los binarios del navegador.
