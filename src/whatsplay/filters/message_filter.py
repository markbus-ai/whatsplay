"""
Message filtering utilities for WhatsApp messages
"""

from typing import Tuple


class MessageFilter:
    """Helper class for filtering WhatsApp messages"""

    @classmethod
    def filter_search_result(cls, text: str) -> list[str]:
        """Filtra y formatea un resultado de búsqueda

        Returns:
            List[str]: (texto_formateado)
        """
        text = text.strip()

        # Formatear el resultado
        lines = text.split("\n")
        if len(lines) >= 2:
            name = lines[0].strip()
            date = lines[1].strip()
            message = " ".join(lines[2:]).strip() if len(lines) > 2 else ""

            # No mostrar si el mensaje está vacío o muy corto
            if not message or len(message) < 2:
                return text

            # No mostrar si el mensaje solo contiene números o caracteres especiales
            if all(c.isdigit() or c in ".,-_+=/\\" for c in message.replace(" ", "")):
                return text

            text_formatted = {"name": name, "date": date, "message": message}
            return text_formatted

        return text
