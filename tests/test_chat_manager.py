import pytest
from unittest.mock import AsyncMock, MagicMock
from src.whatsplay.chat_manager import ChatManager

# Mock de loc (locator) para evitar dependencias reales
class MockLocator:
    SEARCH_ITEM_UNREAD_MESSAGES = ".//span[contains(@aria-label, 'unread message')]"
    SPAN_TITLE = ".//span[@title]"

# Mock de un cliente mínimo para ChatManager
class MockClient:
    def __init__(self):
        self._page = AsyncMock()
        self.wa_elements = MagicMock()
        self.unread_messages_sleep = 1

    async def emit(self, event, *args, **kwargs):
        pass

    async def wait_until_logged_in(self):
        return True

@pytest.fixture
def mock_chat_manager():
    client = MockClient()
    manager = ChatManager(client)
    manager.loc = MockLocator() # Inyectar el mock de loc
    return manager

@pytest.mark.asyncio
async def test_parse_search_result_individual_chat(mock_chat_manager):
    # Simular un elemento de chat individual (2 componentes)
    mock_element = AsyncMock()
    
    # Mock de components[0] (título y datetime)
    mock_component0 = AsyncMock()
    mock_span_title0 = AsyncMock()
    mock_span_title0.get_attribute.return_value = "Contacto Individual"
    mock_component0.query_selector.return_value = mock_span_title0
    
    mock_datetime_child = AsyncMock()
    mock_datetime_child.text_content.return_value = "10:30 AM"
    mock_component0.query_selector_all.return_value = [MagicMock(), mock_datetime_child]

    # Mock de components[1] (info_text)
    mock_component1 = AsyncMock()
    mock_info_child = AsyncMock()
    mock_info_child.text_content.return_value = "Hola, ¿cómo estás?"
    mock_component1.query_selector_all.return_value = [mock_info_child]

    mock_element.query_selector_all.return_value = [mock_component0, mock_component1]

    # Mock de unread_el
    mock_unread_el = AsyncMock()
    mock_unread_el.inner_text.return_value = "5"
    mock_element.query_selector.return_value = mock_unread_el

    result = await mock_chat_manager._parse_search_result(mock_element)

    assert result is not None
    assert result["type"] == "CHATS"
    assert result["name"] == "Contacto Individual"
    assert result["last_activity"] == "10:30 AM"
    assert result["last_message"] == "Hola, ¿cómo estás?"
    assert result["unread_count"] == "5"
    assert result["group"] is None

@pytest.mark.asyncio
async def test_parse_search_result_group_chat(mock_chat_manager):
    # Simular un elemento de chat de grupo (3 componentes)
    mock_element = AsyncMock()

    # Mock de components[0] (group_title y datetime)
    mock_component0 = AsyncMock()
    mock_span_title0 = AsyncMock()
    mock_span_title0.get_attribute.return_value = "Nombre del Grupo"
    mock_component0.query_selector.return_value = mock_span_title0

    mock_datetime_child = AsyncMock()
    mock_datetime_child.text_content.return_value = "Ayer"
    mock_component0.query_selector_all.return_value = [MagicMock(), mock_datetime_child]

    # Mock de components[1] (title - que es el mismo que el grupo en este caso)
    mock_component1 = AsyncMock()
    mock_span_title1 = AsyncMock()
    mock_span_title1.get_attribute.return_value = "Nombre del Grupo"
    mock_component1.query_selector.return_value = mock_span_title1

    # Mock de components[2] (info_text con remitente)
    mock_component2 = AsyncMock()
    mock_component2.text_content.return_value = "Juan Pérez: Mensaje del grupo"

    mock_element.query_selector_all.return_value = [mock_component0, mock_component1, mock_component2]

    # Mock de unread_el
    mock_unread_el = AsyncMock()
    mock_unread_el.inner_text.return_value = "12"
    mock_element.query_selector.return_value = mock_unread_el

    result = await mock_chat_manager._parse_search_result(mock_element)

    assert result is not None
    assert result["type"] == "CHATS"
    assert result["group"] == "Nombre del Grupo"
    assert result["name"] == "Nombre del Grupo"
    assert result["last_activity"] == "Ayer"
    assert result["last_message"] == "Juan Pérez: Mensaje del grupo"
    assert result["unread_count"] == "12"

@pytest.mark.asyncio
async def test_parse_search_result_group_chat_with_different_sender(mock_chat_manager):
    # Simular un elemento de chat de grupo (3 componentes) donde el remitente es diferente al título del grupo
    mock_element = AsyncMock()

    # Mock de components[0] (group_title y datetime)
    mock_component0 = AsyncMock()
    mock_span_title0 = AsyncMock()
    mock_span_title0.get_attribute.return_value = "Mi Grupo de Amigos"
    mock_component0.query_selector.return_value = mock_span_title0

    mock_datetime_child = AsyncMock()
    mock_datetime_child.text_content.return_value = "Hoy"
    mock_component0.query_selector_all.return_value = [MagicMock(), mock_datetime_child]

    # Mock de components[1] (title - que es el mismo que el grupo en este caso)
    mock_component1 = AsyncMock()
    mock_span_title1 = AsyncMock()
    mock_span_title1.get_attribute.return_value = "Mi Grupo de Amigos"
    mock_component1.query_selector.return_value = mock_span_title1

    # Mock de components[2] (info_text con remitente diferente al título del grupo)
    mock_component2 = AsyncMock()
    mock_component2.text_content.return_value = "Ana: Hola a todos!"

    mock_element.query_selector_all.return_value = [mock_component0, mock_component1, mock_component2]

    # Mock de unread_el
    mock_unread_el = AsyncMock()
    mock_unread_el.inner_text.return_value = "3"
    mock_element.query_selector.return_value = mock_unread_el

    result = await mock_chat_manager._parse_search_result(mock_element)

    assert result is not None
    assert result["type"] == "CHATS"
    assert result["group"] == "Mi Grupo de Amigos" # Sigue siendo un grupo
    assert result["name"] == "Mi Grupo de Amigos"
    assert result["last_activity"] == "Hoy"
    assert result["last_message"] == "Ana: Hola a todos!"
    assert result["unread_count"] == "3"

@pytest.mark.asyncio
async def test_parse_search_result_individual_chat_with_colon_in_message(mock_chat_manager):
    # Simular un chat individual donde el mensaje contiene dos puntos, pero no es un grupo
    mock_element = AsyncMock()
    
    # Mock de components[0] (título y datetime)
    mock_component0 = AsyncMock()
    mock_span_title0 = AsyncMock()
    mock_span_title0.get_attribute.return_value = "Contacto Individual"
    mock_component0.query_selector.return_value = mock_span_title0
    
    mock_datetime_child = AsyncMock()
    mock_datetime_child.text_content.return_value = "11:00 AM"
    mock_component0.query_selector_all.return_value = [MagicMock(), mock_datetime_child]

    # Mock de components[1] (info_text con dos puntos, pero sin remitente)
    mock_component1 = AsyncMock()
    mock_info_child = AsyncMock()
    mock_info_child.text_content.return_value = "Mensaje: con dos puntos"
    mock_component1.query_selector_all.return_value = [mock_info_child]

    mock_element.query_selector_all.return_value = [mock_component0, mock_component1]

    # Mock de unread_el
    mock_unread_el = AsyncMock()
    mock_unread_el.inner_text.return_value = "1"
    mock_element.query_selector.return_value = mock_unread_el

    result = await mock_chat_manager._parse_search_result(mock_element)

    assert result is not None
    assert result["type"] == "CHATS"
    assert result["name"] == "Contacto Individual"
    assert result["last_activity"] == "11:00 AM"
    assert result["last_message"] == "Mensaje: con dos puntos"
    assert result["unread_count"] == "1"
    assert result["group"] is None
