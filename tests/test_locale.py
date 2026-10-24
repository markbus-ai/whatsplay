"""Client(locale=...) reaches the browser context and the Accept-Language header."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from whatsplay import Client


def _browser_type():
    context = MagicMock()
    context.browser = MagicMock()
    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)
    browser_type = MagicMock()
    browser_type.launch_persistent_context = AsyncMock(return_value=context)
    browser_type.launch = AsyncMock(return_value=browser)
    return browser_type, browser


@pytest.mark.asyncio
async def test_persistent_context_uses_the_requested_locale():
    client = Client(locale="es-AR")
    browser_type, _ = _browser_type()

    await client._init_persistent_context(browser_type, "/tmp/profile", {"args": []})

    kwargs = browser_type.launch_persistent_context.call_args.kwargs
    assert kwargs["locale"] == "es-AR"


@pytest.mark.asyncio
async def test_regular_context_uses_the_requested_locale():
    client = Client(locale="es-AR")
    browser_type, browser = _browser_type()

    await client._init_regular_context(browser_type, {"headless": True})

    assert browser.new_context.call_args.kwargs["locale"] == "es-AR"


@pytest.mark.asyncio
async def test_accept_language_follows_the_requested_locale():
    client = Client(locale="es-AR")
    client._context = MagicMock()
    client._context.set_extra_http_headers = AsyncMock()
    client._context.add_init_script = AsyncMock()

    await client._configure_context()

    headers = client._context.set_extra_http_headers.call_args.args[0]
    assert headers["Accept-Language"].startswith("es-AR,")


@pytest.mark.asyncio
async def test_default_locale_is_still_en_us():
    client = Client()
    browser_type, _ = _browser_type()

    await client._init_persistent_context(browser_type, "/tmp/profile", {"args": []})

    assert client.locale == "en-US"
    assert browser_type.launch_persistent_context.call_args.kwargs["locale"] == "en-US"
