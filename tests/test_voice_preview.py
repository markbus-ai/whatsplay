"""The unread scan must recognise a voice-note preview in the chat list."""

import os

import pytest

from whatsplay.constants import locator as loc

CURRENT = """<div id="row"><div data-testid="cell-frame-secondary"><span>
  <svg viewBox="0 0 24 24"><title>ic-keyboard-voice-filled</title><path d=""/></svg>
  <span>0:12</span></span></div></div>"""
LEGACY = """<div id="row"><span data-icon="mic"></span><span>0:12</span></div>"""
TEXT = """<div id="row"><svg><title>wds-ic-read</title></svg><span>hola</span></div>"""


@pytest.mark.asyncio
@pytest.mark.parametrize("html, is_voice", [(CURRENT, True), (LEGACY, True), (TEXT, False)])
async def test_voice_icon_in_the_chat_list_preview(html, is_voice):
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        try:
            browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        except Exception as e:  # no browser installed in this environment
            pytest.skip(f"chromium unavailable: {e}")
        page = await browser.new_page()
        await page.set_content(html)
        row = await page.query_selector("#row")
        found = await row.query_selector(loc.CHAT_LIST_VOICE_ICON)
        await browser.close()
    assert (found is not None) is is_voice
