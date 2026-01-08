# Guía: Administración de Grupos

WhatsPlay proporciona una funcionalidad robusta para gestionar grupos de WhatsApp, permitiéndote crear nuevos grupos y gestionar sus miembros programáticamente.

## Creando un Nuevo Grupo

Puedes crear un nuevo grupo de WhatsApp usando el método `client.new_group()`. Este método requiere un nombre de grupo y una lista de nombres de contacto o números de teléfono para los miembros iniciales.

**Importante:** Los contactos en la lista `members` ya deben estar en tus contactos de WhatsApp o ser números de teléfono válidos (incluyendo código de país, sin '+' ni '00').

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def create_my_group():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True) # Establece headless=False si quieres ver el navegador

    @client.event("on_start")
    async def on_start():
        print("Cliente listo. Intentando crear un nuevo grupo...")
        
        group_name = "Mi Grupo Increíble de WhatsPlay"
        # Usa nombres de contacto existentes o números de teléfono
        initial_members = ["Nombre Contacto 1", "5491123456789"] # Ejemplo: "54911..." para móvil de Argentina
        
        success = await client.new_group(group_name, initial_members)
        
        if success:
            print(f"Grupo '{group_name}' creado exitosamente con miembros iniciales.")
        else:
            print(f"Falló la creación del grupo '{group_name}'.")
            
        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR para iniciar sesión.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(create_my_group())
```

## Añadiendo Miembros a un Grupo Existente

Para añadir más miembros a un grupo ya existente, usa el método `client.add_members_to_group()`. Necesitas proporcionar el nombre del grupo y una lista de miembros para añadir.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def add_members_to_existing_group():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Cliente listo. Intentando añadir miembros a un grupo...")
        
        group_name = "Mi Grupo Increíble de WhatsPlay" # Debe ser un grupo existente
        new_members = ["Nuevo Nombre Contacto 1", "5491198765432"]
        
        success = await client.add_members_to_group(group_name, new_members)
        
        if success:
            print(f"Miembros añadidos exitosamente a '{group_name}'.")
        else:
            print(f"Falló al añadir miembros a '{group_name}'.")
            
        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR para iniciar sesión.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(add_members_to_existing_group())
```

## Eliminando Miembros de un Grupo

Puedes eliminar miembros de un grupo usando el método `client.del_members_from_group()`. Proporciona el nombre del grupo y una lista de miembros a eliminar.

```python
import asyncio
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def remove_members_from_group():
    auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
    client = Client(auth=auth, headless=True)

    @client.event("on_start")
    async def on_start():
        print("Cliente listo. Intentando eliminar miembros de un grupo...")
        
        group_name = "Mi Grupo Increíble de WhatsPlay" # Debe ser un grupo existente
        members_to_remove = ["Nombre Contacto A Eliminar", "5491112345678"]
        
        success = await client.del_members_from_group(group_name, members_to_remove)
        
        if success:
            print(f"Miembros eliminados exitosamente de '{group_name}'.")
        else:
            print(f"Falló al eliminar miembros de '{group_name}'.")
            
        await client.stop()

    @client.event("on_qr")
    async def on_qr(qr):
        print("Por favor escanea el código QR para iniciar sesión.")

    await client.start()

if __name__ == "__main__":
    asyncio.run(remove_members_from_group())
```

## Características Futuras de Gestión de Grupos (Bajo Consideración)

Aunque WhatsPlay proporciona capacidades centrales de gestión de grupos, mejoras futuras podrían incluir:

*   **Promover/Degradar Administradores de Grupo:** Funcionalidad para cambiar el estado administrativo de un miembro.
*   **Actualizar Información del Grupo:** Métodos para cambiar el asunto (nombre) o descripción del grupo después de la creación.
*   **Obtener Lista Detallada de Participantes:** Una forma de obtener una lista completa de miembros del grupo junto con sus roles (admin/participante).

¡Mantente atento a las actualizaciones a medida que WhatsPlay evoluciona!