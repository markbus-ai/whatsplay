"""
Utilities for interacting with WhatsApp Web elements
"""

import asyncio
from typing import Optional, List, Dict, Any
from playwright.async_api import (
    Page,
    ElementHandle,
    TimeoutError as PlaywrightTimeoutError,
)

from .constants import locator as loc
from .constants.states import State
from .filters import MessageFilter


class WhatsAppElements:
    """Helper class for interacting with WhatsApp Web elements"""

    def __init__(self, page: Page):
        self.page = page

    async def get_state(self) -> Optional[State]:
        """
        Determina el estado actual de WhatsApp Web basado en los elementos visibles
        """
        try:
            # Checkear en orden de prioridad
            if await self.page.locator(loc.LOGGED_IN).is_visible():
                print("LOGGED_IN")
                return State.LOGGED_IN
            elif await self.page.locator(loc.LOADING).is_visible():
                print("LOADING")
                return State.LOADING
            elif await self.page.locator(loc.QR_CODE).is_visible():
                print("QR_AUTH")
                return State.QR_AUTH
            elif await self.page.locator(loc.AUTH).is_visible():
                print("AUTH")
                return State.AUTH
            elif await self.page.locator(loc.LOADING_CHATS).is_visible():
                print("LOADING_CHATS")
                return State.LOADING
            return None
        except Exception:
            return None

    async def wait_for_selector(
        self, selector: str, timeout: int = 5000, state: str = "visible"
    ) -> Optional[ElementHandle]:
        """
        Espera por un elemento y lo retorna cuando está disponible
        """
        try:
            element = await self.page.wait_for_selector(
                selector, timeout=timeout, state=state
            )
            return element
        except PlaywrightTimeoutError:
            return None

    async def click_search_button(self) -> bool:
        """Intenta hacer click en el botón de búsqueda usando múltiples estrategias"""
        try:
            # Intentar con cada selector del botón de búsqueda
            for selector in loc.SEARCH_BUTTON:
                try:
                    element = await self.page.wait_for_selector(
                        selector, timeout=1000, state="visible"
                    )
                    if element:
                        await element.click()
                        if await self.verify_search_active():
                            return True
                except Exception:
                    continue

            # Si no funcionó el clic directo, intentar con atajos de teclado
            shortcuts = ["Control+/", "Control+f", "/", "Slash"]
            for shortcut in shortcuts:
                try:
                    await self.page.keyboard.press("Escape")  # Limpiar estado actual
                    await self.page.keyboard.press(shortcut)
                    if await self.verify_search_active():
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            print(f"Error clicking search button: {e}")
            return False

    async def verify_search_active(self) -> bool:
        """Verifica si la búsqueda está activa usando múltiples indicadores"""
        try:
            # Verificar si el botón de cancelar búsqueda está visible
            cancel_button = await self.wait_for_selector(
                loc.CANCEL_SEARCH, timeout=1000
            )
            if cancel_button:
                return True

            # Verificar si algún campo de búsqueda está visible
            for selector in loc.SEARCH_TEXT_BOX:
                try:
                    element = await self.page.wait_for_selector(
                        selector, timeout=1000, state="visible"
                    )
                    if element:
                        return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    async def get_qr_code(self) -> Optional[bytes]:
        """
        Obtiene la imagen del código QR si está disponible
        """
        try:
            qr_element = await self.wait_for_selector(loc.QR_CODE)
            if qr_element:
                return await qr_element.screenshot()
            return None
        except Exception:
            return None

    async def search_chats(self, query: str, close=True) -> List[Dict[str, Any]]:
        """Busca chats usando un término y retorna los resultados"""
        results = []
        try:
            # Activar búsqueda
            if not await self.click_search_button():
                return results

            # Buscar campo de texto y escribir consulta
            search_box = None
            for selector in loc.SEARCH_TEXT_BOX:
                try:
                    search_box = await self.wait_for_selector(selector, timeout=2000)
                    if search_box:
                        break
                except Exception:
                    continue

            if not search_box:
                return results

            # Escribir consulta con reintento
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    await search_box.click()
                    await search_box.fill("")
                    await search_box.type(query, delay=100)
                    break
                except Exception as e:
                    if attempt == max_attempts - 1:
                        return results

            # Esperar resultados
            results_container = await self.wait_for_selector(
                loc.SEARCH_RESULT, timeout=5000
            )
            if not results_container:
                print("No search results found")
                return results

            # Obtener y procesar resultados
            items = await self.page.locator(loc.SEARCH_ITEM).all()
            for item in items:
                text = await item.inner_text()
                if text:
                    formatted = MessageFilter.filter_search_result(text)
                    results.append(formatted)

        except Exception as e:
            print(f"Error searching chats: {e}")
        finally:
            # Cerrar búsqueda
            try:
                if close:
                    await self.page.keyboard.press("Escape")
            except:
                pass

        return results
    async def new_group(self, group_name: str, members: List[str]) -> Optional[ElementHandle]:
        print(f"Creating new group: {group_name} with members: {members}")
        """
        Crea un nuevo grupo con el nombre especificado
        """
        try:
            # Hacer click en el botón de nuevo chat
            new_chat_button = await self.page.wait_for_selector(
                loc.NEW_CHAT_BUTTON, timeout=5000
            )
            if new_chat_button:
                await new_chat_button.click()
            new_group_button = await self.page.wait_for_selector(
                loc.NEW_GROUP_BUTTON, timeout=5000
            )
            if new_group_button:
                await new_group_button.click()
            # Esperar al campo de nombre del grupo
            member_name_input = await self.page.wait_for_selector(
                loc.INPUT_MEMBERS_GROUP, timeout=5000
            )
            if member_name_input:
                for name in members:
                    await member_name_input.fill(name)
                    await asyncio.sleep(0.5)  # Esperar un poco entre entradas
                    await self.page.keyboard.press("Enter")
                    
            enter_arrow = await self.page.wait_for_selector(
                "xpath=//span[@data-icon='arrow-forward']", timeout=5000
            )
            if enter_arrow:
                await enter_arrow.click()
                
            input_group_name = await self.page.wait_for_selector(
                loc.ENTER_GROUP_NAME, timeout=5000
            )
            if input_group_name:
                await input_group_name.fill(group_name)
                await self.page.keyboard.press("Enter")
            


        except PlaywrightTimeoutError:
            print("Timeout while trying to create a new group")
            return None
        except Exception as e:
            print(f"Error creating new group: {e}")
            return None