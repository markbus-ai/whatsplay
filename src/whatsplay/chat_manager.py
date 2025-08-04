import re
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
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

    async def _check_unread_chats(self):
        """Verifica y devuelve los chats no leídos"""
        unread_chats = []
        try:
            unread_button = await self._page.query_selector(loc.UNREAD_CHATS_BUTTON)
            if unread_button:
                await unread_button.click()
                await asyncio.sleep(self.client.unread_messages_sleep)

                chat_list = await self._page.query_selector_all(loc.UNREAD_CHAT_DIV)
                if chat_list and len(chat_list) > 0:
                    chats = await chat_list[0].query_selector_all(loc.SEARCH_ITEM)
                    for chat in chats:
                        chat_result = await self._parse_search_result(chat, "CHATS")
                        if chat_result:
                            unread_chats.append(chat_result)

            # Volver a la vista de todos los chats
            all_button = await self._page.query_selector(loc.ALL_CHATS_BUTTON)
            if all_button:
                await all_button.click()

        except Exception as e:
            await self.client.emit("on_warning", f"Error al verificar chats no leídos: {e}")

        return unread_chats

    async def _parse_search_result(
        self, element, result_type: str = "CHATS"
    ) -> Optional[Dict[str, Any]]:
        try:
            components = await element.query_selector_all(
                "xpath=.//div[@role='gridcell' and @aria-colindex='2']/parent::div/div"
            )
            count = len(components)

            unread_el = await element.query_selector(
                f"xpath={loc.SEARCH_ITEM_UNREAD_MESSAGES}"
            )
            unread_count = await unread_el.inner_text() if unread_el else "0"
            mic_span = await components[1].query_selector('xpath=.//span[@data-icon="mic"]')
            
            if count == 3:
                span_title_0 = await components[0].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                group_title = (
                    await span_title_0.get_attribute("title") if span_title_0 else ""
                )

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = (
                    await datetime_children[1].text_content()
                    if len(datetime_children) > 1
                    else ""
                )

                span_title_1 = await components[1].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                title = (
                    await span_title_1.get_attribute("title") if span_title_1 else ""
                )

                info_text = (await components[2].text_content()) or ""
                info_text = info_text.replace("\n", "")

                if "loading" in info_text or "status-" in info_text or "typing" in info_text:
                    return None

                return {
                    "type": result_type,
                    "group": group_title,
                    "name": title,
                    "last_activity": datetime_text,
                    "last_message": info_text,
                    "last_message_type": "audio" if mic_span else "text",
                    "unread_count": unread_count,
                    "element": element,
                }

            elif count == 2:
                span_title_0 = await components[0].query_selector(
                    f"xpath={loc.SPAN_TITLE}"
                )
                title = (
                    await span_title_0.get_attribute("title") if span_title_0 else ""
                )

                datetime_children = await components[0].query_selector_all("xpath=./*")
                datetime_text = (
                    await datetime_children[1].text_content()
                    if len(datetime_children) > 1
                    else ""
                )

                info_children = await components[1].query_selector_all("xpath=./*")
                info_text = (
                    await info_children[0].text_content()
                    if len(info_children) > 0
                    else ""
                ) or ""
                info_text = info_text.replace("\n", "")
                if "loading" in info_text or "status-" in info_text or "typing" in info_text:
                    return None

                return {
                    "type": result_type,
                    "name": title,
                    "last_activity": datetime_text,
                    "last_message": info_text,
                    "last_message_type": "audio" if mic_span else "text",
                    "unread_count": unread_count,
                    "element": element,
                    "group": None,
                }

            return None

        except Exception as e:
            print(f"Error parsing result: {e}")
            return None

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
        """
        Abre un chat por su nombre visible. Si no está en el DOM, lo busca y lo abre.
        """
        page = self._page
        es_numero = bool(re.fullmatch(r"\+?\d+", chat_name))

        if es_numero or force_open:
            numero = chat_name.lstrip("+")
            url = f"https://web.whatsapp.com/send?phone={numero}"
            await page.goto(url)
        
        span_xpath = f"//span[contains(@title, {repr(chat_name)})]"

        try:
            chat_element = await page.query_selector(f"xpath={span_xpath}")
            if chat_element:
                await chat_element.click()
                print(f"✅ Chat '{chat_name}' abierto directamente.")
            else:
                print(f"🔍 Chat '{chat_name}' no visible, usando buscador...")
                for btn in loc.SEARCH_BUTTON:
                    btns = await page.query_selector_all(f"xpath={btn}")
                    if btns:
                        await btns[0].click()
                        break
                else:
                    raise Exception("❌ Botón de búsqueda no encontrado")

                for input_xpath in loc.SEARCH_TEXT_BOX:
                    inputs = await page.query_selector_all(f"xpath={input_xpath}")
                    if inputs:
                        await inputs[0].fill(chat_name)
                        break
                else:
                    raise Exception("❌ Input de búsqueda no encontrado")

                await page.wait_for_selector(loc.SEARCH_ITEM, timeout=timeout)
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
                print(f"✅ Chat '{chat_name}' abierto desde buscador.")

            await page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=timeout)
            return True

        except PlaywrightTimeoutError:
            print(f"❌ Timeout esperando el input del chat '{chat_name}'")
            return False
        except Exception as e:
            print(f"❌ Error al abrir el chat '{chat_name}': {e}")
            return False

    async def search_conversations(
        self, query: str, close=True
    ) -> List[Dict[str, Any]]:
        """Busca conversaciones por término"""
        if not await self.client.wait_until_logged_in():
            return []
        try:
            return await self.wa_elements.search_chats(query, close)
        except Exception as e:
            await self.client.emit("on_error", f"Search error: {e}")
            return []

    async def collect_messages(self) -> List[Union[Message, FileMessage]]:
        """
        Recorre todos los contenedores de mensaje (message-in/message-out) actualmente visibles
        y devuelve una lista de instancias Message o FileMessage.
        """
        resultados: List[Union[Message, FileMessage]] = []
        msg_elements = await self._page.query_selector_all(
            'div[class*="message-in"], div[class*="message-out"]'
        )

        for elem in msg_elements:
            file_msg = await FileMessage.from_element(elem)
            if file_msg:
                resultados.append(file_msg)
                continue

            simple_msg = await Message.from_element(elem)
            if simple_msg:
                resultados.append(simple_msg)

        return resultados

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

    async def new_group(self, group_name: str, members: list[str]):
        return await self.wa_elements.new_group(group_name, members)
