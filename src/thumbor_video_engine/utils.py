from contextlib import contextmanager
import os
import shutil
from struct import unpack
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


def is_mp4(buf):
    if buf[4:8] != b'ftyp':
        return False
    (ftyp_box_len,) = unpack('>L', buf[:4])
    if not (20 <= ftyp_box_len <= 256) or (ftyp_box_len % 4) != 0:
        return False
    major_brand = unpack('4s', buf[8:12])
    compat_brand_len = ftyp_box_len - 16
    fmt = '4s' * (compat_brand_len // 4)
    compat_brands = unpack(fmt, buf[16:ftyp_box_len])
    all_brands = set(major_brand + compat_brands)
    return bool(all_brands & {b'isom', b'avc1', b'iso2', b'mp41', b'mp42'})


def has_transparency(im):
    if 'A' in im.mode or 'transparency' in im.info:
        # If the image has alpha channel, we check for any pixels that are not opaque (255)
        return min(im.convert('RGBA').getchannel('A').getextrema()) < 255
    else:
        return False
