"""A message must only ever be typed into the chat that was requested.

Before 2.6.4, open() accepted any visible composer as success and fell back to
ArrowDown+Enter when no search result matched, so text meant for one chat
could land in whichever chat (often a group) was open.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import whatsplay.constants.locator as loc
from whatsplay.chat_manager import DEFAULT_WAIT_TIMEOUT, ChatManager
from whatsplay.wa_elements import WhatsAppElements, parse_composer_label, same_chat


@pytest.mark.parametrize(
    "a, b",
    [
        ("+54 9 2234 48-0402", "+5492234480402"),
        ("+54 9 2234 48-0402", "5492234480402"),
        ("Juan Pérez", "juan  perez"),
        ("~ Juan", "Juan"),
        ("Cliente", "cliente"),
    ],
)
def test_same_chat_accepts_the_same_chat(a, b):
    assert same_chat(a, b)


@pytest.mark.parametrize(
    "a, b",
    [
        ("Cliente", "Cliente (pruebas)"),
        ("+54 9 2234 48-0402", "+54 9 2234 48-0403"),
        ("Juan", "Juana"),
        ("8856", "+54 9 2235 98-8856"),
        # A local number is not enough: 2235988856 is also a valid suffix of
        # numbers in other countries (e.g. +1 223 598 8856).
        ("2235988856", "+54 9 2235 98-8856"),
        ("2235988856", "+1 223 598 8856"),
        ("", ""),
    ],
)
def test_same_chat_keeps_different_chats_apart(a, b):
    assert not same_chat(a, b)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "composer_label, expected",
    [
        ("Escribir un mensaje para +54 9 2234 48-0402", "+54 9 2234 48-0402"),
        ("Escribir un mensaje para el grupo Cliente", "Cliente"),
    ],
)
async def test_active_chat_title_reads_the_open_composer(composer_label, expected):
    page = AsyncMock()
    page.evaluate.return_value = {"composer": composer_label, "header": "ignored"}
    elements = WhatsAppElements(page)

    assert await elements.active_chat_title() == expected


@pytest.mark.asyncio
async def test_active_chat_title_falls_back_to_header():
    page = AsyncMock()
    page.evaluate.return_value = {"composer": None, "header": "Cliente"}
    elements = WhatsAppElements(page)

    assert await elements.active_chat_title() == "Cliente"


@pytest.mark.asyncio
async def test_open_does_not_press_arrowdown_enter_when_no_result_matches(monkeypatch):
    page = AsyncMock()
    page.keyboard = AsyncMock()
    page.query_selector.return_value = None
    elements = WhatsAppElements(page)
    elements.prepare_search = AsyncMock(return_value=AsyncMock())

    other = AsyncMock()
    title = AsyncMock()
    title.get_attribute.return_value = "Cliente"
    other.query_selector.return_value = title
    page.query_selector_all.return_value = [other]
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("+54 9 2235 98-8856") is False

    page.keyboard.press.assert_not_awaited()
    other.click.assert_not_awaited()


@pytest.mark.asyncio
async def test_open_fails_when_the_active_chat_is_not_the_target(monkeypatch):
    page = AsyncMock()
    chat = AsyncMock()
    chat.get_attribute.return_value = "+54 9 2235 98-8856"
    page.query_selector_all.return_value = [chat]
    elements = WhatsAppElements(page)
    # The click "worked" but WhatsApp still shows the group.
    elements.active_chat = AsyncMock(return_value=("group", "Cliente"))
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("+54 9 2235 98-8856") is False


@pytest.mark.asyncio
async def test_open_direct_lookup_skips_titles_that_only_contain_the_name(monkeypatch):
    page = AsyncMock()
    lookalike = AsyncMock()
    lookalike.get_attribute.return_value = "Cliente (pruebas)"
    exact = AsyncMock()
    exact.get_attribute.return_value = "Cliente"
    page.query_selector_all.return_value = [lookalike, exact]
    elements = WhatsAppElements(page)
    elements.active_chat = AsyncMock(return_value=("group", "Cliente"))
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("Cliente") is True

    lookalike.click.assert_not_awaited()
    exact.click.assert_awaited_once_with()


def _manager_with_open_chat(active_title):
    client = MagicMock()
    client._page_lock = __import__("asyncio").Lock()
    client.wait_until_logged_in = AsyncMock(return_value=True)
    client.emit = AsyncMock()
    page = AsyncMock()
    page.keyboard = AsyncMock()
    composer = AsyncMock()
    composer.get_attribute.return_value = f"Escribir un mensaje para {active_title}"
    composer.inner_text.return_value = ""
    page.wait_for_selector.return_value = composer
    manager = ChatManager(client)
    manager._page = page
    manager.open = AsyncMock(return_value=True)
    manager.close = AsyncMock()
    manager.wait_for_sent_confirmation = AsyncMock(return_value=True)
    manager.wa_elements = MagicMock()
    manager.wa_elements.active_chat_title = AsyncMock(return_value=active_title)
    return manager, page, composer


@pytest.mark.asyncio
async def test_send_message_never_types_into_another_chat(monkeypatch):
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    manager, page, composer = _manager_with_open_chat(active_title="Cliente")

    assert await manager.send_message("+54 9 2235 98-8856", "Hola") is False

    composer.fill.assert_not_awaited()
    page.keyboard.press.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_message_types_into_the_verified_chat(monkeypatch):
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    manager, page, composer = _manager_with_open_chat(active_title="+54 9 2235 98-8856")
    composer.inner_text.return_value = "Hola"

    assert await manager.send_message("+5492235988856", "Hola") is True

    composer.fill.assert_awaited_once_with("Hola")
    page.wait_for_selector.assert_any_await(loc.ACTIVE_CHAT_COMPOSER, timeout=DEFAULT_WAIT_TIMEOUT)


def test_group_info_button_matches_current_whatsapp_web():
    # Verified live 2026-10-20: the header button is titled "Información del perfil".
    assert "Información del perfil" in loc.GROUP_INFO_BUTTON
    # Every title alternative must require role=button (was an or/and precedence bug).
    assert loc.GROUP_INFO_BUTTON.count("@role=\"button\"") == 1
    assert ") and @role" in loc.GROUP_INFO_BUTTON


@pytest.mark.parametrize(
    "label, expected",
    [
        ("Escribir un mensaje para +54 9 2234 48-0402", ("chat", "+54 9 2234 48-0402")),
        ("Escribir un mensaje para el grupo Cliente", ("group", "Cliente")),
        # English labels verified live 2026-10-20 (WhatsApp Web with an English phone).
        ("Type a message to Mika Bici", ("chat", "Mika Bici")),
        ("Type a message to group Tres Chiflados", ("group", "Tres Chiflados")),
        ("Añadir un comentario", None),
        (None, None),
    ],
)
def test_parse_composer_label_tells_groups_from_chats(label, expected):
    assert parse_composer_label(label) == expected


@pytest.mark.asyncio
async def test_a_contact_named_like_a_group_is_not_the_group():
    page = AsyncMock()
    page.evaluate.return_value = {"composer": "Escribir un mensaje para Cliente", "header": "Cliente"}
    elements = WhatsAppElements(page)

    assert await elements.is_active_chat("Cliente", is_group=True) is False
    assert await elements.is_active_chat("Cliente", is_group=False) is True


@pytest.mark.asyncio
async def test_open_refuses_when_two_listed_chats_share_the_title(monkeypatch):
    page = AsyncMock()
    first, second = AsyncMock(), AsyncMock()
    first.get_attribute.return_value = "Cliente"
    second.get_attribute.return_value = "Cliente"
    page.query_selector_all.return_value = [first, second]
    elements = WhatsAppElements(page)
    elements.prepare_search = AsyncMock(return_value=None)
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("Cliente") is False

    first.click.assert_not_awaited()
    second.click.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_refuses_when_only_the_header_names_the_target(monkeypatch):
    # The element we would type into must itself name the chat; a header that
    # matches is not enough (another editor could have focus in the footer).
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    manager, page, composer = _manager_with_open_chat(active_title="+54 9 2235 98-8856")
    composer.get_attribute.return_value = "Añadir un comentario"

    assert await manager.send_message("+54 9 2235 98-8856", "Hola") is False

    composer.fill.assert_not_awaited()


@pytest.mark.asyncio
async def test_open_aborts_when_the_search_box_did_not_receive_the_query(monkeypatch):
    # Keys typed while focus moved elsewhere: the box holds only part of it.
    page = AsyncMock()
    page.query_selector_all.return_value = []
    search_box = AsyncMock()
    search_box.input_value.return_value = "+54 9 22"
    elements = WhatsAppElements(page)
    elements.prepare_search = AsyncMock(return_value=search_box)
    elements.close_search = AsyncMock(return_value=True)
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("+54 9 2235 98-8856") is False

    elements.close_search.assert_awaited()
    page.wait_for_selector.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_presses_enter_on_the_composer_not_on_focus(monkeypatch):
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    manager, page, composer = _manager_with_open_chat(active_title="Cliente")
    composer.inner_text.return_value = "Hola"

    assert await manager.send_message("Cliente", "Hola") is True

    composer.press.assert_awaited_once_with("Enter")
    page.keyboard.press.assert_not_awaited()
    assert composer.click.await_args.kwargs.get("force") is not True


@pytest.mark.asyncio
async def test_send_does_not_press_enter_when_the_composer_text_differs(monkeypatch):
    # e.g. stray digits left in the composer by a misdirected keystroke.
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    manager, page, composer = _manager_with_open_chat(active_title="Cliente")
    composer.inner_text.return_value = "2235Hola"

    assert await manager.send_message("Cliente", "Hola") is False

    composer.press.assert_not_awaited()
    page.keyboard.press.assert_not_awaited()


@pytest.mark.asyncio
async def test_open_via_url_accepts_a_saved_contact_shown_by_name(monkeypatch):
    # The URL names the phone; WhatsApp shows the saved contact's name instead.
    page = AsyncMock()
    invalid = AsyncMock()
    invalid.is_visible.return_value = False
    page.query_selector.return_value = invalid
    elements = WhatsAppElements(page)
    elements.active_chat = AsyncMock(return_value=("chat", "Juan Bici"))
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("+54 9 2235 98-8856", open_via_url=True) is True
    assert elements.last_opened_title == "Juan Bici"


@pytest.mark.asyncio
async def test_open_via_url_rejects_a_group(monkeypatch):
    page = AsyncMock()
    invalid = AsyncMock()
    invalid.is_visible.return_value = False
    page.query_selector.return_value = invalid
    elements = WhatsAppElements(page)
    elements.active_chat = AsyncMock(return_value=("group", "Cliente"))
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("+54 9 2235 98-8856", open_via_url=True) is False


@pytest.mark.asyncio
async def test_send_via_url_to_a_saved_contact_writes_to_the_opened_chat(monkeypatch):
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    manager, page, composer = _manager_with_open_chat(active_title="Juan Bici")
    manager.wa_elements.last_opened_title = "Juan Bici"
    composer.inner_text.return_value = "Hola"

    assert await manager.send_message("+54 9 2235 98-8856", "Hola", open_via_url=True) is True

    composer.fill.assert_awaited_once_with("Hola")


@pytest.mark.asyncio
async def test_send_accepts_the_editor_bullet_artifact(monkeypatch):
    # Observed live 2026-10-20 on all 28 real bot replies: before a "\n* " list
    # line, the Lexical composer's inner_text shows "•" in place of one
    # character. Same length, otherwise identical, and the message is sent fine.
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    manager, page, composer = _manager_with_open_chat(active_title="Cliente")
    message = "Precios:\n---\nCubiertas:\n* Rodado 26: $100"
    composer.inner_text.return_value = "Precios:\n---\nCubierta•:\n* Rodado 26: $100"

    assert await manager.send_message("Cliente", message) is True

    composer.press.assert_awaited_once_with("Enter")
