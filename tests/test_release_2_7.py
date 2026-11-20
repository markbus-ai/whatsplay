"""2.7.0: group message ids, and chat filters in the 2026-11-20 production
markup (toggle chips with an exact <span title>, a count on "No leídos")."""

import os

import pytest

from whatsplay.chat_manager import ChatManager
from whatsplay.object.message import Message, _bare_msg_id, _model_bubbles, _model_text, _text_key
from whatsplay.wa_elements import WhatsAppElements

GROUP_ID = "false_120363000000000000@g.us_IMG2_5491122334455@c.us"

STUB = """<script>
const models = [
  {id: {id: 'IMG2'}, type: 'image', body: '/9j/4AAQSkZJRg', caption: 'la de la foto'},
  {id: {id: 'TXT1'}, type: 'chat', body: 'Bicicleta rodado 29 aluminio'},
];
window.require = (name) => {
  if (name !== 'WAWebCollections') throw new Error('unknown module');
  return {Msg: {get: () => undefined, getModelsArray: () => models}};
};
</script>"""


@pytest.mark.parametrize("data_id, bare", [
    ("IMG1", "IMG1"),
    ("false_1@lid_TXT1", "TXT1"),
    ("true_5491122334455@c.us_3EB0ABCD", "3EB0ABCD"),
    (GROUP_ID, "IMG2"),
])
def test_bare_id_is_the_message_segment(data_id, bare):
    assert _bare_msg_id(data_id) == bare


def test_a_group_message_gets_its_kind():
    msg = Message(page=None, sender="x", timestamp=None, text="", container=None, msg_id=GROUP_ID)
    ChatManager._attach_kinds([msg], {"IMG2": "image"})
    assert msg.kind == "image"


async def _browser(p):
    try:
        return await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
    except Exception as e:  # no browser installed in this environment
        pytest.skip(f"chromium unavailable: {e}")


@pytest.mark.asyncio
async def test_group_bubbles_are_found_in_the_model():
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        browser = await _browser(p)
        page = await browser.new_page()
        await page.set_content(STUB + f'<div data-testid="conv-msg-1" data-id="{GROUP_ID}"></div>')
        texts, kinds = await _model_bubbles(page)
        single = await _model_text(page, "false_120363@g.us_TXT1_5491122334455@c.us")
        await browser.close()
    assert kinds == {"IMG2": "image"}  # the kind of a group message is read
    assert texts == {"IMG2": "la de la foto"}
    assert single is None  # this stub's Msg.get never resolves a full id


def _chip(key, title, pressed="false", extra="", attrs=""):
    return (f'<button aria-pressed="{pressed}" data-k="{key}" {attrs} onclick="press(this)">'
            f'<span title="{title}">{title}</span>{extra}</button>')


PROD_ROW = (_chip("all", "Todos", "true", attrs='id="all-filter"')
            + _chip("unread", "No leídos", extra="2", attrs='id="label_item_1"')
            + _chip("favs", "Favoritos", attrs='id="label_item_2"')
            + _chip("groups", "Grupos", attrs='id="label_item_3"'))


async def _filter(html, kind):
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        browser = await _browser(p)
        page = await browser.new_page()
        await page.set_content(
            "<script>window.clicked = []; function press(b) { window.clicked.push(b.dataset.k);"
            " b.setAttribute('aria-pressed', 'true'); }</script>" + html)
        ok = await WhatsAppElements(page).click_chat_filter(kind)
        clicked = await page.evaluate("window.clicked")
        await browser.close()
    return ok, clicked


@pytest.mark.asyncio
@pytest.mark.parametrize("kind, clicked", [("unread", ["unread"]), ("groups", ["groups"]), ("all", [])])
async def test_production_filter_row(kind, clicked):
    """The unread chip shows a count ("No leídos2"); "Todos" is already pressed."""
    assert await _filter(PROD_ROW, kind) == (True, clicked)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["unread", "groups"])
async def test_english_chips(kind):
    html = _chip("calls", "Calls") + _chip("unread", "Unread", extra="3") + _chip("groups", "Groups")
    assert await _filter(html, kind) == (True, [kind])


@pytest.mark.asyncio
async def test_all_without_id_never_takes_calls():
    html = _chip("calls", "Calls") + '<button aria-pressed="false" data-k="all" onclick="press(this)">All</button>'
    assert await _filter(html, "all") == (True, ["all"])


@pytest.mark.asyncio
async def test_late_rendered_pressed_all_is_not_clicked_by_the_fallback():
    html = ("<div id='row'></div><script>setTimeout(() => { document.getElementById('row').innerHTML = "
            + repr(_chip("all", "Todos", "true", attrs='id="all-filter"')) + "; }, 600);</script>")
    assert await _filter(html, "all") == (True, [])


@pytest.mark.asyncio
async def test_english_dropdown_item_is_selected():
    html = ('<button id="additional-filters" onclick="document.getElementById(\'m\').hidden=false">More</button>'
            '<div id="m" role="menu" hidden><button role="menuitem" data-k="all" '
            'onclick="press(this); this.parentNode.hidden=true">All</button></div>')
    assert await _filter(html, "all") == (True, ["all"])


@pytest.mark.parametrize("data_id, key", [
    ("false_1@lid_TXT1", "TXT1"),
    ("true_120363@g.us_3EB0ABC", "3EB0ABC"),     # own group message: model text, as in 2.6.x
    (GROUP_ID, "5491122334455@c.us"),            # another member: no model match, page text
])
def test_text_keys_are_the_same_as_2_6(data_id, key):
    """Texts are read exactly as in 2.6.x; only kinds use the real message id."""
    assert _text_key(data_id) == key


@pytest.mark.asyncio
async def test_chip_without_title_span_but_with_a_count_is_found():
    html = (_chip("all", "Todos", "true", attrs='id="all-filter"')
            + '<button aria-pressed="false" data-k="unread" onclick="press(this)">'
              '<span>No leídos</span><span>2</span></button>')
    assert await _filter(html, "unread") == (True, ["unread"])


FULL_ID_STUB = """<script>
const byId = {'false_1@g.us_TXT1_549@c.us': {id: {id: 'TXT1'}, type: 'chat', body: 'mi pregunta'}};
window.require = (name) => ({Msg: {get: (id) => byId[id],
  getModelsArray: () => [{id: {id: 'TXT1'}, type: 'chat', body: 'mi pregunta'}]}});
</script>"""


@pytest.mark.asyncio
async def test_single_lookup_still_finds_a_group_message_by_its_full_id():
    """As in 2.6.x: Msg.get(full id) resolves a group message; only the bare-id
    fallback is skipped for groups."""
    async_api = pytest.importorskip("playwright.async_api")
    async with async_api.async_playwright() as p:
        browser = await _browser(p)
        page = await browser.new_page()
        await page.set_content(FULL_ID_STUB)
        by_full_id = await _model_text(page, "false_1@g.us_TXT1_549@c.us")
        other = await _model_text(page, "false_1@g.us_TXT1_999@c.us")
        await browser.close()
    assert by_full_id == "mi pregunta"
    assert other is None

