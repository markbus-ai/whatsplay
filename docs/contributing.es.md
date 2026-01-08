# Contribuyendo a WhatsPlay

¡Gracias por tu interés en contribuir a WhatsPlay! Agradecemos las contribuciones de la comunidad para ayudar a mejorar esta biblioteca.

## Cómo Contribuir

1.  **Hacer un Fork del Repositorio:** Crea un fork del [repositorio de WhatsPlay](https://github.com/markbus-ai/whatsplay) en GitHub.
2.  **Clonar el Fork:** Clona tu repositorio bifurcado a tu máquina local.
3.  **Crear una Rama:** Crea una nueva rama para tu funcionalidad o corrección de errores.
    ```bash
    git checkout -b feature/mi-nueva-funcionalidad
    ```
4.  **Hacer Cambios:** Implementa tus cambios. Por favor, asegúrate de que tu código sigue el estilo y las convenciones existentes.
5.  **Probar Tus Cambios:** Ejecuta las pruebas existentes y añade nuevas si aplica.
6.  **Confirmar y Subir:** Confirma (commit) tus cambios y súbelos (push) a tu fork.
    ```bash
    git commit -m "Añadir una nueva funcionalidad"
    git push origin feature/mi-nueva-funcionalidad
    ```
7.  **Crear un Pull Request:** Abre un Pull Request (PR) en el repositorio principal. Describe tus cambios claramente.

## Configuración de Desarrollo

Para configurar tu entorno de desarrollo:

1.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-docs.txt
    ```
2.  **Instalar Navegadores de Playwright:**
    ```bash
    playwright install
    ```

## Reportando Errores (Bugs)

Si encuentras un error, por favor abre un issue en GitHub. Incluye:
*   Una descripción clara del error.
*   Pasos para reproducirlo.
*   Comportamiento esperado vs. real.
*   Tu sistema operativo y versión de Python.
*   Logs o capturas de pantalla si es posible.

## Licencia

Al contribuir, aceptas que tus contribuciones serán licenciadas bajo la Licencia MIT.
