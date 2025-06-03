"""
Event handling system implementation
"""
from typing import Any, Callable, List, Dict, Optional


class Event:
    """
    Represents a single event type that can have multiple listeners
    """
    def __init__(self) -> None:
        self.__listeners: List[Callable] = []

    def register_listener(self, func: Callable) -> Callable:
        """Register a new event listener"""
        self.add_listener(func)
        return func

    def add_listener(self, func: Callable) -> None:
        """Add a listener if it's not already registered"""
        if func not in self.__listeners:
            self.__listeners.append(func)

    async def emit(self, *args: Any, **kwargs: Any) -> None:
        """Emit event to all listeners"""
        for listener in self.__listeners:
            await listener(*args, **kwargs)


class EventHandler:
    """
    Base class for handling events
    """
    def __init__(self, events: Optional[List[str]] = None) -> None:
        self._events: Dict[str, Event] = {}
        if events:
            for event in events:
                self._events[event] = Event()

    def event(self, name: str) -> Callable:
        """Register an event handler"""
        if name not in self._events:
            self._events[name] = Event()
        return self._events[name].register_listener

    async def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all registered listeners"""
        if event in self._events:
            await self._events[event].emit(*args, **kwargs)
