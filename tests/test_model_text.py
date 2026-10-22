"""Message text comes from WhatsApp's own message model when it is loaded.

The DOM only exposes the first selectable-text node: an image caption is not
one (the bubble read as empty) and in a reply it is the quoted message (the
bubble read as the quoted text). Prod 2026-10-21.
"""

import os
from unittest.mock import AsyncMock

import pytest

from whatsplay.object.message import Message, _model_text

STUB = """<script>
const models = [
  {id: {id: 'IMG1'}, type: 'image', body: '/9j/4AAQSkZJRg', caption: 'quería saber si la bici ya está para retirar ?'},
  {id: {id: 'IMG2'}, type: 'image', body: '/9j/4AAQSkZJRg', caption: undefined},
  {id: {id: 'TXT1'}, type: 'chat', body: 'Bicicleta rodado 29 aluminio', quotedStanzaID: 'Q1'},
  {id: {id: 'DOC1'}, type: 'document', body: '', caption: 'Ticket.pdf', filename: 'Ticket.pdf'},
  {id: {id: 'DOC2'}, type: 'document', body: '', caption: 'te paso el comprobante', filename: 'Ticket.pdf'},
];
window.require = (name) => {
  if (name !== 'WAWebCollections') throw new Error('unknown module');
  return {Msg: {get: () => undefined, getModelsArray: () => models}};
};
</script>"""


async def _eval(html, msg_id):
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        try:
            browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        except Exception as e:  # no browser installed in this environment
            pytest.skip(f"chromium unavailable: {e}")
        page = await browser.new_page()
        await page.set_content(html)
        result = await _model_text(page, msg_id)
        await browser.close()
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize("msg_id, expected", [
    ("IMG1", "quería saber si la bici ya está para retirar ?"),  # caption, not the thumbnail
    ("IMG2", ""),                                                  # image without caption
    ("TXT1", "Bicicleta rodado 29 aluminio"),                      # reply: own text, not the quote
    ("false_93497327620330@lid_IMG1", "quería saber si la bici ya está para retirar ?"),
    ("MISSING", None),                                             # not loaded: keep the DOM text
    ("DOC1", ""),                                                  # a document's caption is its file name
    ("DOC2", "te paso el comprobante"),                            # unless the sender wrote one
])
async def test_text_from_the_message_model(msg_id, expected):
    assert await _eval(STUB, msg_id) == expected


@pytest.mark.asyncio
async def test_without_whatsapp_modules_falls_back():
    assert await _eval("<p>no require</p>", "IMG1") is None


@pytest.mark.asyncio
async def test_from_element_prefers_the_model_text_over_the_quoted_block():
    page = AsyncMock()
    page.evaluate.return_value = "Bicicleta rodado 29 aluminio"
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "TXT1", "data-testid": "conv-msg-AC-test",
    }.get(attr)
    quoted = AsyncMock()
    quoted.inner_text.return_value = "¡Hola! ¡Bienvenido/a a Bicicletería Amigorena!"

    async def query_selector(selector):
        return quoted if "selectable-text" in selector else None

    elem.query_selector = query_selector
    msg = await Message.from_element(elem, page)
    assert msg.text == "Bicicleta rodado 29 aluminio"


@pytest.mark.asyncio
async def test_from_element_keeps_the_dom_text_when_the_model_is_missing():
    page = AsyncMock()
    page.evaluate.return_value = None
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "TXT9", "data-testid": "conv-msg-AC-test",
    }.get(attr)
    selectable = AsyncMock()
    selectable.inner_text.return_value = "Hola"

    async def query_selector(selector):
        return selectable if "selectable-text" in selector else None

    elem.query_selector = query_selector
    msg = await Message.from_element(elem, page)
    assert msg.text == "Hola"


BUBBLES = """
<div data-testid="conv-msg-1" data-id="IMG1"></div>
<div data-testid="conv-msg-2"><div data-id="false_1@lid_TXT1"></div></div>
<div data-testid="conv-msg-3" data-id="GONE"></div>
"""


@pytest.mark.asyncio
async def test_one_lookup_returns_the_texts_of_every_rendered_bubble():
    async_api = pytest.importorskip("playwright.async_api")
    from whatsplay.object.message import _model_texts
    async with async_api.async_playwright() as p:
        try:
            browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        except Exception as e:  # no browser installed in this environment
            pytest.skip(f"chromium unavailable: {e}")
        page = await browser.new_page()
        await page.set_content(STUB + BUBBLES)
        texts = await _model_texts(page)
        bare = await browser.new_page()  # a fresh window has no window.require
        await bare.set_content(BUBBLES)
        without_modules = await _model_texts(bare)
        await browser.close()
    # IMG2 is a loaded model but not rendered: not returned
    assert texts == {"IMG1": "quería saber si la bici ya está para retirar ?",
                     "TXT1": "Bicicleta rodado 29 aluminio"}
    assert without_modules is None


@pytest.mark.asyncio
@pytest.mark.parametrize("texts, expected", [
    ({"TXT1": "Bicicleta rodado 29 aluminio"}, "Bicicleta rodado 29 aluminio"),
    ({}, "¡Hola! ¡Bienvenido/a a Bicicletería Amigorena!"),  # not loaded: DOM text
])
async def test_from_element_uses_the_batch_without_querying_the_page(texts, expected):
    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "false_1@lid_TXT1", "data-testid": "conv-msg-AC-test",
    }.get(attr)
    quoted = AsyncMock()
    quoted.inner_text.return_value = "¡Hola! ¡Bienvenido/a a Bicicletería Amigorena!"

    async def query_selector(selector):
        return quoted if "selectable-text" in selector else None

    elem.query_selector = query_selector
    msg = await Message.from_element(elem, page, model_texts=texts)
    assert msg.text == expected
    page.evaluate.assert_not_awaited()
