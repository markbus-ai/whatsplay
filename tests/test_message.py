"""Tests for message.py — selector refactoring (fix-fragile-selectors).

Follows project patterns: pytest + unittest.mock (AsyncMock).
Tests are async when mocking Playwright interactions.
Pure function tests are synchronous (no mocks needed).
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


# ============================================================
# Pure function: parse_timestamp (Phase 1.1)
# ============================================================

def test_parse_timestamp_returns_datetime_for_valid_hhmm():
    from whatsplay.object.message import parse_timestamp
    result = parse_timestamp("[10:30] John Doe: Hello")
    assert result is not None
    assert result.hour == 10
    assert result.minute == 30
    assert result.second == 0


def test_parse_timestamp_with_seconds():
    from whatsplay.object.message import parse_timestamp
    result = parse_timestamp("[10:30:45] John: Hello")
    assert result is not None
    assert result.hour == 10
    assert result.minute == 30
    assert result.second == 0  # We ignore seconds


def test_parse_timestamp_single_digit_hour():
    from whatsplay.object.message import parse_timestamp
    result = parse_timestamp("[8:05] Maria: Hola")
    assert result is not None
    assert result.hour == 8
    assert result.minute == 5


def test_parse_timestamp_midnight():
    from whatsplay.object.message import parse_timestamp
    result = parse_timestamp("[00:00] System: reset")
    assert result is not None
    assert result.hour == 0
    assert result.minute == 0


def test_parse_timestamp_invalid_format_returns_none():
    from whatsplay.object.message import parse_timestamp
    result = parse_timestamp("no brackets here")
    assert result is None


def test_parse_timestamp_empty_string_returns_none():
    from whatsplay.object.message import parse_timestamp
    result = parse_timestamp("")
    assert result is None


def test_parse_timestamp_no_bracket_prefix_returns_none():
    from whatsplay.object.message import parse_timestamp
    result = parse_timestamp("10:30] John: Hello")
    assert result is None


def test_parse_timestamp_no_closing_bracket_returns_none():
    from whatsplay.object.message import parse_timestamp
    result = parse_timestamp("[10:30 John: Hello")
    assert result is None


# ============================================================
# Pure function: _format_duration (Phase 2.1)
# ============================================================

def test_format_duration_seconds():
    from whatsplay.object.message import _format_duration
    result = _format_duration(65.5)
    assert result == "01:05"


def test_format_duration_zero():
    from whatsplay.object.message import _format_duration
    result = _format_duration(0)
    assert result == "00:00"


def test_format_duration_exact_minute():
    from whatsplay.object.message import _format_duration
    result = _format_duration(120)
    assert result == "02:00"


def test_format_duration_single_digit():
    from whatsplay.object.message import _format_duration
    result = _format_duration(5)
    assert result == "00:05"


def test_format_duration_negative_returns_empty():
    from whatsplay.object.message import _format_duration
    result = _format_duration(-1)
    assert result == ""


def test_format_duration_none_returns_empty():
    from whatsplay.object.message import _format_duration
    result = _format_duration(None)
    assert result == ""


def test_format_duration_string_returns_empty():
    from whatsplay.object.message import _format_duration
    result = _format_duration("invalid")
    assert result == ""


# ============================================================
# Message.from_element — timestamp via data-pre-plain-text (Phase 1.2)
# ============================================================

@pytest.mark.asyncio
async def test_message_timestamp_from_data_pre_plain_text():
    """Timestamp is parsed from data-pre-plain-text, not from xpath span."""
    from whatsplay.object.message import Message
    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "msg-1",
        "data-testid": "conv-msg-AC-test",
    }.get(attr)

    pre_plain = AsyncMock()
    pre_plain.get_attribute.return_value = "[14:30] Juan Perez: "
    selectable = AsyncMock()
    selectable.inner_text.return_value = "Hola"

    async def query_selector(selector):
        if "[data-pre-plain-text]" in selector:
            return pre_plain
        if '[data-testid="selectable-text"]' in selector:
            return selectable
        return None

    elem.query_selector = query_selector

    msg = await Message.from_element(elem, page)
    assert msg is not None
    assert msg.timestamp.hour == 14
    assert msg.timestamp.minute == 30
    assert msg.sender == "Juan Perez"
    assert msg.text == "Hola"


@pytest.mark.asyncio
async def test_message_timestamp_defaults_to_now_when_no_pre_plain():
    """When data-pre-plain-text is absent, timestamp defaults to datetime.now()."""
    from whatsplay.object.message import Message
    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "msg-2",
        "data-testid": "conv-msg-AC-test",
    }.get(attr)

    selectable = AsyncMock()
    selectable.inner_text.return_value = "Hello"

    async def query_selector(selector):
        if '[data-testid="selectable-text"]' in selector:
            return selectable
        return None

    elem.query_selector = query_selector

    before = datetime.now()
    msg = await Message.from_element(elem, page)
    after = datetime.now()
    assert msg is not None
    # Timestamp should be close to now (within a few seconds)
    assert before.timestamp() - 1 <= msg.timestamp.timestamp() <= after.timestamp() + 1


# ============================================================
# Message.from_element — text extraction (Phase 4)
# ============================================================

@pytest.mark.asyncio
async def test_message_text_from_selectable_text():
    """Text is extracted from [data-testid="selectable-text"] when present."""
    from whatsplay.object.message import Message
    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "msg-3",
        "data-testid": "conv-msg-AC-test",
    }.get(attr)

    pre_plain = AsyncMock()
    pre_plain.get_attribute.return_value = "[10:00] Ana: "

    selectable = AsyncMock()
    selectable.inner_text.return_value = "Hola, ¿cómo estás?"

    async def query_selector(selector):
        if "[data-pre-plain-text]" in selector:
            return pre_plain
        if '[data-testid="selectable-text"]' in selector:
            return selectable
        return None

    elem.query_selector = query_selector

    msg = await Message.from_element(elem, page)
    assert msg is not None
    assert msg.text == "Hola, ¿cómo estás?"


@pytest.mark.asyncio
async def test_message_text_empty_when_no_selectable_text():
    """Text is empty string when no selectable-text is found (no fallback)."""
    from whatsplay.object.message import Message
    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "msg-4",
        "data-testid": "conv-msg-AC-test",
    }.get(attr)

    pre_plain = AsyncMock()
    pre_plain.get_attribute.return_value = "[10:00] Ana: "

    async def query_selector(selector):
        if "[data-pre-plain-text]" in selector:
            return pre_plain
        return None

    elem.query_selector = query_selector

    msg = await Message.from_element(elem, page)
    assert msg is not None
    assert msg.text == ""


# ============================================================
# VoiceMessage.from_element — duration via audio.duration (Phase 2.2)
# ============================================================

@pytest.mark.asyncio
async def test_voice_message_duration_from_audio_element():
    """Voice duration is extracted from inner <audio>.duration via evaluate."""
    from whatsplay.object.message import VoiceMessage
    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "voice-1",
        "data-testid": "conv-msg-AC-test",
    }.get(attr)

    # Voice message detection checks
    play_button = AsyncMock()
    pre_plain = AsyncMock()
    pre_plain.get_attribute.return_value = "[10:00] Voice: "
    selectable = AsyncMock()
    selectable.inner_text.return_value = ""

    async def query_selector(selector):
        if '[aria-label="Reproducir mensaje de voz"]' in selector:
            return play_button
        if "[data-pre-plain-text]" in selector:
            return pre_plain
        if '[data-testid="selectable-text"]' in selector:
            return selectable
        return None

    elem.query_selector = query_selector
    # Return 65 seconds from audio.duration
    elem.evaluate = AsyncMock(return_value=65.0)

    msg = await VoiceMessage.from_element(elem, page)
    assert msg is not None
    assert msg.duration == "01:05"


@pytest.mark.asyncio
async def test_voice_message_duration_empty_when_no_audio():
    """Duration is empty string when no audio element is found."""
    from whatsplay.object.message import VoiceMessage
    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "voice-2",
        "data-testid": "conv-msg-AC-test",
    }.get(attr)

    play_button = AsyncMock()
    pre_plain = AsyncMock()
    pre_plain.get_attribute.return_value = "[10:00] Voice: "
    selectable = AsyncMock()
    selectable.inner_text.return_value = ""

    async def query_selector(selector):
        if 'voz' in selector and 'button' in selector:
            return play_button
        if "[data-pre-plain-text]" in selector:
            return pre_plain
        if '[data-testid="selectable-text"]' in selector:
            return selectable
        return None

    elem.query_selector = query_selector
    # No audio element found → falls to slider check → also None → duration stays ""
    elem.evaluate = AsyncMock(return_value=None)

    msg = await VoiceMessage.from_element(elem, page)
    assert msg is not None
    assert msg.duration == ""


@pytest.mark.asyncio
async def test_voice_message_duration_rounds_correctly():
    """Duration rounds to nearest second."""
    from whatsplay.object.message import VoiceMessage
    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "voice-3",
        "data-testid": "conv-msg-AC-test",
    }.get(attr)

    play_button = AsyncMock()
    pre_plain = AsyncMock()
    pre_plain.get_attribute.return_value = "[10:00] Voice: "
    selectable = AsyncMock()
    selectable.inner_text.return_value = ""

    async def query_selector(selector):
        if '[aria-label="Reproducir mensaje de voz"]' in selector:
            return play_button
        if "[data-pre-plain-text]" in selector:
            return pre_plain
        if '[data-testid="selectable-text"]' in selector:
            return selectable
        return None

    elem.query_selector = query_selector
    # 187.7 seconds = 3:07.7 → 03:07
    elem.evaluate = AsyncMock(return_value=187.7)

    msg = await VoiceMessage.from_element(elem, page)
    assert msg is not None
    assert msg.duration == "03:07"


# ============================================================
# VoiceMessage.download_via_context_menu — structural selector (Phase 3)
# ============================================================

@pytest.mark.asyncio
async def test_context_menu_logs_warning_when_no_target(caplog):
    """Context menu method logs warning when both selectors fail."""
    from whatsplay.object.message import VoiceMessage
    import logging
    caplog.set_level(logging.WARNING)

    page = AsyncMock()
    elem = AsyncMock()
    elem.get_attribute.side_effect = lambda attr: {
        "data-id": "voice-ctx-1",
        "data-testid": "conv-msg-AC-test",
    }.get(attr)

    play_button = AsyncMock()
    pre_plain = AsyncMock()
    pre_plain.get_attribute.return_value = "[10:00] Voice: "
    selectable = AsyncMock()
    selectable.inner_text.return_value = ""

    async def query_selector(selector):
        if 'voz' in selector and 'button' in selector:
            return play_button
        if "[data-pre-plain-text]" in selector:
            return pre_plain
        if '[data-testid="selectable-text"]' in selector:
            return selectable
        return None

    elem.query_selector = query_selector
    elem.evaluate = AsyncMock(return_value=None)

    msg = await VoiceMessage.from_element(elem, page)
    assert msg is not None

    # The context-menu evaluate returns False (no target found) → graceful fail
    page.evaluate = AsyncMock(return_value=False)
    # expect_download must return a context manager synchronously (no coroutine wrapper).
    # Use MagicMock for the callable, AsyncMock for __aenter__/__aexit__ awaitables.
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__.return_value = MagicMock()
    ctx_mgr.__aexit__.return_value = None
    page.expect_download = MagicMock(return_value=ctx_mgr)

    result = await msg.download_via_context_menu(page, MagicMock())
    assert result is None
    # Verify warning was actually logged
    assert "no target element found" in caplog.text
