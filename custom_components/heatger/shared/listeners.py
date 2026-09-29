"""Small helper to notify listeners (sync callbacks or coroutines)"""
import inspect
import logging
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)


class Listeners:
    """A list of callbacks, each one can be sync or async"""

    def __init__(self):
        self._callbacks: list[Callable[[], Any]] = []

    def add(self, callback: Callable[[], Any]) -> Callable[[], None]:
        """add a callback, return a function removing it"""
        self._callbacks.append(callback)

        def remove() -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
        return remove

    async def notify(self) -> None:
        """call every callback"""
        for callback in list(self._callbacks):
            try:
                result = callback()
                if inspect.isawaitable(result):
                    await result
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception('Error in a Heatger listener')
