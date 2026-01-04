# WhatsPlay 🚀

Automatización avanzada de WhatsApp Web usando Playwright, Python y visión por computadora (OpenCV).  
Permite interactuar con mensajes no leídos, autenticar mediante código QR y realizar acciones complejas a través de eventos personalizados y filtrado de mensajes.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)  
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

---

## ✨ Características

- **Eventos asíncronos:** escucha eventos como `on_start`, `on_auth`, `on_unread_chat`.
- **Persistencia de sesión:** guarda datos de autenticación en un directorio local para no escanear el QR cada vez.
- **Apertura de chat por nombre o teléfono:** si no conocés el `chat_name` exacto, pasá el número de teléfono completo (con prefijo de país).
- **Envío y recepción de mensajes** (texto y multimedia).
- **Filtros personalizados** para procesar solo los mensajes que te interesen.
- **Extracción automática de código QR** para autenticación.
- **Compatibilidad con servidores sin GUI** gracias a Playwright en modo *headless*.
- **Detección robusta de mensajes no leídos** con múltiples heurísticas (aria-labels, badges, font-weight).
- **Búsqueda mejorada** con estrategias de fallback para máxima compatibilidad.
- **Selectores actualizados** compatibles con WhatsApp Web 2024-2025.

---

## 📦 Arquitectura

- **Modularidad:** cada componente (cliente, gestor de chats, filtros, autenticación) está separado.
- **Mantenibilidad:** componentes independientes y bien definidos.
- **Testabilidad:** cada módulo puede probarse por separado.
- **Reutilización:** los módulos pueden usarse en otros proyectos.

---

## 🛠 Instalación

### Prerrequisitos

- Python 3.8 o superior

### Instalación desde PyPI

```bash
pip install whatsplay
```

Después de instalar la librería, descargá los navegadores de Playwright con:

```bash
python -m playwright install
```

---

## ▶️ Ejemplos de uso

WhatsPlay está construido sobre `asyncio`, por lo que todas las operaciones son asíncronas.
A continuación se muestra un ejemplo básico para iniciar sesión, escuchar eventos y enviar un mensaje.

**Nota:** siempre usá funciones `async def` como manejadores de eventos, ya que el sistema de eventos los invoca de forma asíncrona.

```python
import asyncio
from pathlib import Path
from whatsplay import Client
from whatsplay.auth import LocalProfileAuth

async def main() -> None:
    data_dir = Path.home() / "Documents" / "whatsapp_session"
    data_dir.mkdir(parents=True, exist_ok=True)

    auth = LocalProfileAuth(data_dir)
    client = Client(auth=auth, headless=False)

    @client.event("on_start")
    async def on_start():
        print("✅ Cliente iniciado")

    @client.event("on_auth")
    async def on_auth():
        print("📸 Mostrando QR en pantalla")

    @client.event("on_unread_chat")
    async def on_unread_chat(chat_name, messages):
        # Si no conocés el nombre exacto, podés usar el número de teléfono
        await client.send_message(chat_name, "Hola, este es un mensaje automático!")

    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📚 Ejemplos Adicionales

La carpeta `/examples` incluye varios scripts de ejemplo para diferentes casos de uso:

- **`simple_example.py`**: Ejemplo básico con eventos y auto-respuesta a mensajes no leídos
- **`open_example.py`**: Cómo abrir un chat específico programáticamente
- **`search_example.py`**: Búsqueda de conversaciones con resultados detallados
- **`wsp.py`**: Herramienta CLI para envío rápido de mensajes desde terminal

Consulta la documentación completa en `src/DOCUMENTACION.md` para instrucciones detalladas de cada ejemplo.

---

## 📦 Dependencias

### Principales

* `playwright` – Automatización de navegador
* `opencv-python` – Procesamiento de imágenes (opcional)
* `numpy` – Operaciones numéricas utilizadas por OpenCV

### Desarrollo

* `pytest` – Framework de testing
* `pytest-asyncio` – Soporte para pruebas asíncronas
* `black` – Formateador de código
* `flake8` – Linter
* `mypy` – Verificación de tipos
* `requests` – Uso en entornos de desarrollo y pruebas

---

## 🤝 Contribuciones

1. Hacé un *fork* del repositorio.
2. Creá una rama (`git checkout -b feature/nueva-funcionalidad`).
3. Commit de tus cambios (`git commit -am 'Agrega nueva funcionalidad'`).
4. Push (`git push origin feature/nueva-funcionalidad`).
5. Abrí un *Pull Request*.

---

## 🗺 Roadmap

### Completado ✅
* [✅] Soporte para mensajes multimedia (imágenes, videos, audios)
* [✅] Filtros para mensajes (MessageFilter)
* [✅] Detección robusta de chats no leídos
* [✅] Búsqueda mejorada con múltiples estrategias
* [✅] Selectores actualizados para WhatsApp Web 2024-2025
* [✅] Soporte para listas virtualizadas

### En desarrollo 🚧
* [ ] Mejoras en detección de tipos de mensajes específicos
* [ ] API para envío de archivos multimedia
* [ ] Soporte para mensajes con reacciones

### Planificado 🔮
* [ ] Integración con webhooks
* [ ] Dashboard web de monitoreo
* [ ] Soporte para múltiples cuentas simultáneas

---

## ❓ FAQ

**¿Es seguro usar WhatsPlay?**
Usa la interfaz oficial de WhatsApp Web; es tan seguro como usar WhatsApp en un navegador.

**¿Puede ser detectado por WhatsApp?**
Siempre hay riesgo al automatizar servicios web. Úsalo bajo tu responsabilidad.

**¿Funciona sin GUI?**
Sí, gracias al modo *headless* de Playwright.

---

## 🐞 Reporte de bugs

Abrí un [issue](https://github.com/markbus-ai/whatsplay/issues) con:

* Descripción del problema
* Pasos para reproducirlo
* Versión de Python y dependencias
* Logs relevantes

---

## 📄 Licencia

Licencia **Apache 2.0**.

---

<div align="center">

**[⭐ Dejá una estrella](https://github.com/markbus-ai/whatsplay)** si te resultó útil  
Hecho con ❤️ por Markbusking

</div>
