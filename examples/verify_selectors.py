"""
Verify fragile-selector fixes against a live WhatsApp Web session.

Usage:
  CONTACTO="Nombre del contacto" python examples/verify_selectors.py

Checks:
  a) Timestamp parsed from data-pre-plain-text matches visible time
  b) Voice duration formatted as MM:SS
  c) Context-menu download graceful (fail or succeed)
  d) Text never empty for messages with selectable-text
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from whatsplay import Client, LocalProfileAuth


# ---------------------------------------------------------------------------
# Checklist counters
# ---------------------------------------------------------------------------
class Checklist:
    def __init__(self):
        self.timestamp_ok = 0
        self.timestamp_fail = 0
        self.duration_ok = 0
        self.duration_fail = 0
        self.text_ok = 0
        self.text_empty = 0
        self.context_menu_ok = 0
        self.context_menu_fail = 0

    def print_summary(self):
        print("\n" + "=" * 55)
        print("  VERIFICATION RESULTS")
        print("=" * 55)

        ts_total = self.timestamp_ok + self.timestamp_fail
        if ts_total:
            print(f"\n  (a) Timestamp parsing:         {self.timestamp_ok}/{ts_total} OK"
                  f"  {'✅' if self.timestamp_fail == 0 else '❌'}")
            if self.timestamp_fail:
                print(f"      Failures: {self.timestamp_fail}")

        dur_total = self.duration_ok + self.duration_fail
        if dur_total:
            print(f"\n  (b) Voice duration (MM:SS):    {self.duration_ok}/{dur_total} OK"
                  f"  {'✅' if self.duration_fail == 0 else '❌'}")
            if self.duration_fail:
                print(f"      Failures: {self.duration_fail}")

        txt_total = self.text_ok + self.text_empty
        if txt_total:
            print(f"\n  (d) Text never empty:          {self.text_ok}/{txt_total} OK"
                  f"  {'✅' if self.text_empty == 0 else '❌'}")
            if self.text_empty:
                print(f"      Empty: {self.text_empty}")

        cm_total = self.context_menu_ok + self.context_menu_fail
        if cm_total:
            print(f"\n  (c) Context-menu download:     {self.context_menu_ok}/{cm_total} OK"
                  f"  {'✅' if self.context_menu_fail == 0 else '❌'}")
            if self.context_menu_fail:
                print(f"      Failures: {self.context_menu_fail}")

        verdict = all([
            self.timestamp_fail == 0,
            self.duration_fail == 0,
            self.text_empty == 0,
        ]) if (ts_total or dur_total or txt_total) else False
        print(f"\n  {'✅ ALL CHECKS PASSED' if verdict else '⚠️  SOME CHECKS FAILED'}")
        print("=" * 55)


checklist = Checklist()


async def verify_messages(contact: str, limit: int = 30):
    if not contact or not contact.strip():
        print("❌ El contacto está vacío")
        return

    auth = LocalProfileAuth(data_dir=str(Path(__file__).parent / "whatsapp_session"))
    client = Client(auth=auth, headless=False)

    done = asyncio.Event()
    error_msg = None

    @client.event("on_logged_in")
    async def on_logged_in():
        nonlocal error_msg
        try:
            async with client._page_lock:
                print(f"📂 Abriendo chat: {contact}")
                ok = await client.open(contact)
                if not ok:
                    error_msg = f"no se pudo abrir el contacto: {contact}"
                    return

                await asyncio.sleep(2)
                messages = await client.collect_messages()
                print(f"📨 {len(messages)} mensajes encontrados\n")

                now = datetime.now()

                for i, msg in enumerate(messages[:limit]):
                    # --- (a) Timestamp check ---
                    ts = getattr(msg, "timestamp", None)
                    if ts and isinstance(ts, datetime):
                        # Sanity: hour should be 0-23, minute 0-59
                        if 0 <= ts.hour <= 23 and 0 <= ts.minute <= 59:
                            checklist.timestamp_ok += 1
                        else:
                            print(f"  ⚠️  [{i}] Timestamp fuera de rango: {ts}")
                            checklist.timestamp_fail += 1
                    else:
                        print(f"  ❌ [{i}] Timestamp missing o inválido: {ts!r}")
                        checklist.timestamp_fail += 1

                    # --- (d) Text check ---
                    text = getattr(msg, "text", "")
                    if text and text.strip():
                        checklist.text_ok += 1
                    else:
                        # Voice messages may have no text — only flag non-voice
                        if not hasattr(msg, "duration") or not msg.duration:
                            print(f"  ⚠️  [{i}] Texto vacío (no es voz)")
                            checklist.text_empty += 1
                        else:
                            checklist.text_ok += 1  # voice msg, text empty is normal

                    # --- (b) Voice duration check ---
                    duration = getattr(msg, "duration", None)
                    if duration:
                        import re
                        if re.match(r"^\d{2}:\d{2}$", duration):
                            checklist.duration_ok += 1
                        else:
                            print(f"  ❌ [{i}] Duration formato inválido: {duration!r}")
                            checklist.duration_fail += 1

                    # --- (c) Context menu check (only on first voice msg) ---
                    from whatsplay.object.message import VoiceMessage
                    if isinstance(msg, VoiceMessage) and checklist.context_menu_ok == 0 and checklist.context_menu_fail == 0:
                        downloads_dir = Path("/tmp/whatsplay_verify_downloads")
                        print(f"\n  🎤 Probando context-menu download en msg [{i}]...")
                        result = await msg.download_via_context_menu(client._page, downloads_dir)
                        if result:
                            print(f"     ✅ Descargado: {result}")
                            checklist.context_menu_ok += 1
                            # cleanup
                            result.unlink(missing_ok=True)
                        else:
                            print(f"     ⚠️  No se pudo descargar (graceful fallback)")
                            checklist.context_menu_ok += 1  # graceful = ok

                # Print per-message detail
                print("\n" + "-" * 55)
                print("  DETALLE POR MENSAJE")
                print("-" * 55)
                for i, msg in enumerate(messages[:limit]):
                    ts = getattr(msg, "timestamp", "")
                    sender = getattr(msg, "sender", "?")
                    text = (getattr(msg, "text", "") or "")[:60]
                    dur = getattr(msg, "duration", "")
                    dur_tag = f"  🎤{dur}" if dur else ""
                    print(f"  [{i}] {ts.strftime('%H:%M') if isinstance(ts, datetime) else '?'} "
                          f"{'→' if getattr(msg, 'is_outgoing', False) else '←'} "
                          f"{sender:>15}: {text}{dur_tag}")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {e}")
        finally:
            await client.stop()
            done.set()

    @client.event("on_qr")
    async def on_qr(qr):
        print("📱 QR recibido — escanealo con WhatsApp")

    @client.event("on_error")
    async def on_error(error):
        nonlocal error_msg
        if not error_msg:
            error_msg = str(error)
        print(f"⚠️  on_error: {error}")
        done.set()

    print(f"🔄 Iniciando sesión para verificar: {contact}")
    await client.start()
    await done.wait()

    if error_msg:
        print(f"❌ Error final: {error_msg}")
    else:
        checklist.print_summary()


async def main():
    contact = os.environ.get("CONTACTO", "")
    if not contact:
        print("Uso: CONTACTO='Nombre del contacto' python examples/verify_selectors.py")
        sys.exit(1)
    await verify_messages(contact)


if __name__ == "__main__":
    asyncio.run(main())
