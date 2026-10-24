# Solución de problemas

Esta guía aborda los problemas comunes que podrías encontrar al usar WhatsPlay y cómo resolverlos.

## Problemas de instalación

### `playwright: command not found`
Si obtienes este error después de instalar WhatsPlay, probablemente necesites instalar manualmente los binarios del navegador de Playwright.

**Solución:**
```bash
python -m playwright install chromium
```

### `Error: EACCES: permission denied` (Linux/Mac)
Si encuentras errores de permisos al ejecutar el script o instalar dependencias.

**Solución:**
Asegúrate de tener acceso de lectura y escritura a tu directorio actual y al `data_dir` que pasaste a `LocalProfileAuth`. Evita ejecutar scripts con `sudo` a menos que sea necesario, ya que puede alterar la propiedad de los archivos.

---

## Problemas de conexión e inicio de sesión

### El código QR no aparece
Si el navegador se abre pero el código QR nunca carga, o si solo ves un indicador de carga.

**Causas:**
1.  **Internet lento:** WhatsApp Web carga muchos recursos.
2.  **Modo headless:** en algunos entornos, el modo headless puede comportarse de forma diferente.

**Solución:**
Intenta ejecutar primero con `headless=False` para inspeccionar visualmente qué está pasando.
```python
client = Client(auth=auth, headless=False)
```

### La sesión no se guarda
Escaneas el código QR, pero la próxima vez que ejecutas el script te pide escanear de nuevo.

**Solución:**
Asegúrate de usar `LocalProfileAuth` y de proporcionar una ruta válida.
```python
auth = LocalProfileAuth(data_dir="./whatsapp_session")
```
Asegúrate también de que el script se detenga correctamente (con `await client.stop()`) para que el contexto del navegador pueda guardar bien los datos del perfil.

---

## Errores en tiempo de ejecución

### `ElementHandle.click: Timeout 30000ms exceeded`
Este es el error más común en la automatización web. Significa que WhatsPlay intentó encontrar un elemento (como un chat o un botón) pero no lo encontró dentro del límite de tiempo.

**Causas:**
1.  **WhatsApp Web se actualizó:** WhatsApp actualiza con frecuencia su DOM (estructura HTML), lo que rompe selectores.
2.  **Chat no visible:** intentaste abrir un chat que no está en la lista cargada.
3.  **Diferencia de idioma:** algunos selectores dependen del texto (por ejemplo, "Type a message").

**Solución:**
1.  **Busca actualizaciones:** ejecuta `pip install --upgrade whatsplay` para obtener los selectores más recientes.
2.  **Usa la búsqueda:** en lugar de depender de que un chat esté visible, usa `client.search_conversations()` o `client.open(..., open_via_url=True)` para números de teléfono.
3.  **Aumenta el timeout:** algunos métodos aceptan un parámetro `timeout`.

### `send_message()` / `send_file()` devuelve `False`
WhatsPlay solo informa éxito cuando WhatsApp muestra el nuevo mensaje con un estado de entrega. Devuelve `False` (y registra el motivo) cuando:

1.  **No se pudo abrir el chat:** el nombre no coincide exactamente, o más de un chat tiene ese título. Usa el título exacto, pasa `is_group=True/False` o usa un número de teléfono completo con `open_via_url=True`.
2.  **El cuadro de redacción pertenece a otro chat:** WhatsPlay se niega a escribir en un chat que no pediste.
3.  **El idioma de la interfaz no es español ni inglés:** no se puede verificar la etiqueta del cuadro de redacción, así que se rechaza el envío.
4.  **No apareció ningún estado de entrega:** el mensaje puede seguir pendiente (por ejemplo, sin conexión en el teléfono). Revisa WhatsApp antes de reintentar para evitar duplicados.

### `open()` devuelve `False`
`open()` se niega en lugar de adivinar. Revisa los logs (`whatsplay.wa_elements`) en busca de errores "ambiguous", y recuerda que los números de teléfono deben coincidir con el número internacional completo.

### La memoria no deja de crecer en bots de larga duración
El renderizador de WhatsApp Web acumula memoria con el tiempo. Usa `collect_messages(dispose=True)` cuando solo necesites los datos de los mensajes, y llama a `await client.refresh()` periódicamente (por ejemplo, cada pocas horas). Consulta [Funciones avanzadas](guides/advanced-features.md#bots-persistentes-y-memoria).

### `Target closed` o `Browser closed`
La ventana del navegador se cerró inesperadamente.

**Causas:**
1.  **Intervención manual:** cerraste la ventana del navegador manualmente mientras el script se ejecutaba.
2.  **Fallo:** Chromium se cerró por falta de memoria.

---

## Problemas del modo headless en servidor/Docker

Ejecutar WhatsPlay en un servidor (CI/CD, VPS) sin pantalla requiere atención especial.

**Solución:**
1.  **Instala las dependencias:** asegúrate de que todas las dependencias del sistema para Playwright estén instaladas.
    ```bash
    playwright install-deps
    ```
2.  **User Agent:** a veces WhatsApp Web bloquea los navegadores headless. WhatsPlay intenta manejarlo, pero podrías necesitar probar otras configuraciones o ejecutar en modo con interfaz ("headed") usando `xvfb`.

## ¿Sigues teniendo problemas?

Si probaste estas soluciones y sigues teniendo problemas:

1.  **Activa el logging de depuración:** `logging.getLogger("whatsplay").setLevel(logging.DEBUG)` muestra la detección de estado y las decisiones sobre el DOM. Maneja también `on_error` y `on_warning`. Consulta [Configuración › Registros](configuration.md#registros).
2.  **Reporta un error:** abre un issue en nuestro repositorio de GitHub con el log del error y, si es posible, una captura de pantalla.
