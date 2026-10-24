# Primeros pasos con WhatsPlay

Esta guía te acompaña en la instalación de WhatsPlay y en la escritura de tu primer script para enviar un mensaje de WhatsApp.

## 1. Instalación

WhatsPlay requiere Python 3.8 o superior. Instálalo desde PyPI:

```bash
pip install whatsplay
```

Luego descarga el navegador Chromium que usa Playwright:

```bash
python -m playwright install chromium
```

> **Nota:** si hay un Chromium del sistema (`/usr/bin/chromium`) o Google Chrome (`/usr/bin/google-chrome`) instalado, WhatsPlay lo usa en lugar del navegador incluido con Playwright.

## 2. Tu primer script: enviar un mensaje

Vamos a crear un script simple que inicie sesión en WhatsApp y envíe un mensaje.

Crea un nuevo archivo de Python, por ejemplo `send_hello.py`, y añade el siguiente código.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    # --- Paso 1: Configurar la autenticación ---
    # Los datos de sesión se guardan en la carpeta "whatsapp_session",
    # así que solo necesitas escanear el código QR una vez.
    auth = LocalProfileAuth(data_dir="./whatsapp_session")

    # --- Paso 2: Inicializar el cliente ---
    # Usa headless=False la primera vez para poder escanear el código QR.
    # Cambia a headless=True después para ejecutarlo en segundo plano.
    client = Client(auth=auth, headless=False)

    # --- Paso 3: Definir los manejadores de eventos ---
    # `on_logged_in` se dispara una vez que el cliente inició sesión y está listo.
    @client.event("on_logged_in")
    async def on_logged_in():
        # Reemplaza con un nombre de contacto, nombre de grupo o número de teléfono real.
        # Los números de teléfono necesitan el número internacional completo (con código de país).
        recipient = "5491123456789"
        message = "¡Este es mi primer mensaje desde WhatsPlay! 🎉"

        # True solo cuando WhatsApp muestra el nuevo mensaje con un estado de entrega.
        if await client.send_message(recipient, message, open_via_url=True):
            print(f"¡Mensaje enviado a {recipient}!")
        else:
            print(f"No se pudo confirmar el mensaje a {recipient}. Revisa los logs.")

        await client.stop()

    # `on_qr` se dispara cuando se necesita escanear un QR.
    @client.event("on_qr")
    async def on_qr(qr):
        print("Escanea el código QR que aparece en la ventana del navegador.")

    # `on_error` informa fallos (WhatsPlay devuelve False/None en lugar de lanzar excepciones).
    @client.event("on_error")
    async def on_error(error):
        print(f"Ocurrió un error: {error}")

    # --- Paso 4: Iniciar el cliente ---
    # Inicia el navegador y ejecuta el bucle principal hasta que se llame a client.stop().
    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### Cómo ejecutarlo

1.  **Guarda el código** como `send_hello.py`.
2.  **Cambia el destinatario** por un número de teléfono real (con `open_via_url=True`) o por un nombre de contacto o de grupo exactamente como aparece en WhatsApp (sin `open_via_url`).
3.  **Ejecútalo:**
    ```bash
    python send_hello.py
    ```
4.  **Primer inicio de sesión:** se abre una ventana del navegador. Escanea el código QR de WhatsApp Web con tu teléfono.
5.  **Ejecuciones siguientes:** se reutiliza la sesión guardada y el cliente inicia sesión automáticamente.

## 3. Qué esperar de `send_message()`

`send_message()` es deliberadamente estricto. Devuelve `False` (y registra el motivo) en lugar de adivinar cuando:

- el chat no se puede abrir, o más de un chat tiene el mismo título;
- el cuadro de redacción no pertenece al chat solicitado;
- el cuadro de redacción no contiene exactamente el texto que pasaste;
- no aparece ningún mensaje nuevo con estado de entrega después de presionar Enter.

Cuando necesites dirigirte a un grupo o a un contacto con el mismo nombre, pasa `is_group=True` o `is_group=False`. Consulta [Funciones avanzadas](guides/advanced-features.md) para más detalles.

## 4. Ver qué está pasando

WhatsPlay registra mediante el módulo estándar `logging` de Python. Si tu aplicación no configura el logging, WhatsPlay imprime los mensajes `INFO` en stdout. Para ver más detalle:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("whatsplay").setLevel(logging.DEBUG)
```

Consulta [Configuración › Registros](configuration.md#registros) para más información.
