import os
import sys
import asyncio
from pathlib import Path

# Añade src al PYTHONPATH para ejecutar el ejemplo sin instalar el paquete
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from whatsplay.client import Client


async def main():
    # Carpeta de sesión persistente
    user_data = Path(__file__).parent / "whatsapp_session"
    user_data.mkdir(exist_ok=True)

    client = Client(user_data_dir=str(user_data), headless=False, locale="en-US", auth=None)

    # Arranca el cliente en segundo plano
    task = asyncio.create_task(client.start())

    try:
        print("Esperando inicio de sesión...")
        logged = await client.wait_until_logged_in(timeout=120)
        if not logged:
            print("No se pudo iniciar sesión a tiempo.")
            return

        chat_name = os.environ.get("WP_OPEN_CHAT", "")
        if not chat_name:
            print("Define WP_OPEN_CHAT con el nombre del chat a abrir.")
            return

        print(f"Intentando abrir: {chat_name}")
        ok = await client.open(chat_name, timeout=10000, force_open=False)
        print("✅ Abierto" if ok else "❌ No se pudo abrir el chat")

        # Permite ver el resultado unos segundos
        await asyncio.sleep(2)

    except Exception as e:
        print(f"❌ Error en open_example: {e}")
    finally:
        print("Cerrando cliente...")
        try:
            await client.stop()
        except Exception:
            pass
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    asyncio.run(main())


