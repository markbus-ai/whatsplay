# Solución de Problemas (Troubleshooting)

Esta guía aborda los problemas comunes que podrías encontrar al usar WhatsPlay y cómo resolverlos.

## Problemas de Instalación

### `playwright: command not found`
Si obtienes este error después de instalar WhatsPlay, probablemente necesites instalar los binarios del navegador de Playwright manualmente.

**Solución:**
```bash
pip install playwright
playwright install
```

### `Error: EACCES: permission denied` (Linux/Mac)
Si encuentras errores de permisos al ejecutar el script o instalar dependencias.

**Solución:**
Asegúrate de tener acceso de lectura/escritura a tu directorio actual y al `user_data_dir` que especificaste. Evita ejecutar scripts con `sudo` a menos que sea necesario, ya que puede alterar la propiedad de los archivos.

---

## Problemas de Conexión e Inicio de Sesión

### El Código QR No Aparece
Si el navegador se abre pero el código QR nunca carga, o si solo ves un spinner de carga.

**Causas:**
1.  **Internet Lento:** WhatsApp Web carga muchos recursos.
2.  **Modo Headless:** En algunos entornos, el modo headless (sin cabeza) puede comportarse de manera diferente.

**Solución:**
Intenta ejecutar con `headless=False` primero para inspeccionar visualmente qué está pasando.
```python
client = Client(auth=auth, headless=False)
```

### La Sesión No se Guarda
Escaneas el código QR, pero la próxima vez que ejecutas el script, te pide escanear de nuevo.

**Solución:**
Asegúrate de estar usando `LocalProfileAuth` y proporcionando una ruta válida.
```python
auth = LocalProfileAuth(user_data_dir="./whatsapp_session")
```
También, asegúrate de que el script se detenga correctamente (usando `await client.stop()`) para que el contexto del navegador pueda guardar los datos del perfil correctamente.

---

## Errores en Tiempo de Ejecución

### `ElementHandle.click: Timeout 30000ms exceeded`
Este es el error más común en la automatización web. Significa que WhatsPlay intentó encontrar un elemento (como un chat o un botón) pero no pudo encontrarlo dentro del límite de tiempo.

**Causas:**
1.  **WhatsApp Web se Actualizó:** WhatsApp actualiza frecuentemente su DOM (estructura HTML), rompiendo selectores.
2.  **Chat No Visible:** Intentaste abrir un chat que no está en la lista cargada.
3.  **Diferencia de Idioma:** Algunos selectores dependen del texto (ej., "Escribe un mensaje").

**Solución:**
1.  **Busca Actualizaciones:** Ejecuta `pip install --upgrade whatsplay` para obtener los selectores más recientes.
2.  **Usa Búsqueda:** En lugar de confiar en que un chat sea visible, usa `client.search_conversations()` o `client.open(..., open_via_url=True)` para números de teléfono.
3.  **Aumenta el Timeout:** Algunos métodos aceptan un parámetro `timeout`.

### `Target closed` o `Browser closed`
La ventana del navegador se cerró inesperadamente.

**Causas:**
1.  **Intervención Manual:** Cerraste la ventana del navegador manualmente mientras el script corría.
2.  **Crash:** Chromium se cerró debido a falta de memoria.

---

## Problemas en Modo Headless en Servidor/Docker

Ejecutar WhatsPlay en un servidor (CI/CD, VPS) sin pantalla requiere atención especial.

**Solución:**
1.  **Instala Dependencias:** Asegúrate de que todas las dependencias del sistema para Playwright estén instaladas.
    ```bash
    playwright install-deps
    ```
2.  **User Agent:** A veces WhatsApp Web bloquea navegadores headless. WhatsPlay intenta manejar esto, pero podrías necesitar probar diferentes configuraciones o ejecutar en modo "headed" usando `xvfb`.

## ¿Sigues Teniendo Problemas?

Si has probado estas soluciones y sigues enfrentando problemas:

1.  **Habilita Depuración:** Añade prints a tus eventos (`on_error`, `on_warning`) para obtener más detalles.
2.  **Reporta un Bug:** Abre un issue en nuestro repositorio de GitHub con el log de error y una captura de pantalla si es posible.
