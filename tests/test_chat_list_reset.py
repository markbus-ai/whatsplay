"""The unread scan only sees rendered rows of the virtualized chat list, so
before sweeping it must show the "All" filter scrolled to the top."""

import os
from types import SimpleNamespace

import pytest

from whatsplay.chat_manager import ChatManager

PAGE = """
<div>
  <button role="tab" id="all-filter" aria-selected="{all_selected}"
          onclick="window.clicks++; this.setAttribute('aria-selected','true');
                   document.getElementById('unread').setAttribute('aria-selected','false')">Todos</button>
  <button role="tab" id="unread" aria-selected="{unread_selected}">No leídos</button>
</div>
<div id="pane-side" style="height:100px; overflow-y:auto">
  <div role="grid" style="height:5000px"></div>
</div>
<script>window.clicks = 0; document.getElementById('pane-side').scrollTop = 3000;</script>
"""


async def _run(all_selected):
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        try:
            browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        except Exception as e:  # no browser installed in this environment
            pytest.skip(f"chromium unavailable: {e}")
        page = await browser.new_page()
        await page.set_content(PAGE.format(
            all_selected=str(all_selected).lower(),
            unread_selected=str(not all_selected).lower(),
        ))
        assert await page.evaluate("document.getElementById('pane-side').scrollTop") > 0
        await ChatManager._reset_chat_list(SimpleNamespace(_page=page))
        state = await page.evaluate("""() => ({
            top: document.getElementById('pane-side').scrollTop,
            all: document.getElementById('all-filter').getAttribute('aria-selected'),
            clicks: window.clicks,
        })""")
        await browser.close()
    return state


@pytest.mark.asyncio
async def test_scrolled_list_goes_back_to_the_top():
    state = await _run(all_selected=True)
    assert state["top"] == 0
    assert state["clicks"] == 0  # "All" was already selected: no click


@pytest.mark.asyncio
async def test_other_filter_switches_to_all():
    state = await _run(all_selected=False)
    assert state["all"] == "true"
    assert state["clicks"] == 1
    assert state["top"] == 0
