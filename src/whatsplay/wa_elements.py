"""
Utilities for interacting with WhatsApp Web elements
"""
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, ElementHandle, TimeoutError as PlaywrightTimeoutError

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
                print("Logged in")
                return State.LOGGED_IN
            elif await self.page.locator(loc.LOADING).is_visible():
                print("Loading")
                return State.LOADING
            elif await self.page.locator(loc.QR_CODE).is_visible():
                print("QR auth")
                return State.QR_AUTH
            elif await self.page.locator(loc.AUTH).is_visible():
                print("Auth")
                return State.AUTH
            return None
        except Exception:
            return None

    async def wait_for_selector(self, 
                              selector: str, 
                              timeout: int = 5000, 
                              state: str = "visible") -> Optional[ElementHandle]:
        """
        Espera por un elemento y lo retorna cuando está disponible
        """
        try:
            element = await self.page.wait_for_selector(
                selector,
                timeout=timeout,
                state=state
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
                    element = await self.page.wait_for_selector(selector, timeout=1000, state='visible')
                    if element:
                        await element.click()
                        await self.page.wait_for_timeout(1000)
                        if await self.verify_search_active():
                            return True
                except Exception:
                    continue

            # Si no funcionó el clic directo, intentar con atajos de teclado
            shortcuts = ["Control+/", "Control+f", "/", "Slash"]
            for shortcut in shortcuts:
                try:
                    await self.page.keyboard.press("Escape")  # Limpiar estado actual
                    await self.page.wait_for_timeout(500)
                    await self.page.keyboard.press(shortcut)
                    await self.page.wait_for_timeout(1000)
                    
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
            cancel_button = await self.wait_for_selector(loc.CANCEL_SEARCH, timeout=1000)
            if cancel_button:
                return True

            # Verificar si algún campo de búsqueda está visible
            for selector in loc.SEARCH_TEXT_BOX:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=1000, state='visible')
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

    async def search_chats(self, query: str, close = True) -> List[Dict[str, Any]]:
        """Busca chats usando un término y retorna los resultados"""
        results = []
        try:
            # Activar búsqueda
            if not await self.click_search_button():
                print("Could not activate search")
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
                print("Could not find search text box")
                return results

            # Escribir consulta con reintento
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    await search_box.click()
                    await self.page.wait_for_timeout(500)
                    await search_box.fill("")
                    await search_box.type(query, delay=100)
                    break
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"Could not type in search box: {e}")
                        return results
                    await self.page.wait_for_timeout(1000)

            # Esperar resultados
            results_container = await self.wait_for_selector(loc.SEARCH_RESULT, timeout=5000)
            if not results_container:
                print("No search results found")
                return results

            # Pequeña pausa para cargar resultados
            await self.page.wait_for_timeout(1000)

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
