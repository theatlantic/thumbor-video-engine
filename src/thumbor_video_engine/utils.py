from collections import namedtuple
from contextlib import contextmanager
from decimal import Decimal
from fractions import Fraction
from io import BytesIO
import os
import shutil
from struct import error as StructError, unpack
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


class GifParseError(ValueError):
    pass


GifFrame = namedtuple("GifFrame", ["delay_cs", "transparency", "disposal"])

_DISPOSAL_RESTORE_TO_BACKGROUND = 2

# Browsers (and ffmpeg's gif demuxer) treat delays below 2cs as 10cs
MIN_EFFECTIVE_DELAY_CS = 2
DEFAULT_EFFECTIVE_DELAY_CS = 10


class GifInfo(object):
    """Animation metadata extracted from a GIF buffer by :func:`parse_gif`,
    without decoding any pixel data."""

    def __init__(self, width, height, frames, loop_count=None, truncated=False):
        self.width = width
        self.height = height
        self.frames = frames
        self.loop_count = loop_count
        self.truncated = truncated

    @property
    def frame_count(self):
        return len(self.frames)

    @property
    def total_pixels(self):
        return self.width * self.height * self.frame_count

    @property
    def delays_ms(self):
        """Raw per-frame delays in milliseconds (matches PIL's
        ``im.info['duration']`` units, with no browser clamping)."""
        return [frame.delay_cs * 10 for frame in self.frames]

    def effective_delays_cs(self):
        """Per-frame delays in centiseconds, with sub-2cs delays clamped to
        10cs to match how browsers and ffmpeg's gif demuxer render them."""
        return [
            DEFAULT_EFFECTIVE_DELAY_CS
            if frame.delay_cs < MIN_EFFECTIVE_DELAY_CS
            else frame.delay_cs
            for frame in self.frames
        ]

    @property
    def is_uniform_delay(self):
        return len(set(self.effective_delays_cs())) == 1

    @property
    def uniform_delay_cs(self):
        delays = set(self.effective_delays_cs())
        if len(delays) != 1:
            return None
        return delays.pop()

    @property
    def uniform_fps(self):
        delay_cs = self.uniform_delay_cs
        if delay_cs is None:
            return None
        return Fraction(100, delay_cs)

    @property
    def duration(self):
        """Total duration of one loop of the animation, in seconds."""
        return Decimal(sum(self.effective_delays_cs())) / Decimal(100)

    @property
    def has_transparency_flags(self):
        return any(frame.transparency for frame in self.frames)

    @property
    def has_transparent_disposal(self):
        """True if any frame combines a transparency flag with
        restore-to-background disposal, which can expose the transparent
        background mid-animation even when frame 0 is opaque."""
        return any(
            frame.transparency
            and frame.disposal == _DISPOSAL_RESTORE_TO_BACKGROUND
            for frame in self.frames
        )


def _i16(data, offset=0):
    """Little-endian uint16, mirroring the ``i16le`` helper that
    ``PIL.GifImagePlugin`` uses (aliased there as ``i16``)."""
    return unpack("<H", data[offset:offset + 2])[0]


class _GifMetadataReader(object):
    """A metadata-only re-implementation of the block walk in Pillow's
    ``PIL.GifImagePlugin.GifImageFile`` (its ``_open`` and ``_seek`` methods),
    stripped of everything that decodes pixels, builds palettes, or composites
    frames.

    It reads through a file-like object with ``fp.read()`` exactly as Pillow
    does -- same block dispatch, same field offsets, same sub-block reader --
    so its correctness can be checked directly against the Pillow source. The
    only intentional differences from ``_seek`` are:

    * image-data sub-blocks are consumed eagerly (Pillow defers them to the
      next seek), because we never decode a frame; and
    * reaching the end of the buffer without a trailer byte sets ``truncated``
      rather than raising, because callers use this at load time to decide
      whether to reject the image (a 400) instead of erroring (a 500).

    As in Pillow, ``disposal`` is carried across frames: a frame whose Graphic
    Control Extension gives disposal 0 (unspecified) inherits the previous
    frame's method.
    """

    def __init__(self, fp):
        self.fp = fp
        self.width = 0
        self.height = 0
        self.frames = []
        self.loop_count = None
        self.disposal_method = 0
        self.truncated = False
        self._open()

    def data(self):
        # PIL.GifImagePlugin.GifImageFile.data: read one length-prefixed
        # sub-block, or None at the block terminator.
        s = self.fp.read(1)
        if s and s[0]:
            return self.fp.read(s[0])
        return None

    def _open(self):
        # Logical screen descriptor (cf. GifImageFile._open)
        header = self.fp.read(13)
        if not header.startswith((b"GIF87a", b"GIF89a")):
            raise GifParseError("buffer is not a GIF")
        if len(header) < 13:
            raise GifParseError("truncated GIF header")
        self.width = _i16(header, 6)
        self.height = _i16(header, 8)
        flags = header[10]
        if flags & 0x80:
            # skip the global color table
            self.fp.read(3 << ((flags & 7) + 1))

    def _read_frame(self):
        # Mirrors the block loop in GifImageFile._seek, returning one GifFrame
        # per image descriptor. Returns None at the trailer or end of the
        # buffer; sets self.truncated if the buffer ends without a trailer.
        duration_cs = 0
        transparency = None

        s = self.fp.read(1)
        if not s:
            self.truncated = True
            return None
        if s == b";":
            return None

        while True:
            if not s:
                s = self.fp.read(1)
            if not s:
                self.truncated = True
                return None
            if s == b";":
                # trailer reached before this frame's image descriptor
                return None

            if s == b"!":
                #
                # extension
                #
                label = self.fp.read(1)
                block = self.data()
                if label and label[0] == 0xF9 and block is not None:
                    #
                    # graphic control extension
                    #
                    flags = block[0]
                    if flags & 0x01:
                        transparency = block[3]
                    duration_cs = _i16(block, 1)
                    # disposal method - bits 2-4 of the packed flags
                    dispose_bits = (0b00011100 & flags) >> 2
                    if dispose_bits:
                        # only set the dispose if it is not unspecified,
                        # carrying the previous method forward otherwise (as
                        # Pillow does)
                        self.disposal_method = dispose_bits
                elif (
                    label
                    and label[0] == 0xFF
                    and block is not None
                    and not self.frames
                    and block.startswith((b"NETSCAPE2.0", b"ANIMEXTS1.0"))
                ):
                    #
                    # application extension: loop count. Pillow reads only
                    # NETSCAPE2.0; ANIMEXTS1.0 is a byte-identical variant.
                    #
                    block = self.data()
                    if block and len(block) >= 3 and block[0] == 1:
                        self.loop_count = _i16(block, 1)
                # drain any remaining sub-blocks of this extension. The first
                # sub-block was already read into ``block``; if it was None the
                # block terminator has been consumed (e.g. a zero-sub-block
                # comment), so stop rather than reading into the next block.
                while block is not None:
                    block = self.data()

            elif s == b",":
                #
                # local image
                #
                descriptor = self.fp.read(9)
                flags = descriptor[8]
                if flags & 0x80:
                    # skip the local color table
                    self.fp.read(3 << ((flags & 7) + 1))
                self.fp.read(1)  # LZW minimum code size
                while self.data():  # image data sub-blocks
                    pass
                return GifFrame(
                    delay_cs=duration_cs,
                    transparency=transparency is not None,
                    disposal=self.disposal_method,
                )
            s = b""

    def parse(self):
        while True:
            try:
                frame = self._read_frame()
            except (IndexError, StructError):
                # a field or sub-block ran past the end of the buffer
                self.truncated = True
                break
            if frame is None:
                break
            self.frames.append(frame)
        return self


def parse_gif(buffer):
    """Parse ``buffer`` and return a :class:`GifInfo` describing its animation
    metadata (per-frame delays, transparency and disposal flags,
    NETSCAPE/ANIMEXTS loop count, and logical screen size).

    This walks the GIF block structure without decoding any pixel data --
    unlike iterating frames with PIL, which materializes every full-resolution
    frame canvas just to read header fields. The walk is patterned directly on
    the block dispatch in Pillow's :class:`PIL.GifImagePlugin.GifImageFile`
    (see :class:`_GifMetadataReader`).

    Raises :class:`GifParseError` if the buffer is not a GIF or contains no
    frames. A GIF that ends abruptly (without a trailer byte) is returned with
    ``truncated=True`` as long as at least one frame was parsed.
    """
    reader = _GifMetadataReader(BytesIO(buffer)).parse()
    if not reader.frames:
        raise GifParseError("no frames found in GIF")
    return GifInfo(
        width=reader.width,
        height=reader.height,
        frames=reader.frames,
        loop_count=reader.loop_count,
        truncated=reader.truncated,
    )
