import six


__all__ = ['filter_retval']


# Thumbor 7.0+ requires filters to return an async_generator; by adding
# ``return filter_retval()`` to the end of our filters, we can achieve
# compatibility with Python 2 + Thumbor < 7 and Python 3 + Thumbor 7+
def filter_retval():
    pass


if six.PY3:
    exec("async def filter_retval(): pass")
