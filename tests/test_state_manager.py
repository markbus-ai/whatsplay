import pytest
from unittest.mock import AsyncMock, MagicMock
from src.whatsplay.state_manager import StateManager

# Mock de un cliente mínimo para StateManager
class MockClient:
    def __init__(self):
        self._page = AsyncMock()
        self.wa_elements = MagicMock()
        self.chat_manager = AsyncMock()
        self.emit = AsyncMock() # Make emit an AsyncMock

@pytest.fixture
def mock_state_manager():
    client = MockClient()
    manager = StateManager(client)
    return manager

@pytest.mark.asyncio
async def test_extract_image_from_canvas_success(mock_state_manager):
    mock_canvas_element = AsyncMock()
    mock_canvas_element.screenshot.return_value = b"dummy_qr_image_bytes"

    result = await mock_state_manager._extract_image_from_canvas(mock_canvas_element)

    assert result == b"dummy_qr_image_bytes"
    mock_canvas_element.screenshot.assert_called_once()

@pytest.mark.asyncio
async def test_extract_image_from_canvas_no_element(mock_state_manager):
    result = await mock_state_manager._extract_image_from_canvas(None)

    assert result is None

@pytest.mark.asyncio
async def test_extract_image_from_canvas_error(mock_state_manager):
    mock_canvas_element = AsyncMock()
    mock_canvas_element.screenshot.side_effect = Exception("Screenshot error")

    result = await mock_state_manager._extract_image_from_canvas(mock_canvas_element)

    assert result is None
    mock_state_manager.client.emit.assert_called_with(
        "on_error", "Error extracting QR image: Screenshot error"
    )

@pytest.mark.asyncio
async def test_handle_logged_in_state_with_continue_button(mock_state_manager):
    # Simular que el botón 'Continue' está presente
    mock_continue_button = AsyncMock()
    mock_state_manager._page.query_selector.return_value = mock_continue_button

    await mock_state_manager._handle_logged_in_state()

    # Verificar que el botón 'Continue' fue clicado
    mock_continue_button.click.assert_called_once()
    # Verificar que no se llamó a _check_unread_chats ni se emitió on_unread_chat
    mock_state_manager.client.chat_manager._check_unread_chats.assert_not_called()
    mock_state_manager.client.emit.assert_not_called()

@pytest.mark.asyncio
async def test_handle_logged_in_state_with_unread_chats(mock_state_manager):
    # Simular que el botón 'Continue' no está presente
    mock_state_manager._page.query_selector.return_value = None

    # Simular que hay chats no leídos
    mock_unread_chats = [{"name": "Chat1"}, {"name": "Chat2"}]
    mock_state_manager.client.chat_manager._check_unread_chats.return_value = mock_unread_chats

    await mock_state_manager._handle_logged_in_state()

    # Verificar que se llamó a _check_unread_chats
    mock_state_manager.client.chat_manager._check_unread_chats.assert_called_once()
    # Verificar que se emitió 'on_unread_chat' con los chats correctos
    mock_state_manager.client.emit.assert_called_with("on_unread_chat", mock_unread_chats)

@pytest.mark.asyncio
async def test_handle_logged_in_state_no_unread_chats(mock_state_manager):
    # Simular que el botón 'Continue' no está presente
    mock_state_manager._page.query_selector.return_value = None

    # Simular que no hay chats no leídos
    mock_state_manager.client.chat_manager._check_unread_chats.return_value = []

    await mock_state_manager._handle_logged_in_state()

    # Verificar que se llamó a _check_unread_chats
    mock_state_manager.client.chat_manager._check_unread_chats.assert_called_once()
    # Verificar que no se emitió 'on_unread_chat'
    mock_state_manager.client.emit.assert_not_called()

@pytest.mark.asyncio
async def test_handle_logged_in_state_exception(mock_state_manager):
    # Simular una excepción al verificar chats no leídos
    mock_state_manager._page.query_selector.return_value = None # No continue button
    mock_state_manager.client.chat_manager._check_unread_chats.side_effect = Exception("Test error")

    await mock_state_manager._handle_logged_in_state()

    # Verificar que se emitió 'on_error'
    mock_state_manager.client.emit.assert_called_with(
        "on_error", "Error en estado de sesión iniciada: Test error"
    )