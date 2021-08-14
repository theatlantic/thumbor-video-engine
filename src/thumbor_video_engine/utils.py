from contextlib import contextmanager
from io import BytesIO
import os
import shutil
from struct import unpack
from tempfile import NamedTemporaryFile, mkdtemp

from PIL import Image


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


def is_qt(buf):
    return buf[4:12] == b'ftypqt  '


def has_transparency(im):
    if 'A' in im.mode or 'transparency' in im.info:
        # If the image has alpha channel, we check for any pixels that are not opaque (255)
        return min(im.convert('RGBA').getchannel('A').getextrema()) < 255
    else:
        return False


def is_animated(buffer):
    im = Image.open(BytesIO(buffer))
    return getattr(im, 'is_animated', False)


def ord_compat(val):
    if isinstance(val, int):
        return val
    else:
        return ord(val)


def is_animated_gif(buffer):
    if buffer[:6] not in [b"GIF87a", b"GIF89a"]:
        return False
    i = 10  # skip header
    frames = 0

    def skip_color_table(i, flags):
        if flags & 0x80:
            i += 3 << ((flags & 7) + 1)
        return i

    flags = ord_compat(buffer[i])

    i = skip_color_table(i + 3, flags)
    while frames < 2:
        block = buffer[i]
        i += 1
        if block in (b'\x3B', 0x3B):
            break
        if block in (b'\x21', 0x21):
            i += 1
        elif block in (b'\x2C', 0x2C):
            frames += 1
            i += 8
            i = skip_color_table(i + 1, ord_compat(buffer[i]))
            i += 1
        else:
            return False
        while True:
            j = ord_compat(buffer[i])
            i += 1
            if not j:
                break
            i += j
    return frames > 1
