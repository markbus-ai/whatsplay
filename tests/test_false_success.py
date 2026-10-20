"""Operations must report failure when they fail, and act on the current page."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from whatsplay.client import Client
from whatsplay.wa_elements import WhatsAppElements


@pytest.mark.asyncio
async def test_add_members_does_nothing_when_the_group_does_not_open():
    page = AsyncMock()
    elements = WhatsAppElements(page)
    elements.open = AsyncMock(return_value=False)

    assert await elements.add_members_to_group("Cliente", ["Ana"]) is False

    elements.open.assert_awaited_once()
    page.wait_for_selector.assert_not_awaited()


@pytest.mark.asyncio
async def test_open_closes_the_search_when_results_time_out(monkeypatch):
    page = AsyncMock()
    page.query_selector_all.return_value = []
    search_box = AsyncMock()
    search_box.input_value.return_value = "Alice"
    elements = WhatsAppElements(page)
    elements.prepare_search = AsyncMock(return_value=search_box)
    elements.close_search = AsyncMock(return_value=True)
    elements._search_active = True
    page.wait_for_selector.side_effect = PlaywrightTimeoutError("no results")
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    assert await elements.open("Alice") is False

    elements.close_search.assert_awaited()


@pytest.mark.asyncio
async def test_reconnect_rebinds_components_to_the_new_page(monkeypatch):
    client = Client()
    old_page, new_page = MagicMock(name="old"), MagicMock(name="new")
    client._page = old_page
    client._bind_components()
    assert client.wa_elements.page is old_page

    async def fake_base_reconnect(self):
        self._page = new_page

    monkeypatch.setattr("whatsplay.base_client.BaseWhatsAppClient.reconnect", fake_base_reconnect)
    await client.reconnect()

    assert client.wa_elements.page is new_page
    assert client.chat_manager._page is new_page
    assert client.state_manager._page is new_page
    assert client.chat_manager.wa_elements is client.wa_elements


@pytest.mark.asyncio
async def test_send_file_reports_failure_when_not_confirmed(tmp_path, monkeypatch):
    import asyncio as _asyncio
    from contextlib import asynccontextmanager

    from whatsplay.chat_manager import ChatManager

    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    path = tmp_path / "f.pdf"
    path.write_bytes(b"x")

    client = MagicMock()
    client._page_lock = _asyncio.Lock()
    client.wait_until_logged_in = AsyncMock(return_value=True)
    client.emit = AsyncMock()
    page = MagicMock()
    composer = AsyncMock()
    composer.get_attribute.return_value = "Escribir un mensaje para el grupo Cliente"
    page.wait_for_selector = AsyncMock(side_effect=[composer, AsyncMock()])

    chooser = MagicMock()
    chooser.set_files = AsyncMock()
    info = MagicMock()

    async def _value():
        return chooser

    info.value = _value()

    @asynccontextmanager
    async def expect_file_chooser(timeout):
        yield info

    page.expect_file_chooser = expect_file_chooser
    button = MagicMock()
    button.count = AsyncMock(return_value=1)
    button.click = AsyncMock()
    button.wait_for = AsyncMock()
    page.locator.return_value.first = button

    manager = ChatManager(client)
    manager._page = page
    manager.open = AsyncMock(return_value=True)
    manager.wait_for_sent_confirmation = AsyncMock(return_value=False)

    assert await manager.send_file("Cliente", str(path), is_group=True) is False


def _manager_for_confirmation(evaluate_results):
    from whatsplay.chat_manager import ChatManager

    client = MagicMock()
    manager = ChatManager(client)
    manager._page = MagicMock()
    manager._page.evaluate = AsyncMock(side_effect=evaluate_results)
    return manager


@pytest.mark.asyncio
async def test_confirmation_requires_a_new_bubble_with_a_status(monkeypatch):
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    # An old outgoing bubble already shows "Leído"; the new one appears later.
    manager = _manager_for_confirmation([
        [],                                   # nothing new yet
        [{"id": "NEW", "status": True}],      # our message, confirmed
    ])

    assert await manager.wait_for_sent_confirmation({"OLD"}, timeout=5000) is True


@pytest.mark.asyncio
async def test_confirmation_fails_when_no_new_bubble_appears(monkeypatch):
    # The previous outgoing message being "Leído" must not count as success.
    monkeypatch.setattr("whatsplay.chat_manager.asyncio.sleep", AsyncMock())
    clock = iter(range(0, 100, 1))
    monkeypatch.setattr("whatsplay.chat_manager.time.monotonic", lambda: next(clock))
    manager = _manager_for_confirmation(lambda *a, **k: [])
    manager._page.evaluate = AsyncMock(return_value=[])

    assert await manager.wait_for_sent_confirmation({"OLD"}, timeout=5000) is False
