"""
Utilities for interacting with WhatsApp Web elements
"""

import asyncio
import datetime
from typing import Optional, List, Dict, Any
from playwright.async_api import (
    Page,
    ElementHandle,
    TimeoutError as PlaywrightTimeoutError,
)
import re

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
            # Asegurar que el foco está en el área principal
            try:
                main_area = await self.page.wait_for_selector('div#app div#main', timeout=3000)
                if main_area:
                    await main_area.click()
            except Exception:
                print("⚠️ No se pudo establecer el foco en el área principal")

            # Intentar primero con selectores CSS directos del nuevo botón de búsqueda (2024)
            new_selectors = [
                # Nuevos selectores 2025 (basados en el DOM actual)
                'span[data-icon="search-refreshed-thin"]',
                'button:has(span[data-icon="search-refreshed-thin"])',
                'div._ai04 button',  # selector por clase contenedora
                'button._ai08',      # selector por clase del botón
                # Selectores anteriores por si hay variantes
                'button[aria-label="Search"]',
                'button[aria-label="Buscar"]',
                '[role="button"][title="Search"]',
                '[role="button"][title="Buscar"]',
                'span[data-icon="search"]',
                'span[data-testid="search"]'
            ]
            for css in new_selectors:
                try:
                    print(f"🔍 Intentando selector directo: {css}")
                    element = await self.page.wait_for_selector(
                        css, timeout=2000, state="visible"
                    )
                    if element:
                        await element.click()
                        if await self.verify_search_active():
                            print(f"✅ Búsqueda activada con selector directo: {css}")
                            return True
                except Exception as e:
                    print(f"❌ Selector directo falló: {css} - Error: {e}")

            # Intentar con cada selector del botón de búsqueda de locator.py
            for selector in loc.SEARCH_BUTTON:
                try:
                    print(f"🔍 Intentando selector de locator.py: {selector}")
                    element = await self.page.wait_for_selector(
                        selector, timeout=2000, state="visible"
                    )
                    if element:
                        await element.click()
                        if await self.verify_search_active():
                            print(f"✅ Búsqueda activada con selector de locator: {selector}")
                            return True
                except Exception as e:
                    print(f"❌ Selector de locator falló: {selector} - Error: {e}")
                    continue

            # Si no funcionó el clic directo, intentar con atajos de teclado
            # Añadimos variantes para soportar layouts donde '/' requiere AltGr/Alt
            # Intentar la secuencia especial para Ctrl+Alt+Shift+7
            try:
                print("🔑 Intentando secuencia especial Ctrl+Alt+Shift+7...")
                # Click en el área de chats primero
                chats_area = await self.page.wait_for_selector('#pane-side', timeout=3000)
                if chats_area:
                    await chats_area.click()
                    # Pequeña pausa para que el foco se establezca
                    await asyncio.sleep(0.5)
                    # Presionar la combinación
                    await self.page.keyboard.press("Control+Alt+/")
                    if await self.verify_search_active():
                        print("✅ Búsqueda activada con Ctrl+Alt+/")
                        return True
                    print("⚠️ Ctrl+Alt+Shift+7 presionado pero no activó la búsqueda")
            except Exception as e:
                print(f"❌ Error en secuencia Ctrl+Alt+Shift+7: {e}")

            # Otros atajos como fallback
            shortcuts = [
                # Atajos alternativos
                "Control+Alt+Shift+Digit7",  # Alternativa por si el layout requiere Digit7
                # Atajos tradicionales
                "Control+/",
                "Control+Alt+/",  # Por si el layout usa AltGr
                "Alt+/",
                "Control+f",
                "/",
                "Slash",
            ]
            for shortcut in shortcuts:
                try:
                    print(f"🔑 Probando atajo: {shortcut}")
                    await self.page.keyboard.press("Escape")  # Limpiar estado actual
                    await self.page.keyboard.press(shortcut)
                    if await self.verify_search_active():
                        print(f"✅ Búsqueda activada con atajo: {shortcut}")
                        return True
                    else:
                        print(f"⚠️ Atajo {shortcut} presionado pero no activó la búsqueda")
                except Exception as e:
                    # Registrar el error para depuración pero continuar con el siguiente atajo
                    print(f"❌ Error al usar atajo {shortcut}: {e}")
                    continue

            return False

        except Exception as e:
            print(f"Error clicking search button: {e}")
            return False

    async def verify_search_active(self) -> bool:
        """Verifica si la búsqueda está activa usando múltiples indicadores"""
        try:
            # Verificar estructura específica del input de búsqueda (2025)
            active_search_selectors = [
                # La clase específica del contenedor de búsqueda activo
                'div._ak9t',
                # El div con el input de búsqueda lexical
                'div.lexical-rich-text-input div[aria-label="Cuadro de texto para ingresar la búsqueda"]',
                # El placeholder específico cuando está activo
                'div[aria-placeholder="Buscar un chat o iniciar uno nuevo"]',
                # La estructura específica del editor
                'div[data-lexical-editor="true"]'
            ]

            for selector in active_search_selectors:
                try:
                    print(f"🔍 Verificando búsqueda con selector: {selector}")
                    element = await self.page.wait_for_selector(
                        selector, timeout=2000, state="visible"
                    )
                    if element:
                        # Si encontramos cualquiera de estos elementos, la búsqueda está activa
                        print(f"✅ Búsqueda confirmada activa con selector: {selector}")
                        return True
                except Exception as e:
                    print(f"⚠️ Selector de verificación falló: {selector} - {str(e)}")
                    continue

            print("❌ No se encontraron indicadores de búsqueda activa")
            return False

        except Exception as e:
            print(f"❌ Error verificando búsqueda activa: {str(e)}")
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

    async def open(self, chat_name: str, timeout: int = 10000, open_via_url: bool = False) -> bool:
        """
        Abre un chat por su nombre visible o número. Si no está visible, lo busca.
        """
        if open_via_url:
            numero_limpio = re.sub(r"\D", "", chat_name)
            # Asumimos que si no tiene +, es un número local que puede necesitar el prefijo de país.
            # Esta lógica puede necesitar ser ajustada dependiendo del caso de uso.
            # Por ahora, simplemente limpiamos y usamos el número.
            url = f"https://web.whatsapp.com/send?phone={numero_limpio}"
            print(f"🌐 Abriendo chat por URL: {url}")
            try:
                await self.page.goto(url, timeout=60000) # Timeout más largo para la navegación
                
                # Esperar a que la interfaz principal de WhatsApp cargue
                await self.page.wait_for_selector(loc.LOGGED_IN, timeout=30000)
                print("✅ Interfaz principal de WhatsApp cargada.")

                # Esperar a que el input de chat aparezca o a un mensaje de "número inválido".
                await self.page.wait_for_selector(
                    f"{loc.CHAT_INPUT_BOX}|{loc.INVALID_NUMBER_WARNING}", 
                    timeout=timeout
                )
                
                # Verificar si el número es inválido
                invalid_warning = await self.page.query_selector(loc.INVALID_NUMBER_WARNING)
                if invalid_warning and await invalid_warning.is_visible():
                    print(f"❌ El número de teléfono '{chat_name}' parece ser inválido.")
                    return False

                print(f"✅ Chat con '{chat_name}' abierto vía URL.")
                return True
            except PlaywrightTimeoutError:
                print(f"⏱️❌ Timeout abriendo el chat con '{chat_name}' vía URL.")
                return False
            except Exception as e:
                print(f"💥❌ Error abriendo el chat con '{chat_name}' vía URL: {e}")
                return False

        es_numero = False
        chat_name_normalizado = None

        span_xpath = f"//span[contains(@title, {repr(chat_name)})]"

        try:
            chat_element = await self.page.query_selector(f"xpath={span_xpath}")
            if chat_element:
                await chat_element.click()
                print(f"✅ Chat '{chat_name}' abierto directamente.")
            else:
                print(f"🔍 Chat '{chat_name}' no visible, usando buscador...")
                # Esperar a que la UI esté completamente cargada
                await asyncio.sleep(2)
                # Capturar estado antes de intentar búsqueda
                await self.page.screenshot(path="before_search.png")
                # Intentar el método centralizado y más robusto para activar la búsqueda
                activated = await self.click_search_button()
                if not activated:
                    await self.page.screenshot(path="no_search_button.png")
                    raise Exception("❌ Botón de búsqueda no encontrado")

                # Buscar y llenar el input con más tiempo de espera
                for j, input_xpath in enumerate(loc.SEARCH_TEXT_BOX):
                    inputs = await self.page.query_selector_all(f"xpath={input_xpath}")
                    if inputs:
                        print(f"⌨️ Esperando que el input esté listo...")
                        await asyncio.sleep(1)  # Esperar que el input esté realmente listo
                        
                        print(f"⌨️ Llenando input de búsqueda [{input_xpath}] con: {chat_name}")
                        await self.page.screenshot(path=f"search_input_{j}.png")
                        
                        # Limpiar el input primero
                        await inputs[0].fill("")
                        await asyncio.sleep(0.5)  # Esperar que se limpie
                        
                        # Escribir caracteres con delay
                        await inputs[0].type(chat_name, delay=100)  # 100ms entre cada caracter
                        print("📝 Texto ingresado, esperando resultados...")
                        await asyncio.sleep(1)  # Esperar que aparezcan resultados
                        break
                else:
                    raise Exception("❌ Input de búsqueda no encontrado")

                # Esperar y verificar resultados de búsqueda
                print("🔍 Esperando resultados de búsqueda...")
                results = await self.page.wait_for_selector(loc.SEARCH_ITEM, timeout=5000)
                if not results:
                    raise Exception("❌ No se encontraron resultados de búsqueda")
                
                # Esperar un momento para que los resultados se carguen completamente
                await asyncio.sleep(1)
                
                # Buscar el chat específico en los resultados
                chat_results = await self.page.query_selector_all(loc.SEARCH_ITEM)
                for chat in chat_results:
                    title = await chat.get_attribute("title")
                    if title and chat_name.lower() in title.lower():
                        print(f"✅ Chat encontrado: {title}")
                        await chat.click()
                        print(f"✅ Chat '{chat_name}' abierto desde buscador.")
                        break
                else:
                    # Si no encontramos el chat específico, usar el comportamiento anterior
                    print("⚠️ Chat específico no encontrado, usando primer resultado...")
                    await self.page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.5)  # Esperar antes de Enter
                    await self.page.keyboard.press("Enter")
                    print(f"✅ Chat '{chat_name}' abierto desde buscador.")

            await self.page.wait_for_selector(loc.CHAT_INPUT_BOX, timeout=timeout)
            print("esperando input box...")
            return True

        except PlaywrightTimeoutError:
            print(f"⏱️❌ Timeout esperando el input del chat '{chat_name}'")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"search_timeout_error_{timestamp}.png")
            return False

        except Exception as e:
            print(f"💥❌ Error al abrir el chat '{chat_name}': {e}")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"search_exception_error_{timestamp}.png")
            return False


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
            
    async def add_members_to_group(
        self, group_name: str, members: List[str]
    ) -> bool:
        """
        Agrega miembros a un grupo existente. Asume que el chat del grupo ya está abierto.
        """
        try:
            if not self.open(group_name, timeout=5000):
                print(f"❌ No se pudo abrir el grupo '{group_name}'")
                return False
            
            # 2. Hacer clic en la cabecera para abrir la info del grupo
            header = await self.page.wait_for_selector(loc.GROUP_INFO_BUTTON, timeout=5000)
            await header.click()

            # 2. Buscar y hacer clic en el botón "Add participant"
            # Usamos un selector de texto porque es más robusto
            add_participant_button = await self.page.wait_for_selector(
                loc.ADD_MEMBERS_BUTTON, timeout=5000
            )
            await add_participant_button.click()

            # 3. Agregar cada miembro
            member_input = await self.page.wait_for_selector(
                loc.INPUT_MEMBERS_GROUP, timeout=5000
            )
            for member in members:
                await member_input.fill(member)
                await asyncio.sleep(0.5)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(0.5)

            # 4. Confirmar la adición
            confirm_button = await self.page.wait_for_selector(
                loc.CONFIRM_ADD_MEMBERS_BUTTON, timeout=5000
            )
            await confirm_button.click()
            await asyncio.sleep(0.5)  # Esperar un poco para que se procese
            
            confirm_add_button = await self.page.wait_for_selector('//div[text()="Add member"]', timeout=3000)
            
            # Esperar un poco para que se procese y cerrar el panel
            await asyncio.sleep(1)
            await self.page.keyboard.press("Escape")
            return True

        except PlaywrightTimeoutError:
            print(f"Timeout al intentar agregar miembros a '{group_name}'")
            await self.page.keyboard.press("Escape") # Intentar limpiar
            return False
        except Exception as e:
            print(f"Error agregando miembros a '{group_name}': {e}")
            await self.page.keyboard.press("Escape") # Intentar limpiar
            return False
    async def del_member_group(self, group_name: str, member_name: str) -> bool:
        """
        Elimina un miembro de un grupo existente. Asume que el chat del grupo ya está abierto.
        """
        try:
            if not await self.open(group_name, timeout=5000):
                print(f"❌ No se pudo abrir el grupo '{group_name}'")
                return False

            # 1. Abrir info de grupo
            print(" 1. Esperando GROUP_INFO_BUTTON...")
            header = await self.page.wait_for_selector(loc.GROUP_INFO_BUTTON, timeout=5000)
            await header.click()

            # 2. Contenedor de info del grupo
            print(" 2. Esperando contenedor 'Group info'...")
            group_info = await self.page.wait_for_selector('div[aria-label="Group info"]', timeout=5000)
            if not group_info:
                print("❌ No se encontró el contenedor 'Group info'")
                return False

            # 3. Buscar el <span> del miembro por coincidencia parcial
            print(" 3. Buscando miembro por coincidencia parcial...")
            span_member = await group_info.evaluate_handle(
                f"""
                (container) => {{
                    const spans = Array.from(container.querySelectorAll('span[title]'));
                    return spans.find(s => s.textContent.trim().toLowerCase().includes("{member_name.lower()}")) || null;
                }}
                """
            )

            # ⚠️ Verificar si se encontró o no
            if not await span_member.evaluate("el => !!el"):
                print(f"❌ No se encontró el miembro '{member_name}'")
                return False

            # 4. Subir al contenedor general del miembro (div[role="button"])
            member_row = await span_member.evaluate_handle("el => el.closest('div[role=\"button\"]')")
            if not await member_row.evaluate("el => !!el"):
                print("⚠️ No se encontró el contenedor del miembro")
                return False

            # 5. Buscar el contenedor del status
            status_container = await member_row.evaluate_handle(
                """(row) => {
                    const divs = Array.from(row.querySelectorAll('div'));
                    return divs.find(div => {
                        const span = div.querySelector('span');
                        return span && span.getAttribute('title');
                    }) || null;
                }"""
            )
            if not await status_container.evaluate("el => !!el"):
                print("⚠️ No se encontró el contenedor del estado del miembro")
                return False

            # 6. Hover sobre el estado
            print(" 4. Hover sobre el estado...")
            await status_container.scroll_into_view_if_needed()
            await status_container.hover()
            print(f"✅ Hover sobre el estado de '{member_name}'")

            # 7. Esperar botón de menú
            print(" 5. Esperando botón ⋮ ...")
            try:
                menu_btn = await self.page.wait_for_selector(
                    'button[aria-label="Open the chat context menu"]',
                    timeout=3000
                )
                await menu_btn.click()
                print("✅ Menú contextual clickeado correctamente.")
            except Exception as e:
                print(f"❌ No se pudo hacer clic en el botón del menú: {e}")
                return False

            # 8. Clic en "Remove"
            remove_button = await self.page.wait_for_selector(loc.REMOVE_MEMBER_BUTTON, timeout=5000)
            await remove_button.click()
            await asyncio.sleep(0.5)

            # 9. Confirmar
            confirm_button = await self.page.wait_for_selector('//div[text()="Remove"]', timeout=3000)
            await confirm_button.click()
            await asyncio.sleep(0.5)

            print(f"✅ Miembro '{member_name}' eliminado de '{group_name}'.")
            return True

        except PlaywrightTimeoutError:
            print(f"⏱️ Timeout al intentar eliminar miembro de '{group_name}'")
            await self.page.keyboard.press("Escape")
            return False
        except Exception as e:
            print(f"❌ Error eliminando miembro '{member_name}' de '{group_name}': {e}")
            await self.page.keyboard.press("Escape")
            return False
