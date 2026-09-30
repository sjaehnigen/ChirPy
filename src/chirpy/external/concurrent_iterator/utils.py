# vim: set fileencoding=utf-8
"""Utility decorators for concurrent iterator helpers."""

from decorator import decorator


@decorator
def check_open(f, self, *args, **kwargs):
    """Ensure a consumer is still open before calling a method."""
    if self.closed:
        raise ValueError("%s operation on closed Consumer" % f.__name__)
    return f(self, *args, **kwargs)
