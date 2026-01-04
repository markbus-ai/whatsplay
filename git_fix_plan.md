Okay, basándome en el historial de `git`, parece que el commit `70538bd` está en la rama `LK2B2UwdjzzhwYvP`, pero probablemente debería estar en una nueva rama de funcionalidad (feature branch) basada en `main`.

Aquí está mi plan para arreglarlo de forma segura:

1.  **Desharé el último commit** en tu rama actual (`LK2B2UwdjzzhwYvP`), pero mantendré todos los cambios intactos y listos para ser movidos.
2.  **Crearé una nueva rama** llamada `feature/messaging-updates` a partir de la rama `main`.
3.  **Moveré tus cambios** a esta nueva rama.
4.  **Crearé un nuevo commit** con tus cambios en la nueva rama `feature/messaging-updates`.

El resultado será:
*   Tus cambios estarán seguros en la nueva rama `feature/messaging-updates`.
*   Tu rama `LK2B2UwdjzzhwYvP` quedará limpia, tal como estaba antes de que hicieras el commit por error.

¿Te parece bien este plan? No haré ningún cambio hasta que me des tu confirmación.