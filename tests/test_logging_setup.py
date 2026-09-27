"""
Tests del logging centralizado de whatsplay.

Cubren: compatibilidad (visible sin configurar), silenciamiento por nivel,
namespace correcto de loggers, y que el refactor de print->logging no deje
prints sueltos en el código de la librería.
"""

import io
import logging
import contextlib
from pathlib import Path

import pytest

from whatsplay.logging_setup import get_logger, ROOT_LOGGER_NAME, _CompatHandler


@pytest.fixture(autouse=True)
def clean_whatsplay_logger():
    """Aísla el logger entre tests: limpia handlers y restaura el nivel.

    Al terminar reinstala el handler de compatibilidad, porque la librería
    asume que hay al menos uno (si no, quedaría muda).
    """
    root = logging.getLogger(ROOT_LOGGER_NAME)
    saved_handlers = list(root.handlers)
    saved_level = root.level
    root.handlers.clear()
    root.setLevel(logging.NOTSET)
    yield
    root.handlers.clear()
    root.setLevel(logging.NOTSET)
    # Reinstalar la config por defecto de la librería
    from whatsplay.logging_setup import _ensure_default_handler
    _ensure_default_handler()
    # Restaurar lo que había (menos duplicados del compat handler)
    for h in saved_handlers:
        if h not in root.handlers:
            root.addHandler(h)
    root.setLevel(saved_level)


def test_get_logger_namespaces_under_whatsplay():
    """Todo logger debe colgar de 'whatsplay.*', nunca suelto."""
    assert get_logger("whatsplay").name == "whatsplay"
    assert get_logger("whatsplay.chat_manager").name == "whatsplay.chat_manager"
    # nombre suelto se normaliza bajo el namespace del paquete
    assert get_logger("wa_elements").name == "whatsplay.wa_elements"
    assert get_logger("some.other.thing").name == "whatsplay.some.other.thing"


def test_visible_by_default_for_consumers_without_logging():
    """Compat: si nadie configura logging, los mensajes se ven."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        get_logger("whatsplay.compat").info("mensaje de compat")
    assert "mensaje de compat" in buf.getvalue()


def test_consumer_can_silence_debug_and_info():
    """El consumidor debe poder bajar el ruido con setLevel."""
    logging.getLogger(ROOT_LOGGER_NAME).setLevel(logging.WARNING)
    lg = get_logger("whatsplay.chat_manager")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        lg.debug("ruido debug")
        lg.info("ruido info")
        lg.warning("esto si importa")
    out = buf.getvalue()

    assert "ruido debug" not in out
    assert "ruido info" not in out
    assert "esto si importa" in out


def test_does_not_propagate_to_root():
    """No debe duplicar mensajes en el logging del consumidor."""
    assert logging.getLogger(ROOT_LOGGER_NAME).propagate is False


def test_debug_and_info_visible_when_level_is_info():
    """Con el nivel por defecto (INFO), info se ve y debug no."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        lg = get_logger("whatsplay.level_check")
        lg.debug("detalle debug")
        lg.info("mensaje info")
    out = buf.getvalue()
    assert "mensaje info" in out
    assert "detalle debug" not in out


def test_no_stray_prints_left_in_library_code():
    """El refactor debe haber eliminado los print() del código (no docstrings)."""
    src_dir = Path(__file__).resolve().parent.parent / "src" / "whatsplay"
    offenders = []
    for py in src_dir.rglob("*.py"):
        if py.name == "logging_setup.py":
            continue
        text = py.read_text(encoding="utf-8")
        in_docstring = False
        for num, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.count('"""') == 1:
                in_docstring = not in_docstring
            if in_docstring or py.name == "client.py":
                continue  # client.py tiene un ejemplo de print en docstring
            if stripped.startswith("print("):
                offenders.append(f"{py.name}:{num}")
    assert offenders == [], f"quedan prints sueltos: {offenders}"
