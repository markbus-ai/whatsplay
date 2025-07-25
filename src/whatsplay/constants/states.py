from enum import Enum, auto


class State(Enum):
    """Estados posibles del cliente de WhatsApp Web"""

    LOGGED_IN = auto()  # Usuario autenticado y listo para usar
    LOADING = auto()  # Cargando interfaz o datos
    QR_AUTH = auto()  # Mostrando código QR para autenticación
    AUTH = auto()  # Pantalla inicial de autenticación
    CONNECTING = auto()  # Conectando con WhatsApp Web
    ERROR = auto()  # Error en la conexión o autenticación

    def __str__(self):
        return self.name.lower()
