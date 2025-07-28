"""
Event handling system implementation
"""

from typing import Any, Callable, List, Dict, Optional, Tuple
from ..filters import Filter


class Event:
    """
    Represents a single event type that can have multiple listeners
    """

    def __init__(self) -> None:
        self.__listeners: List[Tuple[Callable, Optional[Filter]]] = []

    def register_listener(
        self, func: Callable, filter_obj: Optional[Filter] = None
    ) -> Callable:
        """Register a new event listener"""
        self.add_listener(func, filter_obj)
        return func

    def add_listener(self, func: Callable, filter_obj: Optional[Filter] = None) -> None:
        """Add a listener if it's not already registered"""
        self.__listeners.append((func, filter_obj))

    async def emit(self, *args: Any, **kwargs: Any) -> None:
        """Emit event to all listeners"""
        for listener, filter_obj in self.__listeners:
            if not filter_obj:
                await listener(*args, **kwargs)
                continue

            # We assume the filter is for the first argument, which is a list of chats
            if not args or not isinstance(args[0], list):
                continue

            filtered_args = [arg for arg in args[0] if filter_obj.test(arg)]
            if filtered_args:
                await listener(filtered_args, *args[1:], **kwargs)


class EventHandler:
    """
    Base class for handling events
    """

    def __init__(self, events: Optional[List[str]] = None) -> None:
        self._events: Dict[str, Event] = {}
        if events:
            for event in events:
                self._events[event] = Event()

    def event(self, name: str, filter_obj: Optional[Filter] = None) -> Callable:
        """Register an event handler"""

        def decorator(func: Callable) -> Callable:
            if name not in self._events:
                self._events[name] = Event()
            self._events[name].register_listener(func, filter_obj)
            return func

        return decorator

    async def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all registered listeners"""
        if event in self._events:
            await self._events[event].emit(*args, **kwargs)
