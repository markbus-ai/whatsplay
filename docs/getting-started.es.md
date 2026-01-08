# Empezando con WhatsPlay

Esta guía te llevará a través de la instalación de WhatsPlay y la escritura de tu primer script para enviar un mensaje de WhatsApp.

## 1. Instalación

WhatsPlay requiere Python 3.8 o superior. Puedes instalarlo directamente desde PyPI. También recomendamos instalar las dependencias del navegador de Playwright.

Primero, instala la biblioteca:

```bash
pip install whatsplay
```

Luego, instala los binarios del navegador necesarios para Playwright (esto descargará un navegador como Chromium):

```bash
playwright install
```

## 2. Tu Primer Script: Enviando un Mensaje

Vamos a crear un script simple que inicie sesión en WhatsApp y envíe un mensaje.

Crea un nuevo archivo Python, por ejemplo `enviar_hola.py`, y añade el siguiente código.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    """
    Función principal para inicializar el cliente, enviar un mensaje y detenerse.
    """
    
    # --- Paso 1: Configurar Autenticación ---
    # Esto le dice a WhatsPlay que guarde los datos de sesión en una carpeta llamada "whatsapp_session".
    # De esta manera, solo necesitas escanear el código QR una vez.
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    
    # --- Paso 2: Inicializar el Cliente ---
    # Ejecutamos en headless=False la primera vez para facilitar el escaneo del código QR.
    # Puedes cambiarlo a headless=True después para ejecución en segundo plano.
    client = Client(auth=auth, headless=False)

    # --- Paso 3: Definir Manejadores de Eventos ---
    # `on_start` se dispara una vez que el cliente ha iniciado sesión y está listo.
    @client.event("on_start")
    async def on_start():
        print("¡El cliente está listo! Preparando para enviar un mensaje...")
        
        # Define tu destinatario y mensaje
        # IMPORTANTE: Reemplaza con un número de teléfono real o nombre de contacto.
        # Para números de teléfono, usa el formato con código de país pero sin '+' ni '00'.
        recipient = "1234567890" 
        message = "¡Este es mi primer mensaje desde WhatsPlay! 🎉"
        
        # Enviar el mensaje
        success = await client.send_message(recipient, message)
        
        if success:
            print(f"¡Mensaje enviado exitosamente a {recipient}!")
        else:
            print(f"¡Ups! Falló el envío del mensaje a {recipient}.")
            
        # Detener el cliente después de terminar el trabajo
        print("Trabajo completo. Apagando...")
        await client.stop()

    # `on_qr` se dispara si se necesita un escaneo QR.
    @client.event("on_qr")
    async def on_qr(qr):
        print("Inicio de sesión requerido. Se debería abrir una ventana del navegador para escanear el código QR.")

    # `on_auth` se dispara si se requiere autenticación
    @client.event("on_auth")
    async def on_auth():
        print("Se requiere autenticación.")

    # `on_error` captura errores potenciales durante la ejecución
    @client.event("on_error")
    async def on_error(error):
        print(f"Ocurrió un error: {error}")
        await client.stop()

    # --- Paso 4: Iniciar el Cliente ---
    # Esta llamada inicia el navegador y comienza el proceso de inicio de sesión.
    await client.start()
    print("El script ha terminado de ejecutarse.")

# --- Ejecutar la función principal ---
if __name__ == "__main__":
    asyncio.run(main())
```

### Cómo Ejecutarlo

1.  **Guarda el código:** Guarda el script como `enviar_hola.py`.
2.  **Modifica el destinatario:** Cambia `"1234567890"` a un número de teléfono real o un nombre de contacto guardado en tu WhatsApp.
3.  **Ejecuta desde tu terminal:**
    ```bash
    python enviar_hola.py
    ```
4.  **Inicio de sesión por primera vez:** Se abrirá una ventana del navegador. Escanea el código QR de WhatsApp Web con tu teléfono.
5.  **Ejecuciones subsiguientes:** El script reutilizará la sesión y debería iniciar sesión automáticamente. El mensaje se enviará y el script saldrá.