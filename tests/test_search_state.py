from unittest.mock import AsyncMock, MagicMock, call

import pytest

from whatsplay.chat_manager import ChatManager
from whatsplay.wa_elements import WhatsAppElements


@pytest.mark.asyncio
async def test_prepare_search_selects_all_before_typing():
    page = AsyncMock()
    elements = WhatsAppElements(page)
    search_box = AsyncMock()
    events = []

    async def activate_search():
        events.append("activate")
        return True

    async def close_search():
        events.append("close")
        return True

    async def get_search_box():
        events.append("input")
        return search_box

    async def select_filter(filter_type):
        events.append(f"filter:{filter_type}")
        return filter_type == "all"

    async def fill_search(_value):
        events.append("fill")

    async def type_search(_value, delay):
        events.append("type")

    elements.verify_search_active = AsyncMock(return_value=True)
    elements.close_search = close_search
    elements.click_search_button = activate_search
    elements._get_search_box = get_search_box
    elements.click_chat_filter = select_filter
    search_box.fill.side_effect = fill_search
    search_box.type.side_effect = type_search

    prepared = await elements.prepare_search()
    await prepared.fill("")
    await prepared.type("2235988856", delay=100)

    assert prepared is search_box
    assert events == ["close", "filter:all", "activate", "input", "fill", "type"]


@pytest.mark.asyncio
async def test_prepare_search_does_not_cleanup_when_search_is_inactive():
    page = AsyncMock()
    elements = WhatsAppElements(page)
    search_box = AsyncMock()
    elements.verify_search_active = AsyncMock(return_value=False)
    elements.close_search = AsyncMock(return_value=True)
    elements.click_chat_filter = AsyncMock(return_value=True)
    elements.click_search_button = AsyncMock(return_value=True)
    elements._get_search_box = AsyncMock(return_value=search_box)

    assert await elements.prepare_search() is search_box
    elements.close_search.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_search_fails_closed_when_active_search_cannot_close():
    page = AsyncMock()
    elements = WhatsAppElements(page)
    elements.verify_search_active = AsyncMock(return_value=True)
    elements.close_search = AsyncMock(return_value=False)
    elements.click_chat_filter = AsyncMock(return_value=True)

    assert await elements.prepare_search() is None
    elements.close_search.assert_awaited_once_with()
    elements.click_chat_filter.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_search_fails_closed_when_all_filter_cannot_be_selected():
    page = AsyncMock()
    elements = WhatsAppElements(page)
    search_box = AsyncMock()
    elements._search_active = True
    elements.click_search_button = AsyncMock(return_value=True)
    elements._get_search_box = AsyncMock(return_value=search_box)
    elements.click_chat_filter = AsyncMock(return_value=False)

    prepared = await elements.prepare_search()

    assert prepared is None
    search_box.press.assert_awaited_once_with("Escape")
    assert elements._search_active is False


@pytest.mark.asyncio
async def test_chat_composer_focus_is_not_active_search():
    page = AsyncMock()
    page.evaluate.return_value = False
    elements = WhatsAppElements(page)

    assert await elements.verify_search_active() is False
    assert elements._search_active is False
    page.wait_for_selector.assert_not_called()


@pytest.mark.asyncio
async def test_active_search_uses_one_targeted_escape():
    page = AsyncMock()
    elements = WhatsAppElements(page)
    search_box = AsyncMock()
    elements._search_active = True
    elements._get_search_box = AsyncMock(return_value=search_box)

    assert await elements.close_search() is True

    search_box.press.assert_awaited_once_with("Escape")
    page.keyboard.press.assert_not_awaited()
    assert elements._search_active is False


@pytest.mark.asyncio
async def test_normal_chat_close_still_sends_escape():
    page = AsyncMock()
    client = MagicMock()
    client._page = page
    client.wa_elements = MagicMock()
    client.wa_elements.close_search = AsyncMock(return_value=False)
    client.emit = AsyncMock()
    manager = ChatManager(client)

    await manager.close()

    client.wa_elements.close_search.assert_awaited_once_with()
    page.keyboard.press.assert_awaited_once_with("Escape")


@pytest.mark.asyncio
async def test_chat_manager_does_not_escape_chat_after_search_cleanup():
    page = AsyncMock()
    client = MagicMock()
    client._page = page
    client.wa_elements = MagicMock()
    client.wa_elements.close_search = AsyncMock(return_value=True)
    client.emit = AsyncMock()
    manager = ChatManager(client)

    await manager.close()

    client.wa_elements.close_search.assert_awaited_once_with()
    page.keyboard.press.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_chats_uses_shared_preparation():
    page = AsyncMock()
    elements = WhatsAppElements(page)
    search_box = AsyncMock()
    elements.prepare_search = AsyncMock(return_value=search_box)
    elements.close_search = AsyncMock(return_value=True)
    elements.wait_for_selector = AsyncMock(return_value=MagicMock())
    result = AsyncMock()
    result.inner_text.return_value = "Alice\nHello"
    page.locator = MagicMock()
    page.locator.return_value.all = AsyncMock(return_value=[result])

    await elements.search_chats("2235988856")

    elements.prepare_search.assert_awaited_once_with()
    elements.close_search.assert_awaited_once_with()
    search_box.type.assert_awaited_once_with("2235988856", delay=100)


@pytest.mark.asyncio
async def test_open_search_route_uses_shared_preparation(monkeypatch):
    page = AsyncMock()
    elements = WhatsAppElements(page)
    search_box = AsyncMock()
    elements.prepare_search = AsyncMock(return_value=search_box)
    page.query_selector.return_value = None

    chat = AsyncMock()
    title = AsyncMock()
    title.get_attribute.return_value = "Alice"
    chat.query_selector.return_value = title
    page.query_selector_all.return_value = [chat]

    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("Alice") is True

    elements.prepare_search.assert_awaited_once_with()
    search_box.type.assert_awaited_once_with("Alice", delay=100)
    chat.click.assert_awaited_once_with()
    assert elements._search_active is False


@pytest.mark.asyncio
async def test_keyboard_search_fallback_does_not_escape():
    page = AsyncMock()
    page.wait_for_selector.side_effect = Exception("not found")
    elements = WhatsAppElements(page)

    assert await elements.click_search_button() is True

    page.keyboard.press.assert_awaited_once_with("Control+/")


@pytest.mark.asyncio
async def test_all_filter_accepts_english_tab_label(monkeypatch):
    page = MagicMock()
    tab = MagicMock()
    tab.count = AsyncMock(return_value=1)
    tab.first.is_visible = AsyncMock(return_value=True)
    tab.first.click = AsyncMock()
    page.locator.return_value = tab
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())
    elements = WhatsAppElements(page)

    assert await elements.click_chat_filter("all") is True

    page.locator.assert_called_once_with(
        "button[role='tab']:has-text('All'), button[role='tab']:has-text('Todos')"
    )
    tab.first.click.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_all_filter_accepts_english_dropdown_label(monkeypatch):
    page = MagicMock()
    tab = MagicMock()
    tab.count = AsyncMock(return_value=0)
    more = MagicMock()
    more.count = AsyncMock(return_value=1)
    more.first.click = AsyncMock()
    item = MagicMock()
    item.count = AsyncMock(return_value=1)
    item.first.click = AsyncMock()
    page.locator.side_effect = [tab, more, item]
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())
    elements = WhatsAppElements(page)

    assert await elements.click_chat_filter("all") is True

    assert page.locator.call_args_list == [
        call("button[role='tab']:has-text('All'), button[role='tab']:has-text('Todos')"),
        call("button#additional-filters"),
        call("button[role='menuitem']:has-text('All'), button[role='menuitem']:has-text('Todos')"),
    ]
    item.first.click.assert_awaited_once_with()
