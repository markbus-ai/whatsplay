import re
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

import asyncio

from playwright.async_api import(
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError,
)

from .constants import locator as loc
from .object.message import Message, FileMessage

class ChatManager:
    def __init__(self, client):
        self.client = client
        self._page = client._page
        self.wa_elements = client.wa_elements

        # Íconos de estado que SOLO aparecen si el último mensaje del chat es tuyo
        self.ICONOS_ESTADO_CHATLIST = (
            "ic-chatlist-clock",     # pendiente
            "ic-chatlist-sent",      # enviado (1 check)
            "ic-chatlist-delivered", # entregado (2 checks grises)
            "ic-chatlist-read",      # leído (2 checks azules)
            "ic-chatlist-error",     # fallo de envío
            "ic-msg-warning",        # otro posible fallo
        )

        self.MAP_ESTADO_CHATLIST = {
            "ic-chatlist-clock": "pendiente",
            "ic-chatlist-sent": "enviado",
            "ic-chatlist-delivered": "entregado",
            "ic-chatlist-read": "leído",
            "ic-chatlist-error": "fallo",
            "ic-msg-warning": "fallo",
        }

    async def _get_chatlist_status(self, chat_row):
        """
        Devuelve (is_last_outgoing: bool, status_icon: str|None, status_text: str|None).
        Si no hay icono, es porque el último mensaje NO es tuyo.
        """
        icon_locator = chat_row.locator('[data-icon^="ic-chatlist-"]')
        # puede haber más de uno (mute/pin/archived), buscamos el primero que esté en nuestra tupla
        count = await icon_locator.count()
        if count == 0:
            return False, None, None

        # recorrer pocos (suelen ser 1-2)
        for i in range(min(count, 5)):
            name = await icon_locator.nth(i).get_attribute("data-icon")
            if name in self.ICONOS_ESTADO_CHATLIST:
                return True, name, self.MAP_ESTADO_CHATLIST.get(name)
        return False, None, None

    async def _tiene_badge_unread(self, chat_row):
        """
        Heurística para 'tiene no leídos'. Evita .all(timeout=...) que no existe.
        """
        # clases ofuscadas típicas + aria-labels
        sel = (
            ".x140p0ai, ._ahlk, .xn58pb5, "
            "[aria-label*='unread' i], "
            "[aria-label*='no leído' i], "
            "[aria-label*='sin leer' i]"
        )
        return (await chat_row.locator(sel).count()) > 0
    # ===== helpers =====
    @staticmethod
    def _looks_like_status(s: str) -> bool:
        s = (s or "").lower()
        return any(x in s for x in ("loading", "status-", "typing", "default-", "ic-", "call", "escribiendo"))

    @staticmethod
    def _strip_noise(s: str) -> str:
        s = s or ""
        s = re.sub(r"\b\d{1,2}:\d{2}\s?(am|pm)?\b", "", s, flags=re.I)  # horas 12/24h
        s = re.sub(r"\b(hoy|ayer|today|yesterday)\b", "", s, flags=re.I)
        s = re.sub(r"\b\d+\b", "", s)  # badges numéricos
        s = " ".join(s.split())
        return s


    async def _extract_name_and_preview(self, row) -> Tuple[str, str]:
        name = ""
        preview = ""

        # 1) nombre: <span title="..."> dentro de la col 2
        span_name = row.locator('div[role="gridcell"][aria-colindex="2"] span[title]').first
        if await span_name.count():
            name = (await span_name.get_attribute("title")) or ""
            if name:
                print("DEBUG: name encontrado:", name)

        # fallback: primer span visible con dir="auto" y title
        if not name:
            span_alt = row.locator('xpath=.//span[@dir="auto" and @title]').first
            if await span_alt.count():
                name = (await span_alt.get_attribute("title")) or ""
                if name:
                    print("DEBUG: name encontrado en fallback:", name)

        # 2) preview: 2º <div> hijo directo dentro de la col 2; buscar span con title o texto
        cell = row.locator('div[role="gridcell"][aria-colindex="2"]')
        line2 = cell.locator(':scope > div').nth(1)  # segundo div (0-based)
        if await line2.count():
            span_with_title = line2.locator('span[title]').first
            if await span_with_title.count():
                t = (await span_with_title.inner_text()) or ""
            else:
                t = (await line2.inner_text()) or ""
            preview = self._strip_noise(t)

        # fallback: último span de esa línea que no sea “status”
        if not preview:
            spans = line2.locator('span')
            n = await spans.count()
            for idx in range(n - 1, -1, -1):
                tx = (await spans.nth(idx).inner_text()) or ""
                if tx and not self._looks_like_status(tx):
                    preview = self._strip_noise(tx)
                    print("DEBUG: preview fallback OK")
                    break

        return (name or "Sin nombre"), (preview or "")
    async def _get_time_text(self, row) -> str:
        # columna 2: el 2º div hijo directo tiene el horario/fecha
        cell = row.locator('div[role="gridcell"][aria-colindex="2"]')
        time_div = cell.locator(':scope > div').nth(1)

        if not await time_div.count():
            return ""

        txt = (await time_div.inner_text()) or ""
        return self._strip_noise(txt.strip())



    # ===== _check_unread_chats =====
    async def _check_unread_chats(self, debug: bool = False):
        unread_chats = []
        page = self._page

        try:
            rows = page.locator("[role='listitem']")
            total = await rows.count()
            if debug:
                print(f"DEBUG: listitems visibles: {total}")

            if total == 0:
                # sidebar virtualizado: scrolleo corto para hidratar
                await page.mouse.wheel(0, 800)
                await asyncio.sleep(0.25)
                await page.mouse.wheel(0, -800)
                await asyncio.sleep(0.25)
                rows = page.locator("[role='listitem']")
                total = await rows.count()
                if debug:
                    print(f"DEBUG: tras scroll listitems: {total}")

            for i in range(total):
                row = rows.nth(i)

                # 1) ¿tiene badge de no leído?
                tiene_unread = await self._tiene_badge_unread(row)
                if not tiene_unread:
                    continue

                # 2) ¿el último mensaje es tuyo? (iconos ic-chatlist-*)
                is_out, icon_name, status_text = await self._get_chatlist_status(row)

                # 3) nombre + preview limpios
                name, preview = await self._extract_name_and_preview(row)

                # 4) hora/fecha (opcional)
                time_txt = await self._get_time_text(row)

                chat_info = {
                    "name": name,
                    "preview": preview,
                    "has_unread": True,
                    "last_outgoing": is_out,            # True si el último es tuyo
                    "last_status_icon": icon_name,      # p.ej. ic-chatlist-delivered
                    "last_status_text": status_text,    # p.ej. "entregado"
                    "last_activity": time_txt,          # p.ej. "1:29 am" -> limpiado
                }
                unread_chats.append(chat_info)

                if debug:
                    print(f"✓ Unread: {name} | out={is_out} | {icon_name} ({status_text}) | prev='{preview}'")

        except Exception as e:
            await self.client.emit("on_warning", f"Error detectando no leídos: {e}")
            if debug:
                print(f"DEBUG: Error general: {e}")

        if debug:
            print("\nDEBUG: ===== RESUMEN =====")
            print(f"Total chats no leídos: {len(unread_chats)}")
            for i, chat in enumerate(unread_chats):
                print(f"  {i+1}. {chat['name']} | out={chat['last_outgoing']} | {chat['last_status_icon']}")

        return unread_chats

    # ===== _parse_search_result =====
    async def _parse_search_result(self, element, result_type: str = "CHATS") -> Optional[Dict[str, Any]]:
        """
        Parsea un ítem de resultados (barra de búsqueda).
        Estructura contemplada:
        - count == 3 -> [grupo/fecha] [titulo] [preview]
        - count == 2 -> [titulo/fecha] [preview]
        Ignora estados “typing/loading/ic-...” y limpia ruidos/horas.
        """
        try:
            components = await element.query_selector_all(
                'xpath=.//div[@role="gridcell" and @aria-colindex="2"]/parent::div/div'
            )
            count = len(components)

            unread_el = await element.query_selector(f"xpath={loc.SEARCH_ITEM_UNREAD_MESSAGES}")
            unread_count = await unread_el.inner_text() if unread_el else "0"

            # defensivo: mic solo si hay al menos 2 componentes
            mic_span = None
            if count >= 2:
                mic_span = await components[1].query_selector('xpath=.//span[@data-icon="mic"]')

            if count == 3:
                span_title_0 = await components[0].query_selector(f"xpath={loc.SPAN_TITLE}")
                group_title = await span_title_0.get_attribute("title") if span_title_0 else ""

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = (await datetime_children[1].inner_text()) if len(datetime_children) > 1 else ""

                span_title_1 = await components[1].query_selector(f"xpath={loc.SPAN_TITLE}")
                title = await span_title_1.get_attribute("title") if span_title_1 else ""

                info_text = (await components[2].inner_text()) or ""
                info_text = self._strip_noise(info_text)
                if self._looks_like_status(info_text):
                    return None

                return {
                    "type": result_type,
                    "group": group_title,
                    "name": title,
                    "last_activity": self._strip_noise(datetime_text),
                    "last_message": info_text,
                    "last_message_type": "audio" if mic_span else "text",
                    "unread_count": unread_count,
                    "element": element,
                }

            elif count == 2:
                span_title_0 = await components[0].query_selector(f"xpath={loc.SPAN_TITLE}")
                title = await span_title_0.get_attribute("title") if span_title_0 else ""

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = (await datetime_children[1].inner_text()) if len(datetime_children) > 1 else ""

                info_children = await components[1].query_selector_all("xpath=./*")
                info_text = (await info_children[0].inner_text()) if len(info_children) > 0 else ""
                info_text = self._strip_noise(info_text)
                if self._looks_like_status(info_text):
                    return None

                return {
                    "type": result_type,
                    "name": title,
                    "last_activity": self._strip_noise(datetime_text),
                    "last_message": info_text,
                    "last_message_type": "audio" if mic_span else "text",
                "unread_count": unread_count,
                    "element": element,
                    "group": None,
                }

            # layout no contemplado
            return None

        except Exception as e:
            print(f"Error parsing result: {e}")
            return None


    async def download_all_files(self, carpeta: Optional[str] = None) -> List[Path]:
        """
        Llama a collect_messages(), filtra FileMessage y descarga cada uno.
        Devuelve lista de Path donde se guardaron.
        """
        if not await self.client.wait_until_logged_in():
            return []

        if carpeta:
            downloads_dir = Path(carpeta)
        else:
            downloads_dir = Path.home() / "Downloads" / "WhatsAppFiles"

        archivos_guardados: List[Path] = []
        mensajes = await self.collect_messages()
        for m in mensajes:
            if isinstance(m, FileMessage):
                ruta = await m.download(self._page, downloads_dir)
                if ruta:
                    archivos_guardados.append(ruta)
        return archivos_guardados

    async def download_file_by_index(
        self, index: int, carpeta: Optional[str] = None
    ) -> Optional[Path]:
        """
        Descarga sólo el FileMessage en la posición `index` de la lista devuelta
        por collect_messages() filtrando por FileMessage.
        """
        if not await self.client.wait_until_logged_in():
            return None

        if carpeta:
            downloads_dir = Path(carpeta)
        else:
            downloads_dir = Path.home() / "Downloads" / "WhatsAppFiles"

        mensajes = await self.collect_messages()
        archivos = [m for m in mensajes if isinstance(m, FileMessage)]
        if index < 0 or index >= len(archivos):
            return None

        return await archivos[index].download(self._page, downloads_dir)

    async def send_message(
        self, chat_query: str, message: str, force_open=True
    ) -> bool:
        """Envía un mensaje a un chat"""
        if not await self.client.wait_until_logged_in():
            return False

        try:
            if force_open:
                await self.open(chat_query)
            await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)
            input_box = await self._page.wait_for_selector(
                loc.CHAT_INPUT_BOX, timeout=10000
            )
            if not input_box:
                await self.client.emit(
                    "on_error",
                    "No se encontró el cuadro de texto para enviar el mensaje",
                )
                return False

            await input_box.click()
            await input_box.fill(message)
            await self._page.keyboard.press("Enter")
            return True

        except Exception as e:
            await self.client.emit("on_error", f"Error al enviar el mensaje: {e}")
            return False
        finally:
            await self.close()

    async def send_file(self, chat_name, path):
        """Envía un archivo a un chat especificado en WhatsApp Web usando Playwright"""
        try:
            if not os.path.isfile(path):
                msg = f"El archivo no existe: {path}"
                await self.client.emit("on_error", msg)
                return False

            if not await self.client.wait_until_logged_in():
                msg = "No se pudo iniciar sesión"
                await self.client.emit("on_error", msg)
                return False

            if not await self.open(chat_name):
                msg = f"No se pudo abrir el chat: {chat_name}"
                await self.client.emit("on_error", msg)
                return False

            await self._page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=10000)

            attach_btn = await self._page.wait_for_selector(
                loc.ATTACH_BUTTON, timeout=5000
            )
            await attach_btn.click()

            input_files = await self._page.query_selector_all(loc.FILE_INPUT)
            if not input_files:
                msg = "No se encontró input[type='file']"
                await self.client.emit("on_error", msg)
                return False

            await input_files[0].set_input_files(path)
            await self.client.asyncio.sleep(1)

            send_btn = await self._page.wait_for_selector(
                loc.SEND_BUTTON, timeout=10000
            )
            await send_btn.click()

            return True

        except Exception as e:
            msg = f"Error inesperado en send_file: {str(e)}"
            await self.client.emit("on_error", msg)
            await self._page.screenshot(path="debug_send_file/error_unexpected.png")
            return False
        finally:
            await self.close()

    async def close(self):
        """Cierra el chat o la vista actual presionando Escape."""
        if self._page:
            try:
                await self._page.keyboard.press("Escape")
            except Exception as e:
                await self.client.emit(
                    "on_warning", f"Error trying to close chat with Escape: {e}"
                )

    async def open(
        self, chat_name: str, timeout: int = 10000, force_open: bool = False
    ) -> bool:
        return await self.wa_elements.open(chat_name, timeout, force_open)


    async def new_group(self, group_name: str, members: list[str]):
        return await self.wa_elements.new_group(group_name, members)

    async def add_members_to_group(self, group_name: str, members: list[str]) -> bool:
        """
        Abre un grupo y le añade nuevos miembros.
        """
        try:
            # 1. Abrir el chat del grupo
            if not await self.open(group_name):
                await self.client.emit("on_error", f"No se pudo abrir el grupo '{group_name}'")
                return False

            # 2. Llamar al método de bajo nivel para agregar miembros
            success = await self.wa_elements.add_members_to_group(group_name, members)
            return success

        except Exception as e:
            await self.client.emit("on_error", f"Error al añadir miembros al grupo '{group_name}': {e}")
            return False
