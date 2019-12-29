from contextlib import contextmanager
import os
from tempfile import NamedTemporaryFile


@contextmanager
def named_tmp_file(data=None, **kwargs):
    kwargs.setdefault('delete', False)
    try:
        f = NamedTemporaryFile(**kwargs)
        if data:
            f.write(data)
        f.close()
        yield f.name
    finally:
        os.unlink(f.name)
