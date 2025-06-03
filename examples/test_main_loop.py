import asyncio
import sys
import os

# Añadir el directorio src al path para poder importar el módulo whatsplay
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.whatsplay.client import Client
from src.whatsplay.constants.states import State


class TestClient(Client):
    """Cliente de prueba que sobrescribe algunos métodos para simular comportamientos"""
    
    def __init__(self, headless=False):
        super().__init__(headless=headless)
        self.test_state = None
        self.test_qr_shown = False
        self.test_contact = "yo"
        
    async def _get_state(self):
        """Sobrescribe el método _get_state para simular cambios de estado"""
        # Simular una secuencia de estados para probar el main loop
        if self.test_state is None:
            self.test_state = State.QR_AUTH
            return State.QR_AUTH
        
        # Después de mostrar el QR, simular inicio de sesión
        if self.test_state == State.QR_AUTH and self.test_qr_shown:
            self.test_state = State.LOADING
            return State.LOADING
            
        # Después de cargar, simular inicio de sesión exitoso
        if self.test_state == State.LOADING:
            self.test_state = State.LOGGED_IN
            return State.LOGGED_IN
            
        return self.test_state
    
    async def _extract_image_from_canvas(self, canvas_element):
        """Simula la extracción de imagen del código QR"""
        self.test_qr_shown = True
        # Retornar bytes simulados de una imagen
        return b'FAKE_QR_CODE_IMAGE'
    
    async def _is_present(self, selector):
        """Simula la presencia de elementos en la página"""
        return True
    
    async def _parse_search_result(self, element, result_type="CHATS"):
        """Simula el parseo de resultados de búsqueda"""
        return {
            "type": result_type,
            "name": self.test_contact,
            "last_activity": "en línea",
            "element": None
        }


# Manejadores de eventos para pruebas
async def on_start():
    print("Cliente iniciado")

async def on_auth():
    print("Pantalla de autenticación mostrada")

async def on_qr(qr_binary):
    print(f"Código QR generado: {len(qr_binary)} bytes")

async def on_loading(is_loading):
    print(f"Cargando: {is_loading}")

async def on_logged_in():
    print("Sesión iniciada correctamente")

async def on_unread_chat(chat):
    print(f"Chat no leído: {chat['name']}")

async def on_tick():
    pass  # No imprimir nada para evitar spam

async def on_error(error):
    print(f"ERROR: {error}")


async def main():
    # Crear cliente de prueba
    client = TestClient(headless=True)
    
    # Registrar manejadores de eventos
    client.event("on_start")(on_start)
    client.event("on_auth")(on_auth)
    client.event("on_qr")(on_qr)
    client.event("on_loading")(on_loading)
    client.event("on_logged_in")(on_logged_in)
    client.event("on_unread_chat")(on_unread_chat)
    client.event("on_tick")(on_tick)
    client.event("on_error")(on_error)
    
    # Iniciar el cliente (esto ejecutará _main_loop internamente)
    try:
        # Sobrescribir el método _initialize_browser para evitar iniciar Playwright
        client._initialize_browser = lambda: asyncio.sleep(0)
        client._is_running = True
        
        # Ejecutar el main loop directamente
        await client._main_loop()
        
        # Esperar un tiempo para que se ejecute el ciclo
        await asyncio.sleep(5)
        
        # Detener el cliente
        client._is_running = False
        print("Test completado")
        
    except Exception as e:
        print(f"Error en el test: {e}")
    finally:
        # Asegurar que el cliente se detiene
        client._is_running = False


if __name__ == "__main__":
    asyncio.run(main())