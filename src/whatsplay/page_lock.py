"""
Re-entrant lock serializing every operation on the WhatsApp Web page.

All public page operations take it, so a background scan can never click or
press keys in the middle of another operation. It is re-entrant per asyncio
task: send_message() already holds it when it calls open(), and event
handlers that run while it is held may call back into the client.
"""

import asyncio
from typing import Optional


class ReentrantLock:
    """An asyncio lock that the owning task can acquire more than once."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._owner: Optional[asyncio.Task] = None
        self._depth = 0

    def locked(self) -> bool:
        return self._lock.locked()

    async def acquire(self) -> None:
        task = asyncio.current_task()
        if self._owner is task:
            self._depth += 1
            return
        await self._lock.acquire()
        self._owner = task
        self._depth = 1

    def release(self) -> None:
        if self._owner is not asyncio.current_task():
            raise RuntimeError("ReentrantLock released by a task that does not own it")
        self._depth -= 1
        if self._depth == 0:
            self._owner = None
            self._lock.release()

    async def __aenter__(self) -> "ReentrantLock":
        await self.acquire()
        return self

    async def __aexit__(self, *exc) -> None:
        self.release()
