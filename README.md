# WhatsPlay 🚀

Automatización avanzada de WhatsApp Web usando Playwright, Python y visión por computadora (OpenCV).  
Permite interactuar con mensajes no leídos, autenticar mediante código QR, y realizar acciones complejas a través de eventos personalizados y filtrado de mensajes.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-latest-green.svg)](https://playwright.dev/)

## 🧠 Descripción

WhatsPlay es una librería modular diseñada para automatizar WhatsApp Web desde Python. La arquitectura está inspirada en el patrón de eventos y la separación de responsabilidades, con módulos independientes para autenticación, interacción con la UI, lógica base, y procesamiento de imágenes.

### ✨ Características principales

- **Automatización de navegador** con Playwright para máxima compatibilidad
- **extraccion automática de QR** sin intervención manual
- **Sistema de eventos personalizado** para manejo asíncrono de mensajes
- **Detección inteligente** de mensajes no leídos
- **Arquitectura modular** con separación clara de responsabilidades
- **Procesamiento de imágenes** con OpenCV para reconocimiento avanzado

## 🖼️ Arquitectura del sistema

![Arquitectura](Editor%20_%20Mermaid%20Chart-2025-06-03-140923.png)

La arquitectura modular permite:
- **Escalabilidad**: Fácil adición de nuevas funcionalidades
- **Mantenibilidad**: Componentes independientes y bien definidos  
- **Testabilidad**: Cada módulo puede probarse por separado
- **Reutilización**: Los módulos pueden usarse en otros proyectos

## 🚀 Instalación

### Prerrequisitos

- Python 3.8 o superior
- Node.js (para Playwright)

### Instalación desde PyPI 

```bash
pip install whatsplay
```

## 🧪 Ejemplos de uso

### Uso básico

```python
from whatsplay import WhatsAppClient

# Crear cliente
client = WhatsAppClient()

# Handler para mensajes no leídos
@client.on_unread_chat
def handle_unread(chats):
    print("chat name: ", chats[0]['name'])
    success = await client.send_message(chats[0]['name'], "Hello!")
    if success:
        print("✅ Mensaje enviado con éxito")
    else:
        print("❌ Falló el envío del mensaje")

# Iniciar cliente
client.run()
```

## 📁 Estructura del proyecto

```
whatsplay/
├───examples
│       simple_example.py
│       test_client.py
│       test_main_loop.py
│       
└───src
    └───whatsplay
        │   base_client.py
        │   client.py
        │   event.py
        │   utils.py
        │   wa_elements.py
        │   __init__.py
        │
        ├───auth
        │       auth.py
        │       local_profile_auth.py
        │       no_auth.py
        │       __init__.py
        │
        ├───constants
        │       locator.py
        │       states.py
        │
        ├───events
        │       event_handler.py
        │       event_types.py
        │       __init__.py
        │
        └───filters
                message_filter.py
                __init__.py
```

## 📦 Dependencias

### Principales
- `playwright` - Automatización de navegador
- `opencv-python` - Procesamiento de imágenes (opcional)
- `pillow` - Manipulación de imágenes
- `requests` - Cliente HTTP

### Desarrollo
- `pytest` - Framework de testing
- `black` - Formateador de código
- `flake8` - Linter
- `mypy` - Verificación de tipos


## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

### Guías de desarrollo

- Sigue PEP 8 para el estilo de código
- Agrega tests para nuevas funcionalidades
- Actualiza la documentación cuando sea necesario
- Usa type hints en todas las funciones públicas

## 📋 Roadmap

- [ ] Soporte para mensajes multimedia (imágenes, videos, audios)
- [ ] MessageFilter

## ❓ FAQ

**¿Es seguro usar WhatsPlay?**
WhatsPlay utiliza WhatsApp Web oficial, por lo que es tan seguro como usar WhatsApp en tu navegador.

**¿Puede ser detectado por WhatsApp?**
WhatsPlay simula interacciones humanas normales, pero siempre existe un riesgo al automatizar servicios web.

**¿Funciona en servidores sin GUI?**
Sí, usando el modo headless de Playwright.

## 🐛 Reporte de bugs

Si encuentras un bug, por favor [abre un issue](https://github.com/markbus-ai/whatsplay/issues) incluyendo:

- Descripción del problema
- Pasos para reproducirlo
- Versión de Python y dependencias
- Logs relevantes

## 🤝 Agradecimientos

Este proyecto está inspirado y utiliza partes del código de [RedShot](https://github.com/akrentz6/RedShot), licenciado bajo la licencia Apache 2.0. Agradecemos especialmente a la comunidad de RedShot por su trabajo pionero en automatización de WhatsApp.

## 📄 Licencia

Este proyecto está licenciado bajo la **Licencia Apache 2.0**.

```
Copyright 2025 WhatsPlay

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

Consultá el archivo [LICENSE](./LICENSE) para más información.

---

<div align="center">

**[⭐ Star este proyecto](https://github.com/markbus-ai/whatsplay)** si te resulta útil

Made with ❤️ by [Markbusking]

</div>


