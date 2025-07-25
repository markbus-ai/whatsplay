"""
Event types for the WhatsApp Web client
"""

EVENT_LIST = [
    "on_start",  # Cliente iniciado
    "on_stop",  # Cliente detenido
    "on_auth",  # Pantalla de autenticación mostrada
    "on_qr",  # Código QR detectado
    "on_qr_change",  # Código QR actualizado
    "on_loading",  # Cargando datos/interfaz
    "on_logged_in",  # Login exitoso
    "on_unread_chat",  # Chat no leído detectado
    "on_message",  # Nuevo mensaje recibido
    "on_state_change",  # Cambio de estado del cliente
    "on_error",  # Error detectado
    "on_disconnect",  # Desconexión detectada
    "on_reconnect",  # Reconexión exitosa
    "on_tick",  # Tick del loop principal
]
