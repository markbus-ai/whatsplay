# Bienvenido a WhatsPlay

[![PyPI version](https://img.shields.io/pypi/v/whatsplay)](https://pypi.org/project/whatsplay/)
[![Downloads](https://img.shields.io/pypi/dm/whatsplay)](https://pypi.org/project/whatsplay/)
[![Python](https://img.shields.io/pypi/pyversions/whatsplay)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**WhatsPlay** es una biblioteca moderna de Python para automatizar WhatsApp Web usando Playwright. Proporciona una interfaz estable y basada en eventos para interactuar con chats, enviar mensajes, gestionar grupos y manejar archivos multimedia, sin depender de la API de WhatsApp Business.

Ya sea que quieras construir un bot, automatizar reportes, recopilar mensajes o integrar WhatsApp en tu flujo de trabajo, WhatsPlay te da las herramientas para hacerlo de forma confiable.

## Características principales

- **Selectores estables:** usa selectores basados en atributos (`data-pre-plain-text`, `aria-label`, `data-testid`), no nombres de clases CSS frágiles que se rompen con cada actualización de WhatsApp Web.
- **Envío seguro:** un mensaje solo se escribe en el chat que pediste, y `send_message()` devuelve `True` solo después de que WhatsApp muestra el nuevo mensaje con un estado de entrega.
- **Coincidencia exacta de chats:** los grupos y los contactos se pueden distinguir con `is_group`, los números de teléfono deben coincidir por completo y los títulos ambiguos se rechazan en lugar de adivinarse.
- **Texto de mensaje preciso:** el texto, los pies de foto y las respuestas se leen del propio modelo de mensajes de WhatsApp, con el DOM como alternativa.
- **Multilenguaje:** funciona de inmediato con WhatsApp Web en español y en inglés.
- **API asíncrona moderna:** construida con `asyncio`; cada operación sobre la página se serializa mediante un único lock reentrante, de modo que los manejadores concurrentes nunca se intercalan.
- **Sesiones persistentes:** escanea el código QR una vez; las ejecuciones siguientes reutilizan la sesión guardada.
- **Soporte de archivos y multimedia:** envía archivos y descarga documentos, imágenes y mensajes de voz (con detección de códec).
- **Basada en eventos:** maneja eventos como `on_logged_in`, `on_unread_chat`, `on_error` y más.
- **Gestión de grupos:** crea grupos y añade o elimina miembros de forma programática.
- **Bots de larga duración:** `refresh()` y `collect_messages(dispose=True)` mantienen bajo control la memoria del renderizador.
- **Logging estándar:** todo se registra mediante el módulo `logging` de Python bajo el espacio de nombres `whatsplay`.
- **Modo headless:** funciona en servidores y en CI sin interfaz gráfica.

## Un ejemplo rápido

Envía un mensaje con solo unas pocas líneas:

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    auth = LocalProfileAuth("./whatsapp_session")
    client = Client(auth=auth, headless=False)

    @client.event("on_logged_in")
    async def on_logged_in():
        await client.send_message("ContactName", "¡Hola desde WhatsPlay! 🚀")
        await client.stop()

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
```

> **Primera ejecución:** se abre un navegador; escanea el código QR con tu teléfono.  
> **Ejecuciones siguientes:** la sesión persiste automáticamente, no se necesita QR.

## Próximos pasos

- **[Primeros pasos](getting-started.md):** instalación y tu primer script.
- **[Configuración](configuration.md):** opciones del cliente, autenticación y logging.
- **[Manejo de mensajes](guides/handling-messages.md):** bots de respuesta automática y filtrado de mensajes.
- **[Envío de multimedia](guides/sending-media.md):** envía archivos y descarga multimedia recibida.
- **[Gestión de grupos](guides/group-management.md):** crea y gestiona grupos de WhatsApp.
- **[Funciones avanzadas](guides/advanced-features.md):** búsqueda, números directos, concurrencia y bots de larga duración.
- **[Referencia de API](api-reference.md):** documentación completa de la API.
