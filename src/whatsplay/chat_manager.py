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
    async def _check_unread_chats(self, debug=False):
        unread_chats = []
        page = self._page
        
        try:
            # DEBUG: Inspeccionar estructura general si está activado
            if debug:
                total_items = await page.locator("[role='listitem']").count()
                print(f"DEBUG: Total elementos listitem en la página: {total_items}")
                
                # Analizar primeros 3 chats para entender la estructura
                for i in range(min(3, total_items)):
                    item = page.locator("[role='listitem']").nth(i)
                    text_content = await item.text_content()
                    
                    print(f"\n--- ESTRUCTURA CHAT {i+1} ---")
                    print(f"Texto: {text_content[:80]}...")
                    
                    # Verificar badges existentes
                    badges_x140p0ai = await item.locator(".x140p0ai").count()
                    badges_ahlk = await item.locator("._ahlk").count() 
                    badges_xn58pb5 = await item.locator(".xn58pb5").count()
                    
                    print(f"Badges .x140p0ai: {badges_x140p0ai}")
                    print(f"Badges ._ahlk: {badges_ahlk}")
                    print(f"Badges .xn58pb5: {badges_xn58pb5}")
                    
                    # Verificar aria-labels relevantes con timeout más corto
                    try:
                        aria_elements = await item.locator("[aria-label*='unread' i], [aria-label*='message' i]").all(timeout=5000)
                        for elem in aria_elements:
                            label_text = await elem.get_attribute("aria-label", timeout=2000)
                            if label_text:
                                print(f"Aria-label relevante: {label_text}")
                    except Exception as e:
                        if debug:
                            print(f"DEBUG: Timeout en aria-labels para chat {i+1}: {e}")
            
            # CAMBIO CRÍTICO: Buscar directamente en toda la página, no en una "lista"
            # porque el problema es que no encuentra la lista contenedora correcta
            items_unread = page.locator(
                # Estrategia DIRECTA: buscar listitem con badges específicos
                "[role='listitem']:has(.x140p0ai), "  # Badge principal
                "[role='listitem']:has(._ahlk), "     # Contenedor del badge  
                "[role='listitem']:has(.xn58pb5), "   # Badge específico
                
                # Estrategia de aria-labels
                "[role='listitem']:has([aria-label*='unread' i]), "
                "[role='listitem']:has([aria-label*='message' i]:not([aria-label*='0 message'])), "
                "[role='listitem']:has([aria-label*='no leído' i]), "
                "[role='listitem']:has([aria-label*='sin leer' i])"
            )
            
            n = await items_unread.count()
            if debug:
                print(f"DEBUG: Selector directo encontró {n} chats no leídos")
            
            if n == 0:
                if debug:
                    print("DEBUG: Selector directo no encontró nada. Probando selector por posición...")
                
                # Si no funciona el selector, buscar por posición específica
                # Sabemos que chat 1 tiene badges según el debug
                first_chat = page.locator("[role='listitem']").first
                has_badge_first = await first_chat.locator(".x140p0ai, ._ahlk, .xn58pb5").count()
                
                if debug:
                    print(f"DEBUG: Primer chat tiene {has_badge_first} badges")
                
                if has_badge_first > 0:
                    if debug:
                        print("DEBUG: Agregando primer chat manualmente...")
                    items_unread = page.locator("[role='listitem']").first
                    n = 1
                else:
                    # Lista virtualizada: scroll más suave y específico
                    if debug:
                        print("DEBUG: Intentando scroll...")
                    
                    await page.mouse.wheel(0, 800)
                    await asyncio.sleep(0.3)
                    await page.mouse.wheel(0, -800)
                    await asyncio.sleep(0.3)
                    
                    # Reintentar detección
                    items_unread = page.locator("[role='listitem']:has(.x140p0ai), [role='listitem']:has(._ahlk)")
                    n = await items_unread.count()
                    if debug:
                        print(f"DEBUG: Después del scroll se encontraron {n} chats no leídos")
            
            # Procesar los chats encontrados
            for i in range(n):
                try:
                    # Si n=1 y usamos first, no usar nth()
                    if n == 1 and isinstance(items_unread.locator, type(page.locator("[role='listitem']").first.locator)):
                        item = items_unread
                    else:
                        item = items_unread.nth(i)
                    
                    # DEBUG: Información detallada del item
                    if debug:
                        try:
                            item_text = await item.text_content(timeout=5000)
                            print(f"\n--- PROCESANDO CHAT {i+1} ---")
                            print(f"Texto del chat: {item_text[:60]}...")
                        except Exception as text_error:
                            print(f"\n--- PROCESANDO CHAT {i+1} ---")
                            print(f"Error obteniendo texto: {text_error}")
                    
                    # Verificación adicional: asegurar que realmente tiene badge de no leído
                    has_badge = await item.locator(
                        ".x140p0ai, "  # Badge principal
                        "[aria-label*='unread' i], "
                        "[aria-label*='message' i], "
                        "._ahlk, "
                        ".xn58pb5"
                    ).count()
                    
                    if debug:
                        print(f"Badges confirmados en este chat: {has_badge}")
                    
                    if has_badge > 0:
                        # Si tu parser espera ElementHandle:
                        handle = await item.element_handle()
                        chat_result = await self._parse_search_result(handle, "CHATS")
                        
                        if chat_result:
                            unread_chats.append(chat_result)
                            if debug:
                                print(f"✓ Chat no leído agregado: {chat_result.get('name', 'Sin nombre')}")
                        elif debug:
                            print("✗ Parser no pudo procesar este chat")
                    elif debug:
                        print("✗ Chat descartado: no tiene badge de no leído")
                            
                except Exception as item_error:
                    if debug:
                        print(f"DEBUG: Error procesando item {i}: {item_error}")
                    continue
                    
        except Exception as e:
            await self.client.emit("on_warning", f"Error detectando no leídos (adaptado): {e}")
            if debug:
                print(f"DEBUG: Error general: {e}")
        
        if debug:
            print(f"\nDEBUG: ===== RESUMEN =====")
            print(f"Total chats no leídos encontrados: {len(unread_chats)}")
            for i, chat in enumerate(unread_chats):
                print(f"  {i+1}. {chat.get('name', 'Sin nombre')}")
        
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
        return await self.wa_elements.open(chat_name, timeout, force_open)

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
