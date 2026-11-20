"""WhatsApp Web (seen in production 2026-11-20) renders the chat filters as
toggle buttons: <button id="all-filter" aria-pressed="true">, with no
role="tab". The search route and the unread scan must still find "All"."""

import os
from types import SimpleNamespace

import pytest

from whatsplay.chat_manager import ChatManager
from whatsplay.wa_elements import WhatsAppElements

PAGE = """
<div role="group" aria-label="Chat filters" data-testid="chat_list_filters_row">
  <div data-testid="filter-button" role="none"><span>
    <button data-tab="3" aria-pressed="{all_pressed}" id="all-filter" type="button"
            onclick="window.clicks++; this.setAttribute('aria-pressed','true');
                     document.getElementById('unread-filter').setAttribute('aria-pressed','false')">
      <div><span title="Todos"><span>Todos</span></span></div>
    </button>
  </span></div>
  <div data-testid="filter-button" role="none"><span>
    <button aria-pressed="{unread_pressed}" id="unread-filter" type="button">
      <div><span title="No leídos"><span>No leídos</span></span></div>
    </button>
  </span></div>
</div>
<div id="pane-side" style="height:100px; overflow-y:auto">
  <div role="grid" style="height:5000px"></div>
</div>
<script>window.clicks = 0; document.getElementById('pane-side').scrollTop = 3000;</script>
"""


async def _page(p, all_pressed):
    try:
        browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
    except Exception as e:  # no browser installed in this environment
        pytest.skip(f"chromium unavailable: {e}")
    page = await browser.new_page()
    await page.set_content(PAGE.format(
        all_pressed=str(all_pressed).lower(),
        unread_pressed=str(not all_pressed).lower(),
    ))
    return browser, page


async def _state(page):
    return await page.evaluate("""() => ({
        top: document.getElementById('pane-side').scrollTop,
        all: document.getElementById('all-filter').getAttribute('aria-pressed'),
        clicks: window.clicks,
    })""")


@pytest.mark.asyncio
@pytest.mark.parametrize("all_pressed, clicks", [(False, 1), (True, 0)])
async def test_search_route_selects_all_with_toggle_buttons(all_pressed, clicks):
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        browser, page = await _page(p, all_pressed)
        ok = await WhatsAppElements(page).click_chat_filter("all")
        state = await _state(page)
        await browser.close()
    assert ok is True
    assert state["all"] == "true"
    assert state["clicks"] == clicks  # already pressed: no click


@pytest.mark.asyncio
@pytest.mark.parametrize("all_pressed, clicks", [(False, 1), (True, 0)])
async def test_unread_scan_resets_to_all_with_toggle_buttons(all_pressed, clicks):
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        browser, page = await _page(p, all_pressed)
        await ChatManager._reset_chat_list(SimpleNamespace(_page=page))
        state = await _state(page)
        await browser.close()
    assert state["all"] == "true"
    assert state["clicks"] == clicks
    assert state["top"] == 0
