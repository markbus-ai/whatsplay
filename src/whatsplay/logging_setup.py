"""
Logging centralizado de whatsplay.

Antes la librería escribía con ``print()``: 43 llamadas que iban directo a
stdout, sin nivel, sin timestamp y sin forma de silenciarlas. En el bot eso
generaba ~217.000 líneas por día de ruido del poller, tapando la señal real.

Ahora todo pasa por ``logging`` con un logger propio (``whatsplay.*``), así el
consumidor decide qué ver::

    import logging
    logging.getLogger("whatsplay").setLevel(logging.WARNING)   # silencio el estado
    logging.getLogger("whatsplay.wa_elements").setLevel(logging.DEBUG)  # detalle del DOM

Compatibilidad: si el consumidor NO configura logging, se mantiene el
comportamiento visible previo mediante un handler por defecto a stdout. Es
decir, nadie pierde los mensajes por actualizar.
"""

from __future__ import annotations

import logging
import sys

# Logger raíz del paquete. Los submódulos usan `get_logger(__name__)`, que
# cuelga de este, y así un solo setLevel("whatsplay") controla todo.
ROOT_LOGGER_NAME = "whatsplay"

_logger = logging.getLogger(ROOT_LOGGER_NAME)
# No propagar al root: si el consumidor configura su logging, no queremos que
# nuestros mensajes se dupliquen ni que hereden handlers inesperados.
_logger.propagate = False


class _CompatHandler(logging.Handler):
    """Handler de compatibilidad: imprime si el nivel lo permite.

    Mantiene el comportamiento visible previo para quien no usa logging. A
    diferencia de una heurística por cantidad de handlers (frágil: pytest y
    cualquier consumidor agregan los suyos), la visibilidad la decide el
    NIVEL del logger: si el consumidor lo sube a WARNING, debug/info se
    silencian; si lo deja en INFO, se ven.
    """

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - IO
        try:
            print(f"{record.levelname}: {record.getMessage()}")
        except Exception:
            self.handleError(record)


def _ensure_default_handler() -> None:
    """Instala el handler de compatibilidad si no hay ninguno configurado."""
    if not any(isinstance(h, _CompatHandler) for h in _logger.handlers):
        handler = _CompatHandler()
        handler.setLevel(logging.INFO)
        _logger.addHandler(handler)
    if _logger.level == logging.NOTSET:
        _logger.setLevel(logging.INFO)


def ensure_configured() -> None:
    """Garantiza que el logger del paquete tenga al menos un handler.

    Se llama antes de emitir para cubrir el caso de que alguien limpie los
    handlers (tests, reconfiguración): sin esto la librería quedaría muda.
    """
    _ensure_default_handler()


def get_logger(name: str) -> logging.Logger:
    """Logger de submódulo, colgado de ``whatsplay``.

    Args:
        name: normalmente ``__name__`` del módulo que loguea.

    Returns:
        Un logger bajo el namespace ``whatsplay``.
    """
    _ensure_default_handler()
    if name == ROOT_LOGGER_NAME or name.startswith(ROOT_LOGGER_NAME + "."):
        return logging.getLogger(name)
    # Normalizar: 'whatsplay.wa_elements', nunca logger suelto de otro namespace.
    suffix = name.split("whatsplay.", 1)[-1] if "whatsplay." in name else name
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{suffix}")
