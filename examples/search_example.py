import os
import sys
import asyncio
from pathlib import Path

# Añadir src al PYTHONPATH para ejecutar el ejemplo sin instalar el paquete
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from whatsplay.client import Client


async def main():
    # Carpeta de sesión persistente para no reescanear el QR cada vez
    user_data = Path(__file__).parent / "whatsapp_session"
    user_data.mkdir(exist_ok=True)

    client = Client(user_data_dir=str(user_data), headless=False, locale="en-US", auth=None)

    # Iniciar el cliente en segundo plano
    task = asyncio.create_task(client.start())

    try:
        print("Esperando a que inicies sesión en WhatsApp Web...")
        logged = await client.wait_until_logged_in(timeout=120)
        if not logged:
            print("No se pudo iniciar sesión a tiempo. Cierra y vuelve a intentar.")
            return

        print("✅ Sesión iniciada. Ejecutando búsqueda...")


        # Ajusta este término para probar resultados distintos
        query = os.environ.get("WP_SEARCH_QUERY", "mi num")
        results = await client.search_conversations(query, close=False)
        input("Presiona Enter para continuar...")

        if not results:
            print(f"Sin resultados para: '{query}'")
            return

        print(f"\nResultados de búsqueda para '{query}':\n")
        for i, r in enumerate(results, start=1):
            name = r.get("name") or "(Sin nombre)"
            group = r.get("group")
            last_msg = r.get("last_message")
            unread = r.get("unread_count")
            last_type = r.get("last_message_type")
            last_activity = r.get("last_activity")
            print(f"[{i}] nombre: {name}")
            if group:
                print(f"    grupo: {group}")
            if last_activity:
                print(f"    última actividad: {last_activity}")
            print(f"    último mensaje: {last_msg}")
            print(f"    tipo último: {last_type} | no leídos: {unread}")

        # (Opcional) Abre el primer resultado
        open_first = os.environ.get("WP_OPEN_FIRST", "0") == "1"
        if open_first:
            first_name = results[0].get("name")
            if first_name:
                print(f"\nAbriendo primer resultado: {first_name}")
                ok = await client.open(first_name)
                print("Abierto" if ok else "No se pudo abrir")

    except Exception as e:
        print(f"❌ Error en el ejemplo de búsqueda: {e}")
    finally:
        print("\nCerrando cliente...")
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


