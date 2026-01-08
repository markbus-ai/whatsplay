# Configuración

Esta guía detalla cómo configurar el `Client` y las estrategias de autenticación en WhatsPlay.

## Configuración del Cliente

La clase `Client` es el punto de entrada principal. Puedes configurarla usando los siguientes parámetros en su constructor.

```python
from whatsplay import Client

client = Client(
    auth=...,           # Estrategia de autenticación
    headless=False,     # Ejecutar con ventana de navegador visible
    locale="en-US",     # Idioma del navegador
    user_data_dir=...   # (Opcional) Ruta directa al perfil del navegador
)
```

### Parámetros

| Parámetro | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `auth` | `AuthBase` | `None` | La estrategia de autenticación a usar. Ver **Autenticación** abajo. |
| `headless` | `bool` | `False` | Si es `True`, ejecuta el navegador en segundo plano (sin interfaz visible). Útil para servidores o bots. Si es `False`, se abrirá una ventana. |
| `locale` | `str` | `"en-US"` | El código de configuración regional del navegador (ej. `"es-ES"`, `"pt-BR"`). Esto afecta cómo WhatsApp Web muestra el texto. |
| `user_data_dir` | `str` | `None` | Una ruta directa a un directorio de datos de usuario de Chrome. **Nota:** Se recomienda usar `LocalProfileAuth` en lugar de establecer esto directamente. |

## Estrategias de Autenticación

WhatsPlay soporta diferentes formas de manejar tu sesión de WhatsApp.

### 1. LocalProfileAuth (Recomendado)

Esta estrategia guarda tu sesión de inicio (cookies, almacenamiento local) en una carpeta en tu disco. Esto significa que solo necesitas escanear el código QR una vez.

```python
from whatsplay.auth import LocalProfileAuth

# Guardar sesión en la carpeta "./mi_sesion"
auth = LocalProfileAuth(data_dir="./mi_sesion")

client = Client(auth=auth)
```

**Parámetros:**

*   `data_dir` (str): El directorio donde se almacenarán los datos de la sesión. Si no existe, se creará.
*   `profile` (str, por defecto `"Default"`): El nombre de la subcarpeta del perfil. Útil si quieres gestionar múltiples cuentas en el mismo `data_dir`.

### 2. NoAuth

Esta estrategia **no** guarda ningún dato de sesión. Cada vez que ejecutes el script, se creará una instancia nueva del navegador y tendrás que escanear el código QR nuevamente.

```python
from whatsplay.auth import NoAuth

auth = NoAuth()
client = Client(auth=auth)
```

## Configuración Avanzada del Navegador

WhatsPlay utiliza **Playwright** (Chromium) internamente.

### Viewport y Zona Horaria
Por defecto, el navegador se lanza con:
*   **Viewport:** 1280x720
*   **Zona Horaria:** UTC
*   **User Agent:** Un user agent estándar de Chrome/Windows para prevenir bloqueos básicos.

Estos están configurados actualmente como constantes en el cliente base para asegurar estabilidad con WhatsApp Web.

### Variables de Entorno
Dado que WhatsPlay depende de Playwright, se aplican las variables de entorno estándar de Playwright:
*   `DEBUG=pw:api`: Habilita el registro detallado (verbose logging) para las llamadas a la API de Playwright.
*   `PLAYWRIGHT_BROWSERS_PATH`: Ruta personalizada para los binarios del navegador.
