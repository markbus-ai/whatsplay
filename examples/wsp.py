import os
import sys
import asyncio
from pathlib import Path

# Añadir src al PYTHONPATH para ejecutar el ejemplo sin instalar el paquete
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from whatsplay.client import Client
from whatsplay.auth import LocalProfileAuth

USO = "uso: wsp [--show] [--profile RUTA] <contacto|grupo> <mensaje>"

def parse_args(argv):
    headless = False
    
    profile = Path.home() / ".whatsplay" / "UserData"  # por defecto mantiene sesión
    args = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--show":
            headless = False
            i += 1
        elif a == "--profile" and i + 1 < len(argv):
            profile = Path(argv[i + 1]).expanduser().resolve()
            i += 2
        else:
            args.append(a)
            i += 1

    if len(args) < 2:
        print(USO); sys.exit(1)

    to = args[0]
    text = " ".join(args[1:]).strip()
    if not text:
        print("✗ mensaje vacío"); sys.exit(1)

    return headless, profile, to, text

async def main():
    headless, profile, to, text = parse_args(sys.argv)
    profile.mkdir(parents=True, exist_ok=True)

    auth = LocalProfileAuth(str(profile))  # usa el directorio del perfil
    client = Client(auth=auth, headless=headless)

    print(f"[WSP] perfil: {profile} | headless: {headless}")

    # registrá eventos ANTES de iniciar
    @client.event("on_logged_in")
    async def on_logged_in():
        print("✓ login exitoso")
        try:
            await client.send_message(to, text)
            print(f"✓ enviado a: {to}")
            await asyncio.sleep(2)  # espera a que se envíe
        finally:
            await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        # info útil si es la primera vez en modo --show
        print("Escaneá el QR para iniciar sesión…")

    await client.start()   # en la primera vez, requerirá QR si usás --show
    print("[WSP] cliente iniciado")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
