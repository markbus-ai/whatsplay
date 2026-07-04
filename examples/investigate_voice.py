"""
Investigate voice message DOM — simplified, uses collect_messages to find voice msgs,
then dumps the container HTML for selector analysis.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from whatsplay import Client, LocalProfileAuth
from whatsplay.object.message import VoiceMessage


async def investigate():
    session_dir = Path(__file__).parent.parent / "examples" / "whatsapp_session"
    auth = LocalProfileAuth(data_dir=str(session_dir))
    client = Client(auth=auth, headless=False)

    @client.event("on_logged_in")
    async def on_logged_in():
        try:
            page = client._page
            print("🔄 Abriendo chat: Bot Mark")
            await client.open("Bot Mark")
            await asyncio.sleep(3)

            messages = await client.collect_messages()
            print(f"\n📨 {len(messages)} mensajes encontrados\n")

            for i, msg in enumerate(messages):
                print(f"\n--- Mensaje {i} (type={type(msg).__name__}) ---")
                print(f"  sender={msg.sender}  text={msg.text[:50]!r}  is_outgoing={msg.is_outgoing}")

                if not isinstance(msg, VoiceMessage):
                    continue

                print(f"  duration={msg.duration!r}")
                container = msg.container

                # 1. All attrs of container
                html = await container.evaluate("el => el.outerHTML")
                print(f"\n  🌐 FULL CONTAINER HTML ({len(html)} chars):")
                print(html)

                # 2. Save to file for reference
                out = Path("/tmp/voice_msg_container.html")
                out.write_text(html)
                print(f"\n  💾 Saved to {out}")

                # 3. Check the specific selectors used in from_element
                print(f"\n  🔍 SELECTOR CHECKS:")

                # Play button
                btn = await container.query_selector('button[aria-label="Reproducir mensaje de voz"]')
                print(f"    button[aria-label='Reproducir mensaje de voz']: {'FOUND' if btn else 'NOT FOUND'}")

                # Voice container span
                span = await container.query_selector('span[aria-label="Mensaje de voz"]')
                print(f"    span[aria-label='Mensaje de voz']: {'FOUND' if span else 'NOT FOUND'}")

                # Audio element
                audio = await container.query_selector('audio')
                print(f"    audio element: {'FOUND' if audio else 'NOT FOUND'}")
                if audio:
                    dur = await audio.get_attribute("duration")
                    src = await audio.get_attribute("src")
                    print(f"      duration attr: {dur}")
                    print(f"      src: {src}")

                # Voice icon
                icon = await container.evaluate("""
                    (el) => {
                        const svgs = el.querySelectorAll('svg');
                        for (const svg of svgs) {
                            const title = svg.querySelector('title');
                            if (title && title.textContent.includes('ic-keyboard-voice')) {
                                const p = svg.parentElement;
                                return { tag: p.tagName, classes: p.className, role: p.getAttribute('role') };
                            }
                        }
                        return null;
                    }
                """)
                print(f"    ic-keyboard-voice icon: {icon}")

                # 4. Context menu target candidates
                print(f"\n  🎯 CONTEXT MENU TARGET CANDIDATES:")
                candidates = await container.evaluate("""
                    (el) => {
                        // All div with role=button inside
                        const buttons = el.querySelectorAll('div[role="button"]');
                        const results = [];
                        for (const b of buttons) {
                            const ariaLabel = b.getAttribute('aria-label');
                            // Skip known irrelevant ones
                            if (ariaLabel === 'Reaccionar' || ariaLabel === 'Más reacciones') continue;
                            if (ariaLabel && ariaLabel.includes('voz')) {
                                results.push({ tag: b.tagName, classes: b.className, ariaLabel: b.getAttribute('aria-label'), role: b.getAttribute('role') });
                            }
                        }
                        return results.length > 0
                            ? results
                            : 'Ningún div[role=button] con aria-label de voz';
                    }
                """)
                print(f"    div[role=button] con 'voz': {candidates}")

                # All elements with class containing _ak4
                ak4 = await container.evaluate("""
                    (el) => {
                        const matches = el.querySelectorAll('[class*="_ak4"]');
                        const result = [];
                        for (const m of matches) {
                            result.push({
                                tag: m.tagName,
                                classes: m.className,
                                role: m.getAttribute('role'),
                                ariaLabel: m.getAttribute('aria-label')
                            });
                        }
                        return result;
                    }
                """)
                print(f"    [class*='_ak4']: {ak4}")

                # Capture parent chain: find the deepest button/div nearby audio
                parent_map = await container.evaluate("""
                    (el) => {
                        const audio = el.querySelector('audio');
                        if (!audio) return 'No audio element';
                        let curr = audio.parentElement;
                        const chain = [];
                        let depth = 0;
                        while (curr && curr !== el && depth < 10) {
                            chain.push({
                                tag: curr.tagName,
                                id: curr.id || '',
                                classes: curr.className ? curr.className.substring(0, 120) : '',
                                role: curr.getAttribute('role') || '',
                                dataTestid: curr.getAttribute('data-testid') || ''
                            });
                            curr = curr.parentElement;
                            depth++;
                        }
                        return chain;
                    }
                """)
                print(f"    Parent chain from audio: {parent_map}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                await client.stop()
            except Exception:
                pass

    @client.event("on_qr")
    async def on_qr(qr):
        print("📱 QR recibido — escanealo")

    @client.event("on_error")
    async def on_error(error):
        print(f"⚠️  on_error: {error}")

    print("🔄 Inspeccionando voz en 'Bot Mark'")
    await client.start()


if __name__ == "__main__":
    asyncio.run(investigate())
