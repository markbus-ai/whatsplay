# Contribuir a WhatsPlay

¡Gracias por tu interés en contribuir a WhatsPlay! Agradecemos las contribuciones de la comunidad para ayudar a mejorar esta biblioteca.

## Cómo contribuir

1.  **Haz un fork del repositorio:** crea un fork del [repositorio de WhatsPlay](https://github.com/markbus-ai/whatsplay) en GitHub.
2.  **Clona el fork:** clona tu repositorio en tu máquina local.
3.  **Crea una rama:** crea una nueva rama para tu funcionalidad o corrección.
    ```bash
    git checkout -b feature/my-new-feature
    ```
4.  **Haz tus cambios:** implementa tus cambios. Asegúrate de que tu código siga el estilo y las convenciones existentes.
5.  **Prueba tus cambios:** ejecuta las pruebas existentes y añade nuevas si corresponde.
6.  **Haz commit y push:** confirma tus cambios (usando [Conventional Commits](https://www.conventionalcommits.org/), por ejemplo `fix: ...`, `feat: ...`) y súbelos a tu fork.
    ```bash
    git commit -m "feat: add a new feature"
    git push origin feature/my-new-feature
    ```
7.  **Crea un Pull Request:** abre un Pull Request (PR) en el repositorio principal. Describe tus cambios con claridad.

## Configuración de desarrollo

Para configurar tu entorno de desarrollo:

1.  **Instala el paquete en modo editable, junto con las herramientas de pruebas y documentación:**
    ```bash
    pip install -e . pytest pytest-asyncio
    pip install -r requirements-docs.txt
    ```
2.  **Instala el navegador de Playwright:**
    ```bash
    python -m playwright install chromium
    ```
3.  **Ejecuta las pruebas:**
    ```bash
    pytest tests/ -v
    ```
4.  **Previsualiza la documentación localmente:**
    ```bash
    mkdocs serve
    ```
    El sitio se publica automáticamente en GitHub Pages con cada push a `main`.

## Reportar errores

Si encuentras un error, abre un issue en GitHub. Incluye:
*   Una descripción clara del error.
*   Pasos para reproducirlo.
*   Comportamiento esperado frente al real.
*   Tu sistema operativo y versión de Python.
*   Logs o capturas de pantalla si es posible.

## Licencia

Al contribuir, aceptas que tus contribuciones se licencien bajo la Apache License 2.0.
