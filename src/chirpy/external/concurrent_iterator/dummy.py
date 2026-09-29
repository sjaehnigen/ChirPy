# vim: set fileencoding=utf-8
"""Non-concurrent producer and consumer implementations."""

from __future__ import absolute_import, division, unicode_literals

from . import IProducer, IConsumer
from .utils import check_open


class Producer(IProducer):
    """Dummy implementation that doesn't use concurrency."""

    def __init__(self, iterable, maxsize=None):
        """In this implementation, maxsize is included to ease replacing
        implementations but it's ignored.
        """
        self._iterator = iter(iterable)

    def __next__(self):
        """Return the next value from the wrapped iterator."""
        return next(self._iterator)

    def next(self):
        """Return the next value from the wrapped iterator."""
        return self.__next__()


class Consumer(IConsumer):
    """Dummy implementation that doesn't use concurrency.

    The timeout parameter is ignored, this implementation will block forever.
    """

    def __init__(self, coroutine):
        """Wrap a coroutine without adding concurrency."""
        self._coroutine = coroutine

        self._closed = False

    @check_open
    def send(self, value, timeout=0):
        """Send a value to the wrapped coroutine."""
        self._coroutine.send(value)

    @check_open
    def close(self):
        """Close the wrapped coroutine."""
        self._closed = True  # Nothing to do.
        self._coroutine.close()

    @property
    def closed(self):
        """Whether the consumer has been closed."""
        return self._closed
