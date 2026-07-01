import os
from fractions import Fraction
from io import BytesIO
from struct import pack

import pytest
from PIL import Image

from thumbor_video_engine.utils import GifFrame, GifParseError, parse_gif


def load_fixture(storage_path, name):
    with open(os.path.join(storage_path, name), mode="rb") as f:
        return f.read()


def pil_gif(frames, **save_kwargs):
    buf = BytesIO()
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:], **save_kwargs)
    return buf.getvalue()


def solid_frames(count, size=(16, 16)):
    colors = ["red", "green", "blue", "yellow", "purple", "orange"]
    return [Image.new("RGB", size, colors[i % len(colors)]) for i in range(count)]


def minimal_gif(image_blocks=1, gce=None, trailer=True):
    """Hand-assemble a GIF: optionally GCE-less frames, no color tables."""
    out = b"GIF89a" + pack("<HH", 7, 5) + b"\x00\x00\x00"
    for _ in range(image_blocks):
        if gce is not None:
            out += b"\x21\xf9\x04" + gce + b"\x00"
        out += b"\x2c" + pack("<HHHH", 0, 0, 7, 5) + b"\x00"
        out += b"\x02" + b"\x02\x4c\x01" + b"\x00"
    if trailer:
        out += b"\x3b"
    return out


def test_parses_uniform_delays_hotdog(storage_path):
    buf = load_fixture(storage_path, "hotdog.gif")
    info = parse_gif(buf)

    im = Image.open(BytesIO(buf))
    pil_durations = []
    for i in range(im.n_frames):
        im.seek(i)
        im.load()
        pil_durations.append(im.info["duration"])

    assert (info.width, info.height) == im.size == (200, 150)
    assert info.frame_count == im.n_frames == 42
    # delays cross-checked against PIL's per-frame info['duration'] (ms)
    assert info.delays_ms == pil_durations
    assert info.is_uniform_delay
    assert info.uniform_delay_cs == 3
    assert info.uniform_fps == Fraction(100, 3)
    assert not info.truncated


def test_parses_pbj_time(storage_path):
    info = parse_gif(load_fixture(storage_path, "pbj-time.gif"))
    assert (info.width, info.height) == (200, 200)
    assert info.frame_count == 8
    assert info.is_uniform_delay
    assert info.uniform_fps == Fraction(10)


def test_variable_delays():
    buf = pil_gif(solid_frames(4), duration=[300, 100, 500, 200], loop=0)
    info = parse_gif(buf)
    assert info.delays_ms == [300, 100, 500, 200]
    assert not info.is_uniform_delay
    assert info.uniform_fps is None
    assert float(info.duration) == pytest.approx(1.1)


def test_missing_gce_defaults_zero():
    info = parse_gif(minimal_gif(image_blocks=2, gce=None))
    assert info.frames == [GifFrame(0, False, 0), GifFrame(0, False, 0)]
    # zero delays clamp to the 10cs browser default, which is uniform
    assert info.effective_delays_cs() == [10, 10]
    assert info.is_uniform_delay
    assert info.uniform_fps == Fraction(10)


def test_zero_delay_clamped_to_10cs():
    # packed=0, delay=0, transparent idx=0
    gce = b"\x00" + pack("<H", 0) + b"\x00"
    info = parse_gif(minimal_gif(image_blocks=3, gce=gce))
    assert [f.delay_cs for f in info.frames] == [0, 0, 0]
    assert info.uniform_delay_cs == 10
    assert float(info.duration) == pytest.approx(0.3)


def test_loop_count_netscape():
    looped = parse_gif(pil_gif(solid_frames(2), duration=100, loop=3))
    assert looped.loop_count == 3

    infinite = parse_gif(pil_gif(solid_frames(2), duration=100, loop=0))
    assert infinite.loop_count == 0

    # No `loop` kwarg: PIL omits the NETSCAPE2.0 extension entirely
    once = parse_gif(pil_gif(solid_frames(2), duration=100))
    assert once.loop_count is None


def test_transparency_and_disposal_flags():
    # packed: transparency flag + disposal method 2, delay 10cs
    gce = bytes([0x01 | (2 << 2)]) + pack("<H", 10) + b"\x00"
    info = parse_gif(minimal_gif(image_blocks=2, gce=gce))
    assert all(f.transparency for f in info.frames)
    assert all(f.disposal == 2 for f in info.frames)
    assert info.has_transparency_flags
    assert info.has_transparent_disposal

    opaque = parse_gif(minimal_gif(image_blocks=2, gce=None))
    assert not opaque.has_transparency_flags
    assert not opaque.has_transparent_disposal


def test_logical_screen_size_and_total_pixels(storage_path):
    info = parse_gif(load_fixture(storage_path, "hotdog.gif"))
    assert info.total_pixels == 200 * 150 * 42

    small = parse_gif(minimal_gif(image_blocks=3))
    assert (small.width, small.height) == (7, 5)
    assert small.total_pixels == 7 * 5 * 3


def test_truncated_trailer_sets_flag(storage_path):
    no_trailer = parse_gif(minimal_gif(image_blocks=2, trailer=False))
    assert no_trailer.truncated
    assert no_trailer.frame_count == 2

    cut_mid_frame = parse_gif(load_fixture(storage_path, "hotdog.gif")[:-512])
    assert cut_mid_frame.truncated
    assert cut_mid_frame.frame_count >= 1


def test_non_gif_raises():
    with pytest.raises(GifParseError):
        parse_gif(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    with pytest.raises(GifParseError):
        parse_gif(b"")
    with pytest.raises(GifParseError):
        parse_gif(b"GIF89a")  # header only, no frames


def test_delays_ms_matches_pil_units():
    buf = pil_gif(solid_frames(3), duration=70, loop=0)
    info = parse_gif(buf)
    assert info.delays_ms == [70, 70, 70]


def _pil_truth(buf):
    """Ground-truth metadata as PIL decodes it, frame by frame."""
    im = Image.open(BytesIO(buf))
    durations, disposals = [], []
    for i in range(im.n_frames):
        im.seek(i)
        # PIL reports duration=None for a frame with no Graphic Control
        # Extension; the parser reports 0 there (the documented "a frame with
        # no preceding GCE defaults to delay 0" rule), so normalize None -> 0.
        durations.append(im.info.get("duration") or 0)
        disposals.append(getattr(im, "disposal_method", 0))
    return {
        "size": im.size,
        "n_frames": im.n_frames,
        "durations": durations,
        "disposals": disposals,
        "loop": im.info.get("loop"),
    }


@pytest.mark.parametrize("n", [1, 2, 5, 17])
@pytest.mark.parametrize(
    "kwargs",
    [
        {"duration": 40, "loop": 0},
        {
            "duration": [10, 20, 30, 40, 50, 60, 70][:1],
            "loop": 0,
        },  # trimmed per n below
        {"duration": 60},  # no loop extension
        {"duration": 60, "loop": 3},
        {"duration": 50, "loop": 0, "comment": b"a comment block"},
        {"duration": 70, "loop": 0, "disposal": 0},
        {"duration": 70, "loop": 0, "disposal": 1},
        {"duration": 70, "loop": 0, "disposal": 2},
        {"duration": 70, "loop": 0, "disposal": 3},
        {"duration": 70, "loop": 0, "transparency": 0},
    ],
)
def test_matches_pillow_across_matrix(n, kwargs):
    """The parser must agree with Pillow's own decode on every field where
    Pillow's decode is a stable ground truth -- logical size, frame count,
    per-frame delay, loop count, and per-frame disposal -- across a matrix of
    frame counts, delays, loop counts, disposal methods, comments, and
    transparent inputs.
    """
    kwargs = dict(kwargs)
    # per-frame varied delays, sized to the frame count
    if isinstance(kwargs["duration"], list):
        kwargs["duration"] = [10 * (k + 1) for k in range(n)]
    buf = pil_gif(solid_frames(n), **kwargs)

    info = parse_gif(buf)
    truth = _pil_truth(buf)

    assert (info.width, info.height) == truth["size"]
    assert info.frame_count == truth["n_frames"]
    assert info.delays_ms == truth["durations"]
    assert info.loop_count == truth["loop"]
    assert [f.disposal for f in info.frames] == truth["disposals"]


def test_disposal_carries_forward_like_pillow():
    # frame 0 declares disposal 2; frames 1-2 leave it unspecified (0). Like
    # Pillow, the unspecified frames inherit the last non-zero method.
    buf = pil_gif(solid_frames(3), duration=60, loop=0, disposal=[2, 0, 0])
    info = parse_gif(buf)

    assert [f.disposal for f in info.frames] == _pil_truth(buf)["disposals"]
    assert [f.disposal for f in info.frames] == [2, 2, 2]


# GIF fixtures vendored from the Pillow test suite (rights cleared). Lets us
# cross-check against PIL's own decode:
#   multiple_comments.gif             multiple comment sub-blocks in a frame
#   hopper_zero_comment_subblocks.gif a comment extension with zero sub-blocks
#   duplicate_number_of_loops.gif     a NETSCAPE loop extension repeated later
PILLOW_GIF_FIXTURES = [
    "multiple_comments.gif",
    "hopper_zero_comment_subblocks.gif",
    "duplicate_number_of_loops.gif",
]


@pytest.mark.parametrize("name", PILLOW_GIF_FIXTURES)
def test_matches_pillow_on_vendored_fixtures(storage_path, name):
    buf = load_fixture(storage_path, name)
    info = parse_gif(buf)
    truth = _pil_truth(buf)

    assert (info.width, info.height) == truth["size"]
    assert info.frame_count == truth["n_frames"]
    assert info.delays_ms == truth["durations"]
    assert info.loop_count == truth["loop"]
    assert [f.disposal for f in info.frames] == truth["disposals"]


def test_zero_comment_subblocks_does_not_swallow_frame(storage_path):
    # A comment extension whose first sub-block is the zero-length terminator
    # must not read past it into the following image (regression: the sub-block
    # drain used to consume the next block). Mirrors Pillow's
    # test_zero_comment_subblocks.
    info = parse_gif(load_fixture(storage_path, "hopper_zero_comment_subblocks.gif"))
    assert info.frame_count == 1
    assert not info.truncated


# hand-assembled GIFs for structural cases Pillow has no fixture for

# building blocks: 7x5 logical screen, no color tables, skippable image data
_HDR = b"GIF89a" + pack("<HH", 7, 5) + b"\x00\x00\x00"
_IMG = (
    b"\x2c" + pack("<HHHH", 0, 0, 7, 5) + b"\x00" + b"\x02" + b"\x02\x4c\x01" + b"\x00"
)
_TRAILER = b"\x3b"


def _gce(delay_cs=0, packed=0x00):
    return b"\x21\xf9\x04" + bytes([packed]) + pack("<H", delay_cs) + b"\x00" + b"\x00"


def test_no_frames_raises():
    # a valid header followed immediately by the trailer -> no image frames
    with pytest.raises(GifParseError, match="no frames"):
        parse_gif(_HDR + _TRAILER)


def test_truncated_after_trailing_extension():
    # one complete frame, then a dangling GCE and no trailer (EOF mid-scan)
    info = parse_gif(_HDR + _IMG + _gce())
    assert info.frame_count == 1
    assert info.truncated is True


def test_clean_trailer_after_extension():
    # a GCE between the last frame and the trailer is a clean (non-truncated) end
    info = parse_gif(_HDR + _IMG + _gce() + _TRAILER)
    assert info.frame_count == 1
    assert info.truncated is False


def test_truncated_mid_image_descriptor():
    # frame 0 is complete; a second image descriptor is cut off mid-field
    info = parse_gif(_HDR + _IMG + b"\x2c\x00\x00")
    assert info.frame_count == 1
    assert info.truncated is True


def test_unknown_block_byte_is_skipped():
    # a stray byte that is not an extension/image/trailer marker is skipped,
    # exactly as Pillow's _seek does (``s = b""`` and continue)
    info = parse_gif(_HDR + b"\x99" + _IMG + _TRAILER)
    assert info.frame_count == 1
    assert info.truncated is False


def test_loop_extension_only_honored_before_first_frame():
    # loop=3 before the first frame; a later loop=7 extension must be ignored
    before = b"\x21\xff\x0bNETSCAPE2.0" + b"\x03\x01\x03\x00" + b"\x00"  # loop=3
    after = b"\x21\xff\x0bNETSCAPE2.0" + b"\x03\x01\x07\x00" + b"\x00"  # loop=7
    info = parse_gif(_HDR + before + _IMG + after + _IMG + _TRAILER)
    assert info.loop_count == 3


def test_malformed_netscape_loop_subblock_ignored():
    # a NETSCAPE app-ext whose loop sub-block has the wrong id (not 0x01)
    netscape = b"\x21\xff\x0bNETSCAPE2.0" + b"\x03\x00\x00\x00" + b"\x00"
    info = parse_gif(_HDR + netscape + _IMG + _TRAILER)
    assert info.loop_count is None
    assert info.frame_count == 1
