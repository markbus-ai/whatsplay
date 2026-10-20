"""Every page operation is serialized by one re-entrant lock."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from whatsplay.client import Client
from whatsplay.page_lock import ReentrantLock


@pytest.mark.asyncio
async def test_the_same_task_can_reenter():
    lock = ReentrantLock()
    async with lock:
        async with lock:  # e.g. send_message -> open() while already locked
            assert lock.locked()
    assert not lock.locked()


@pytest.mark.asyncio
async def test_other_tasks_wait_for_the_owner():
    lock = ReentrantLock()
    order = []

    async def owner():
        async with lock:
            order.append("owner-in")
            await asyncio.sleep(0.05)
            order.append("owner-out")

    async def other():
        await asyncio.sleep(0.01)
        async with lock:
            order.append("other-in")

    await asyncio.gather(owner(), other())

    assert order == ["owner-in", "owner-out", "other-in"]


@pytest.mark.asyncio
async def test_lock_is_released_when_the_body_raises():
    lock = ReentrantLock()
    with pytest.raises(RuntimeError):
        async with lock:
            raise RuntimeError("boom")
    assert not lock.locked()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method, args",
    [
        ("open", ("Cliente",)),
        ("collect_messages", ()),
        ("search_conversations", ("Cliente",)),
        ("react_to_last_message", ("👍",)),
        ("close", ()),
    ],
)
async def test_public_page_operations_hold_the_page_lock(method, args):
    client = Client()
    seen = {}

    async def record(*_a, **_k):
        seen["locked"] = client.page_lock.locked()
        return True

    client.chat_manager = AsyncMock()
    setattr(client.chat_manager, method, record)

    await getattr(client, method)(*args)

    assert seen["locked"] is True
    assert not client.page_lock.locked()


@pytest.mark.asyncio
async def test_refresh_reloads_under_the_page_lock_and_rereads_state():
    from unittest.mock import MagicMock

    client = Client()
    page = MagicMock()
    seen = {}

    async def reload(**_k):
        seen["locked"] = client.page_lock.locked()
        client.current_state = "stale-logged-in"  # a tick read the old DOM

    page.reload = reload
    client._page = page
    client.wait_until_logged_in = AsyncMock(return_value=True)
    client.emit = AsyncMock()

    assert await client.refresh() is True
    assert seen["locked"] is True
    assert client.current_state is None or client.current_state != "stale-logged-in"
