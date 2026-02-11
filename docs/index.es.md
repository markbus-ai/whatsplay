# Bienvenido a WhatsPlay

WhatsPlay es una biblioteca de Python para automatizar WhatsApp Web usando Playwright. Proporciona una interfaz simple y basada en eventos para interactuar con chats, enviar mensajes, gestionar grupos y mucho más.

Ya sea que quieras construir un bot, automatizar tus reportes diarios o extraer datos de chats, WhatsPlay te da las herramientas para hacerlo eficientemente.

## Características Principales

*   **Basado en Eventos:** Maneja fácilmente eventos como mensajes entrantes, escaneos QR o cuando el cliente está listo.
*   **API Asíncrona Moderna:** Construido con `asyncio` para un alto rendimiento.
*   **Gestión de Sesión:** Guarda tu sesión localmente para que no tengas que escanear el código QR cada vez.
*   **Gestión de Grupos:** Crea grupos, añade/elimina miembros y más.
*   **Soporte de Archivos y Multimedia:** Envía imágenes, documentos y otros archivos con facilidad.

## Un Ejemplo Rápido

Aquí tienes un script simple para enviar un mensaje a un contacto:

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main():
    auth = LocalProfileAuth("./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_logged_in")
    async def on_logged_in():
        print("¡Cliente iniciado! Enviando mensaje...")
        
        # Usa un número de teléfono (ej., "1234567890") o un nombre de contacto guardado
        # Para números de teléfono, incluye el código de país sin '+' ni '00'
        recipient = "NUMERO_DE_TELEFONO_O_NOMBRE_DE_CONTACTO"
        message = "¡Hola desde WhatsPlay! 🚀"
        
        success = await client.send_message(recipient, message)
        
        if success:
            print(f"Mensaje enviado exitosamente a {recipient}.")
        else:
            print(f"Falló el envío del mensaje a {recipient}.")
            
        await client.stop()

    # Este evento se dispara si necesitas escanear el código QR
    @client.event("on_qr")
    async def on_qr(qr):
        print("Se requiere escaneo de código QR. Por favor escanea el QR en el navegador.")

    await client.start()
    print("Script finalizado.")

if __name__ == "__main__":
    asyncio.run(main())
```