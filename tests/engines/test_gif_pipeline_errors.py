"""Unit coverage for the error/fallback branches in the gif pipeline that the
integration tests don't reach: _video_fps fallbacks, the transparency-probe
failure path, and the failure modes of _gifski_png_frames, _gifsicle_optimize_file,
and _run_pipeline."""

import os
from fractions import Fraction

import pytest

import thumbor_video_engine.engines.ffmpeg as ffmpeg_module
from thumbor_video_engine.engines.ffmpeg import (
    Engine as FFmpegEngine,
    DEFAULT_VIDEO_GIF_FPS,
    MAX_VIDEO_GIF_FPS,
)
from thumbor_video_engine.exceptions import FFmpegError
from thumbor_video_engine.utils import GifParseError


@pytest.mark.parametrize(
    "src_rate,expected",
    [
        (None, DEFAULT_VIDEO_GIF_FPS),  # Fraction(None) -> TypeError
        ("not-a-rate", DEFAULT_VIDEO_GIF_FPS),  # ValueError
        ("0/0", DEFAULT_VIDEO_GIF_FPS),  # ZeroDivisionError
        ("0/1", DEFAULT_VIDEO_GIF_FPS),  # parses to 0 -> fps <= 0
        ("500/1", MAX_VIDEO_GIF_FPS),  # clamped down to the cap
        ("25/1", Fraction(25)),  # ordinary integer rate
        ("30000/1001", Fraction(30000, 1001)),  # ordinary fractional rate
    ],
)
def test_video_fps_fallbacks(context, src_rate, expected):
    engine = FFmpegEngine(context)
    engine.source_frame_rate = src_rate
    assert engine._video_fps() == expected


def test_visibly_transparent_no_flags_short_circuits(context, mocker):
    engine = FFmpegEngine(context)
    has_transparency = mocker.patch.object(
        engine, "has_transparency", return_value=True
    )
    info = mocker.Mock(has_transparency_flags=False)
    assert engine._gif_visibly_transparent(info) is False
    # must not pay for a pixel check when no frame declares transparency
    assert has_transparency.call_count == 0


def test_visibly_transparent_frame0_has_alpha(context, mocker):
    engine = FFmpegEngine(context)
    mocker.patch.object(engine, "has_transparency", return_value=True)
    info = mocker.Mock(has_transparency_flags=True)
    assert engine._gif_visibly_transparent(info) is True


def test_visibly_transparent_assumes_true_on_error(context, mocker):
    engine = FFmpegEngine(context)
    mocker.patch.object(engine, "has_transparency", side_effect=RuntimeError("boom"))
    info = mocker.Mock(has_transparency_flags=True)
    # if we can't determine transparency, err toward the (always-correct) PNG route
    assert engine._gif_visibly_transparent(info) is True


@pytest.mark.parametrize(
    "transparent_disposal,expected", [(True, True), (False, False)]
)
def test_visibly_transparent_falls_back_to_disposal(
    context, mocker, transparent_disposal, expected
):
    engine = FFmpegEngine(context)
    mocker.patch.object(engine, "has_transparency", return_value=False)
    info = mocker.Mock(
        has_transparency_flags=True, has_transparent_disposal=transparent_disposal
    )
    assert engine._gif_visibly_transparent(info) is expected


def test_png_frames_no_output_raises(context, mocker):
    engine = FFmpegEngine(context)
    # run_cmd is stubbed, so no PNG frames land in the tmp dir
    mocker.patch.object(engine, "run_cmd", return_value=b"")
    with pytest.raises(FFmpegError, match="produced no frames"):
        engine._gifski_png_frames("/tmp/does-not-matter.gif", Fraction(10), "0")


def test_gifsicle_invalid_output_raises(context, mocker):
    engine = FFmpegEngine(context)

    def fake_run(command):
        # gifsicle "succeeds" but writes something that isn't a gif
        out_file = command[command.index("-o") + 1]
        with open(out_file, "wb") as f:
            f.write(b"definitely not a gif")
        return b""

    mocker.patch.object(engine, "run_cmd", side_effect=fake_run)
    with pytest.raises(FFmpegError, match="invalid output"):
        engine._gifsicle_optimize_file("/tmp/in.gif")


def test_run_pipeline_sink_start_failure_cleans_up(context):
    engine = FFmpegEngine(context)
    # the sink binary does not exist: Popen raises, the source must be killed
    # and reaped, and the original error re-raised (not masked)
    with pytest.raises((FileNotFoundError, OSError)):
        engine._run_pipeline(["echo", "hi"], ["/nonexistent/sink-binary-xyz"])


def test_run_pipeline_source_nonzero_raises(context):
    engine = FFmpegEngine(context)
    context.request = None  # exercise the "no request" branch of the error message
    # `false` exits 1 producing no output; `cat` drains empty stdin and exits 0
    with pytest.raises(FFmpegError):
        engine._run_pipeline(["false"], ["cat"])


def test_run_pipeline_sink_nonzero_raises(context):
    engine = FFmpegEngine(context)
    # source is fine; `false` as the sink ignores stdin and exits 1
    with pytest.raises(FFmpegError):
        engine._run_pipeline(["echo", "hi"], ["false"])


def test_load_falls_back_to_pil_when_parse_gif_raises(context, mocker, storage_path):
    # if the parser rejects a gif that PIL can still open, load() must swallow
    # the GifParseError, leave gif_info None, and let probe() fall back to PIL's
    # frame iteration (which still yields size and duration)
    mocker.patch.object(
        ffmpeg_module, "parse_gif", side_effect=GifParseError("unparseable")
    )
    with open(os.path.join(storage_path, "hotdog.gif"), mode="rb") as f:
        buf = f.read()

    engine = FFmpegEngine(context)
    engine.load(buf, ".gif")

    assert engine.gif_info is None
    assert engine.original_size == (200, 150)
    assert engine.duration > 0
