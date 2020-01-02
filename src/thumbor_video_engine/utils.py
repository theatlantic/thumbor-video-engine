from contextlib import contextmanager
import os
import shutil
from tempfile import NamedTemporaryFile, mkdtemp


@contextmanager
def named_tmp_file(data=None, extension=None, **kwargs):
    kwargs.setdefault('delete', False)
    if extension is not None:
        kwargs.setdefault('suffix', extension)
    f = NamedTemporaryFile(**kwargs)
    try:
        if data:
            f.write(data)
        f.close()
        yield f.name
    finally:
        os.unlink(f.name)


@contextmanager
def make_tmp_dir():
    try:
        tmp_dir = mkdtemp()
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
