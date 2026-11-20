"""2.6.12 clicked the "Llamadas" rail button when selecting "All" (prod
2026-11-20): it is a <button aria-pressed> whose icon carries a title
"ic-call", so :has-text('All') matched "call", and the comma-joined selector
returned it first because the rail precedes the filter row in the DOM."""

import os

import pytest

from whatsplay.wa_elements import WhatsAppElements

# Markup as captured from production (classes and styles dropped).
PROD = """
<script>window.clicked = [];
function press(b) { window.clicked.push(b.dataset.k); b.setAttribute('aria-pressed', 'true'); }</script>
<button aria-label="Llamadas" aria-pressed="false" tabindex="-1" type="button" data-k="calls"
        data-navbar-item="true" onclick="press(this)">
  <div><span aria-hidden="true"><svg viewBox="0 0 24 24" height="24" width="24">
    <title>ic-call</title><path d="M0 0h24v24H0z"></path></svg></span></div></button>
<div role="group" aria-label="Chat filters" data-testid="chat_list_filters_row">
  <button data-tab="3" aria-pressed="{all}" id="all-filter" type="button" data-k="all" onclick="press(this)">
    <span title="Todos"><span>Todos</span></span></button>
  <button data-tab="3" aria-pressed="false" id="label_item_1" type="button" data-k="unread" onclick="press(this)">
    <span title="No leídos"><span>No leídos</span></span>2</button>
  <button data-tab="3" aria-pressed="false" id="label_item_3" type="button" data-k="groups" onclick="press(this)">
    <span title="Grupos"><span>Grupos</span></span></button>
</div>
"""


async def _click(filter_type, all_pressed):
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        try:
            browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        except Exception as e:  # no browser installed in this environment
            pytest.skip(f"chromium unavailable: {e}")
        page = await browser.new_page()
        await page.set_content(PROD.replace("{all}", all_pressed))
        ok = await WhatsAppElements(page).click_chat_filter(filter_type)
        clicked = await page.evaluate("window.clicked")
        await browser.close()
    return ok, clicked


@pytest.mark.asyncio
@pytest.mark.parametrize("all_pressed, clicked", [("true", []), ("false", ["all"])])
async def test_all_never_clicks_the_calls_rail_button(all_pressed, clicked):
    assert await _click("all", all_pressed) == (True, clicked)


@pytest.mark.asyncio
@pytest.mark.parametrize("filter_type", ["unread", "groups"])
async def test_other_filters_never_click_the_calls_rail_button(filter_type):
    assert await _click(filter_type, "true") == (True, [filter_type])


@pytest.mark.asyncio
async def test_english_dropdown_item_is_still_selected():
    """Replaces a mock test pinned to the old single toggle selector."""
    async_api = pytest.importorskip("playwright.async_api")
    html = ("<script>window.clicked = [];</script>"
            '<button id="additional-filters" onclick="document.getElementById(\'m\').hidden=false">More</button>'
            '<div id="m" role="menu" hidden><button role="menuitem" '
            "onclick=\"window.clicked.push('all'); this.parentNode.hidden=true\">All</button></div>")
    async with async_api.async_playwright() as p:
        try:
            browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        except Exception as e:  # no browser installed in this environment
            pytest.skip(f"chromium unavailable: {e}")
        page = await browser.new_page()
        await page.set_content(html)
        ok = await WhatsAppElements(page).click_chat_filter("all")
        clicked = await page.evaluate("window.clicked")
        await browser.close()
    assert (ok, clicked) == (True, ["all"])
