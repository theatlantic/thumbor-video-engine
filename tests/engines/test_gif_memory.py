"""Memory regression checks for the gif pipelines.

These are skipped by default because they generate a large fixture and are
sensitive to the host's ffmpeg/gifski build. Run them explicitly with::

    THUMBOR_VIDEO_ENGINE_MEM_TEST=1 pytest tests/engines/test_gif_memory.py

The guard they enforce: a gif transcode must never buffer the whole animation
in the Python heap. ``tracemalloc`` measures only Python-level allocations
(ffmpeg/gifsicle/gifski subprocess memory is excluded), so the peak should
track the *output* size, not the decoded source frames. For the 960x540 x 60
fixture below, materializing every frame canvas would be ~120 MB; the assert
threshold sits well under that.
"""

import os
import tracemalloc
from io import BytesIO

import pytest
from PIL import Image, ImageDraw

try:
    from shutil import which
except ImportError:
    from thumbor.utils import which

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine


pytestmark = pytest.mark.skipif(
    not os.getenv("THUMBOR_VIDEO_ENGINE_MEM_TEST"),
    reason="set THUMBOR_VIDEO_ENGINE_MEM_TEST=1 to run memory regression checks")

GIF_W, GIF_H, GIF_N = 960, 540, 60
HEAP_BUDGET_MB = 48


def _make_big_gif(path):
    frames = []
    for i in range(GIF_N):
        im = Image.new("RGB", (GIF_W, GIF_H))
        d = ImageDraw.Draw(im)
        for y in range(0, GIF_H, 8):
            d.rectangle(
                [0, y, GIF_W, y + 8],
                fill=((i * 3 + y) % 256, (y * 2) % 256, (i * 7) % 256))
        # a moving box keeps frames distinct (defeats gifski dedup)
        d.rectangle([(i * 15) % GIF_W, 60, ((i * 15) % GIF_W) + 100, 220],
                    fill=(255, 255, 0))
        frames.append(im)
    frames[0].save(
        path, save_all=True, append_images=frames[1:], duration=40, loop=0)


@pytest.fixture
def big_gif_buffer(tmp_path):
    path = str(tmp_path / "big.gif")
    _make_big_gif(path)
    with open(path, mode="rb") as f:
        return f.read()


@pytest.mark.parametrize("pipeline", ["legacy", "gifski"])
@pytest.mark.parametrize("target", [(480, 270), (960, 540)])
def test_python_heap_stays_bounded(context, big_gif_buffer, pipeline, target):
    if pipeline == "gifski" and not which("gifski"):
        pytest.skip("gifski binary not available")

    context.config.FFMPEG_GIF_PIPELINE = pipeline
    context.config.FFMPEG_USE_GIFSICLE_ENGINE = True
    # exercise the requested pipeline rather than auto-routing big targets
    context.config.GIFSKI_MAX_TARGET_PIXELS = 0
    context.config.MAX_ANIMATED_GIF_PIXELS = 0

    engine = FFmpegEngine(context)
    engine.load(big_gif_buffer, ".gif")
    engine.resize(*target)

    tracemalloc.start()
    try:
        out = engine.read(".gif", quality=80)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    assert peak_mb < HEAP_BUDGET_MB, (
        "%s pipeline peaked at %.1f MB of Python heap (budget %d MB); the "
        "whole animation may be buffered in memory again"
        % (pipeline, peak_mb, HEAP_BUDGET_MB))

    im = Image.open(BytesIO(out))
    assert im.format == "GIF"
    assert im.size == target
    assert im.n_frames == GIF_N
