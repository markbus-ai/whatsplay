"""
Example: collect messages from a contact using the event-based pattern.

Muestra el patrón correcto con:
  - on_logged_in event + done_event
  - _page_lock para evitar race conditions
  - Manejo de errores sin masking
  - Debug logging por timestamp

Uso:
  CONTACTO="Nombre del contacto" python examples/collect_messages_event.py
"""

import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from whatsplay import Client, LocalProfileAuth


async def collect_messages(contact: str, limit: int = 20):
    if not contact or not contact.strip():
        print("❌ El contacto está vacío")
        return

    auth = LocalProfileAuth(data_dir=str(Path(__file__).parent / "whatsapp_session"))
    client = Client(auth=auth, headless=False)

    result = {"contacto": contact, "mensajes": []}
    done = asyncio.Event()
    error_msg = None

    @client.event("on_logged_in")
    async def on_logged_in():
        nonlocal error_msg
        t0 = asyncio.get_event_loop().time()

        try:
            # ── usar _page_lock para evitar race conditions ──
            async with client._page_lock:
                elapsed = asyncio.get_event_loop().time() - t0
                print(f"[collect:{elapsed:.2f}s] _page_lock adquirido, abriendo chat...")

                ok = await client.open(contact)
                elapsed = asyncio.get_event_loop().time() - t0
                print(f"[collect:{elapsed:.2f}s] open() returned: {ok}")

                if not ok:
                    error_msg = f"no se pudo abrir el contacto: {contact}"
                    return

                messages = await client.collect_messages()
                elapsed = asyncio.get_event_loop().time() - t0
                print(f"[collect:{elapsed:.2f}s] collect_messages() returned {len(messages)} msgs")
                for i, m in enumerate(messages):
                    print(f"  [{i}] sender={getattr(m, 'sender', '?')!r} text={getattr(m, 'text', '')[:60]!r} type={type(m).__name__}")

                for msg in messages[:limit]:
                    result["mensajes"].append({
                        "de": getattr(msg, "sender", "?"),
                        "texto": getattr(msg, "text", ""),
                        "propio": getattr(msg, "is_outgoing", False),
                        "timestamp": str(getattr(msg, "timestamp", "")),
                    })

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error en on_logged_in: {e}")
        finally:
            await client.stop()
            done.set()

    @client.event("on_qr")
    async def on_qr(qr):
        print("📱 QR recibido — escanealo con WhatsApp")

    @client.event("on_error")
    async def on_error(error):
        nonlocal error_msg
        # Solo pisar error_msg si no hay uno previo más importante
        if not error_msg:
            error_msg = str(error)
        print(f"⚠️ on_error: {error}")
        done.set()

    print(f"🔄 Iniciando cliente para contacto: {contact}")
    await client.start()
    await done.wait()

    if error_msg:
        print(f"❌ Error final: {error_msg}")
    else:
        print(f"✅ {len(result['mensajes'])} mensajes colectados")
        for m in result["mensajes"]:
            print(f"  [{m['timestamp']}] {'←' if not m['propio'] else '→'} {m['texto'][:80]}")


async def main():
    contact = os.environ.get("CONTACTO", "")
    if not contact:
        print("Uso: CONTACTO='Nombre del contacto' python examples/collect_messages_event.py")
        sys.exit(1)
    await collect_messages(contact)


if __name__ == "__main__":
    asyncio.run(main())
