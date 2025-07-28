"""
Base classes for creating custom filters.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable


class Filter(ABC):
    """
    Abstract base class for all filters.
    """

    @abstractmethod
    def test(self, value: Any) -> bool:
        """
        This method should be overridden in subclasses.
        It takes a value and returns True if the value passes the filter, False otherwise.
        """
        raise NotImplementedError

    def __call__(self, value: Any) -> bool:
        return self.test(value)


class CustomFilter(Filter):
    """
    A filter that uses a custom function to test values.
    """

    def __init__(self, func: Callable[[Any], bool]):
        self.func = func

    def test(self, value: Any) -> bool:
        return self.func(value)
