"""Login-state locators and the blocking 'what's new' dialog (verified live 2026-10-20)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import whatsplay.constants.locator as loc
from whatsplay.wa_elements import WhatsAppElements


def test_login_locators_use_the_verified_test_ids():
    # The QR canvas label is English even in the Spanish UI and has no "!";
    # the data-testid is language independent.
    assert loc.QR_CODE == '[data-testid="link-device-qr-code"] canvas'
    assert '[data-testid="link-device-qr-code"]' in loc.AUTH
    # The WhatsApp wordmark is also on the QR page; only the chat list proves a session.
    assert loc.LOGGED_IN == "[data-testid='chat-list']"


def _page_with_dialog(close_count, dialogs_after):
    page = MagicMock()
    dialog = MagicMock()
    dialog.count = AsyncMock(side_effect=[1] + dialogs_after)
    close = MagicMock()
    close.count = AsyncMock(return_value=close_count)
    close.first.click = AsyncMock()

    def locator(selector):
        return close if selector == loc.DIALOG_CLOSE_BUTTON else dialog

    page.locator.side_effect = locator
    return page, close


@pytest.mark.asyncio
async def test_dismiss_closes_the_dialog_with_its_close_button_only():
    page, close = _page_with_dialog(close_count=1, dialogs_after=[0])
    elements = WhatsAppElements(page)

    assert await elements.dismiss_blocking_dialog() is True

    close.first.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_dismiss_never_clicks_a_dialog_without_a_close_button():
    # e.g. a confirmation dialog: only "Continuar"/"OK" buttons, no X.
    page, close = _page_with_dialog(close_count=0, dialogs_after=[1])
    elements = WhatsAppElements(page)

    assert await elements.dismiss_blocking_dialog() is False

    close.first.click.assert_not_awaited()


@pytest.mark.asyncio
async def test_dismiss_reports_failure_when_the_dialog_stays():
    page, close = _page_with_dialog(close_count=1, dialogs_after=[1])
    elements = WhatsAppElements(page)

    assert await elements.dismiss_blocking_dialog() is False


@pytest.mark.asyncio
async def test_open_dismisses_a_blocking_dialog_first(monkeypatch):
    page = AsyncMock()
    page.query_selector_all.return_value = []
    elements = WhatsAppElements(page)
    elements.dismiss_blocking_dialog = AsyncMock(return_value=True)
    elements.prepare_search = AsyncMock(return_value=None)
    monkeypatch.setattr("whatsplay.wa_elements.asyncio.sleep", AsyncMock())

    await elements.open("Cliente")

    elements.dismiss_blocking_dialog.assert_awaited_once()


def _logged_in_state_manager():
    from whatsplay.state_manager import StateManager

    client = MagicMock()
    client._page = MagicMock()
    client._is_running = True
    client._page_lock = __import__("asyncio").Lock()
    client.emit = AsyncMock()
    client.wa_elements = MagicMock()
    manager = StateManager(client)
    return manager, client


@pytest.mark.asyncio
async def test_logged_in_tick_warns_once_about_an_undismissable_dialog():
    manager, client = _logged_in_state_manager()
    client.wa_elements.dismiss_blocking_dialog = AsyncMock(return_value=False)

    await manager._handle_logged_in_state()
    await manager._handle_logged_in_state()

    warnings = [c for c in client.emit.await_args_list if c.args[0] == "on_warning"]
    assert len(warnings) == 1


@pytest.mark.asyncio
async def test_logged_in_tick_never_clicks_a_continue_button():
    manager, client = _logged_in_state_manager()
    client.wa_elements.dismiss_blocking_dialog = AsyncMock(return_value=False)

    await manager._handle_logged_in_state()

    client._page.query_selector.assert_not_called()


def _qr_state_manager(refresh_visible_after_click):
    from whatsplay.state_manager import StateManager

    client = MagicMock()
    client._page = MagicMock()
    client.emit = AsyncMock()
    client.wa_elements = MagicMock()
    manager = StateManager(client)
    refresh = AsyncMock()
    refresh.is_visible.side_effect = [True, refresh_visible_after_click]
    canvas = AsyncMock()

    async def query_selector(selector):
        return refresh if selector == loc.QR_REFRESH_BUTTON else canvas

    client._page.query_selector = query_selector
    manager._extract_image_from_canvas = AsyncMock(return_value=b"new-qr")
    manager._handle_qr_logic = AsyncMock(return_value=True)
    return manager, client, refresh


@pytest.mark.asyncio
async def test_expired_qr_is_refreshed_with_the_current_button(monkeypatch):
    monkeypatch.setattr("whatsplay.state_manager.asyncio.sleep", AsyncMock())
    manager, client, refresh = _qr_state_manager(refresh_visible_after_click=False)

    await manager._handle_qr_auth_state()

    refresh.click.assert_awaited_once()
    client.emit.assert_awaited_with("on_qr_change", b"new-qr")


@pytest.mark.asyncio
async def test_expired_qr_is_not_reported_while_still_expired(monkeypatch):
    monkeypatch.setattr("whatsplay.state_manager.asyncio.sleep", AsyncMock())
    manager, client, refresh = _qr_state_manager(refresh_visible_after_click=True)

    await manager._handle_qr_auth_state()

    assert not any(c.args[0] == "on_qr_change" for c in client.emit.await_args_list)


@pytest.mark.asyncio
async def test_logged_in_tick_leaves_dialogs_alone_while_an_operation_holds_the_lock():
    # e.g. send_file's media preview or a group dialog opened under the lock.
    from whatsplay.page_lock import ReentrantLock

    manager, client = _logged_in_state_manager()
    client._page_lock = ReentrantLock()
    client.wa_elements.dismiss_blocking_dialog = AsyncMock(return_value=True)
    holder_inside = asyncio.Event()
    release = asyncio.Event()

    async def operation():
        async with client._page_lock:
            holder_inside.set()
            await release.wait()

    task = asyncio.create_task(operation())
    await holder_inside.wait()
    await manager._handle_logged_in_state()
    release.set()
    await task

    client.wa_elements.dismiss_blocking_dialog.assert_not_awaited()
