import os
import sys
import asyncio

# Add the src directory to Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import asyncio
from pathlib import Path

from whatsplay.client import (
    Client,
)  # Asegúrate de que la ruta sea correcta a tu client.py
from whatsplay.object.message import (
    Message,
    FileMessage,
)  # Asegúrate de que la ruta sea correcta a tu models.py


async def list_available_chats(client):
    """Función de depuración: lista los títulos de los chats visibles en la interfaz."""
    try:
        # Esperar breve para asegurarse de que la interfaz cargue
        await asyncio.sleep(2)
        # Obtener todos los elementos con título de chat
        elements = await client._page.query_selector_all("span[title]")
        print("Chats disponibles:")
        for elem in elements:
            title = await elem.get_attribute("title")
            print(f" - {title}")
    except Exception as e:
        print(f"⚠️ No se pudieron obtener los chats: {e}")


async def main():
    # 1) Creamos una carpeta donde se guardará la sesión de WhatsApp Web
    user_data = Path(__file__).parent / "whatsapp_session"
    user_data.mkdir(exist_ok=True)

    # 2) Instanciamos el cliente; en modo no-headless para poder escanear QR la primera vez
    client = Client(
        user_data_dir=str(user_data), headless=False, locale="en-US", auth=None
    )

    # 3) Creamos la tarea que ejecuta el bucle principal del cliente
    task = asyncio.create_task(client.start())

    try:
        # 4) Esperamos hasta que esté LOGGED_IN o falle el timeout
        print("Esperando a que iniciés sesión en WhatsApp Web...")
        logged = await client.wait_until_logged_in(timeout=120)
        if not logged:
            print("No se pudo iniciar sesión en el tiempo esperado. Saliendo.")
            return

        print("✅ Sesión iniciada correctamente.")

        # Depuración: listar los chats para confirmar el nombre exacto
        await list_available_chats(client)

        # 5) Abrimos un chat concreto
        chat_name = (
            "Mom"  # Asegurate de usar el nombre exacto que aparece en la lista anterior
        )
        print(f"Abrimos el chat: {chat_name}")
        ok = await client.open(chat_name)
        if ok is False:
            print(
                f"No se encontró el chat «{chat_name}». Verifica el nombre y vuelve a intentar."
            )
            return
        # Damos un par de segundos para que cargue el historial
        await asyncio.sleep(2)

        # 6) Recopilamos TODOS los mensajes visibles (tanto texto como con archivos)
        mensajes = await client.collect_messages()
        print(f"\nSe encontraron {len(mensajes)} mensajes visibles en pantalla:\n")
        for idx, m in enumerate(mensajes):
            if isinstance(m, FileMessage):
                print(f"[{idx}] 📎 Archivo")
                print(f"      Remitente: {m.sender}")
                print(f"      Hora:      {m.timestamp.strftime('%H:%M')}")
                print(f"      Nombre:    {m.filename}\n")
            else:
                print(f"[{idx}] ✉️ Mensaje de texto")
                print(f"      Remitente: {m.sender}")
                print(f"      Hora:      {m.timestamp.strftime('%H:%M')}")
                print(f"      Texto:     {m.text}\n")

        # 7) Descargamos todos los archivos que haya
        destino = Path.home() / "Downloads"
        print(f"Descargando todos los archivos en: {destino}")
        rutas = await client.download_all_files(str(destino))
        if rutas:
            print("\nArchivos descargados:")
            for r in rutas:
                print("   •", r)
        else:
            print(
                "\nNo se descargó ningún archivo (quizá no había ninguno o hubo error)."
            )

    except Exception as e:
        print(f"❌ Excepción durante ejecución: {e}")

    finally:
        # 8) Detenemos el cliente y cerramos el navegador
        print("\nDeteniendo el cliente y cerrando navegador...")
        try:
            await client.stop()
        except Exception as close_err:
            print(f"⚠️ Error al cerrar el cliente: {close_err}")

        # Cancelar la tarea si no terminó
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    asyncio.run(main())
