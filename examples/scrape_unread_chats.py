import asyncio
from playwright.async_api import async_playwright

USER_DATA_DIR = './pw-session'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = await browser.new_page()
        await page.goto('https://web.whatsapp.com/')
        print("Esperando que cargue la lista de chats...")
        try:
            await page.wait_for_selector('div[role="grid"] > div[role="row"]', timeout=90000)
        except Exception as e:
            print("No se pudo encontrar la lista de chats. ¿La sesión está activa y los chats cargados?")
            await browser.close()
            return

        chats = await page.query_selector_all('div[role="grid"] > div[role="row"]')
        print(f"Se encontraron {len(chats)} chats en la vista.")
        encontrados = 0
        for chat in chats:
            # Buscar celda de mensajes no leídos (soporta español e inglés)
            unread_cell = await chat.query_selector(
                'div[role="gridcell"]:has-text("unread message"),'
                'div[role="gridcell"]:has-text("unread messages"),'
                'div[role="gridcell"]:has-text("mensaje no leíd"),'
                'div[role="gridcell"]:has-text("mensajes no leídos")'
            )
            if unread_cell:
                count_el = await unread_cell.query_selector('span, div')
                count = await count_el.inner_text() if count_el else "?"
                title_el = await chat.query_selector('span[title]')
                title = await title_el.get_attribute("title") if title_el else ""
                print(f"Chat: {title}, Mensajes no leídos: {count}")
                encontrados += 1
        if encontrados == 0:
            print("No se encontraron chats con mensajes no leídos.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
