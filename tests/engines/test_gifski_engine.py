import os
import shutil
from io import BytesIO

import pytest
from PIL import Image

try:
    from shutil import which
except ImportError:
    from thumbor.utils import which

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine
from thumbor_video_engine.utils import has_transparency


GIF_HEADERS = {"Accept": "image/gif,*/*;q=0.8"}


@pytest.fixture
def storage_path(tmp_path, storage_path):
    """Copy the shared fixtures into a per-test loader root and generate a
    variable-frame-delay gif (not committed to the repo)."""
    for name in ("hotdog.gif", "pbj-time.gif", "hotdog.mp4", "hotdog.webp"):
        shutil.copy(os.path.join(storage_path, name), str(tmp_path))
    frames = [
        Image.new("RGB", (64, 64), color)
        for color in ("red", "green", "blue", "yellow")
    ]
    frames[0].save(
        str(tmp_path / "vfr.gif"),
        save_all=True,
        append_images=frames[1:],
        duration=[300, 100, 500, 200],
        loop=0,
    )
    return str(tmp_path)


@pytest.fixture
def config(config):
    config.FILTERS = ["thumbor_video_engine.filters.format"]
    config.FFMPEG_GIF_PIPELINE = "gifski"
    config.GIFSKI_PATH = which("gifski")
    config.FFMPEG_USE_GIFSICLE_ENGINE = True
    # Keep gif routing deterministic regardless of Accept headers
    config.FFMPEG_GIF_AUTO_WEBP = False
    return config


def open_gif(body):
    im = Image.open(BytesIO(body))
    assert im.format == "GIF"
    return im


def gif_durations(im):
    durations = []
    for i in range(im.n_frames):
        im.seek(i)
        im.load()
        durations.append(im.info["duration"])
    return durations


@pytest.mark.asyncio
async def test_resize_uses_y4m_route(mocker, config, http_client, base_url):
    y4m_spy = mocker.spy(FFmpegEngine, "_gifski_y4m")
    png_spy = mocker.spy(FFmpegEngine, "_gifski_png_frames")
    legacy_spy = mocker.spy(FFmpegEngine, "_gif_legacy")

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    assert response.headers.get("content-type") == "image/gif"

    im = open_gif(response.body)
    assert im.size == (100, 75)
    assert im.is_animated
    # gifski may merge near-duplicate frames into longer delays, but the
    # total animation duration must be preserved (source: 42 x 30ms)
    assert sum(gif_durations(im)) == 1260
    assert im.info.get("loop") == 0

    assert y4m_spy.call_count == 1
    assert png_spy.call_count == 0
    assert legacy_spy.call_count == 0


@pytest.mark.asyncio
async def test_legacy_mode_skips_gifski(mocker, config, http_client, base_url):
    config.FFMPEG_GIF_PIPELINE = "legacy"
    legacy_spy = mocker.spy(FFmpegEngine, "_gif_legacy")
    gifski_spy = mocker.spy(FFmpegEngine, "_transcode_to_gif_gifski")

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    im = open_gif(response.body)
    assert im.size == (100, 75)
    assert im.is_animated
    assert sum(gif_durations(im)) == 1260

    assert gifski_spy.call_count == 0
    assert legacy_spy.call_count == 1


@pytest.mark.asyncio
async def test_transparent_gif_uses_png_route_and_keeps_alpha(
        mocker, config, http_client, base_url):
    y4m_spy = mocker.spy(FFmpegEngine, "_gifski_y4m")
    png_spy = mocker.spy(FFmpegEngine, "_gifski_png_frames")

    response = await http_client.fetch(
        "%s/unsafe/100x100/pbj-time.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    im = open_gif(response.body)
    assert im.size == (100, 100)
    assert im.is_animated
    assert has_transparency(im)
    # uniform 10fps x 8 frames -> 800ms, preserved through frame merging
    assert sum(gif_durations(im)) == 800

    assert png_spy.call_count == 1
    assert y4m_spy.call_count == 0


@pytest.mark.asyncio
async def test_vfr_gif_uses_legacy_and_preserves_delays(
        mocker, config, http_client, base_url):
    legacy_spy = mocker.spy(FFmpegEngine, "_gif_legacy")
    y4m_spy = mocker.spy(FFmpegEngine, "_gifski_y4m")

    response = await http_client.fetch(
        "%s/unsafe/32x32/vfr.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    im = open_gif(response.body)
    assert im.size == (32, 32)
    assert im.n_frames == 4

    durations = gif_durations(im)
    assert sum(durations) == pytest.approx(1100, rel=0.1)
    assert len(set(durations)) > 1, "variable delays were not preserved"

    assert legacy_spy.call_count == 1
    assert y4m_spy.call_count == 0


@pytest.mark.asyncio
async def test_probe_does_not_decode_frames(monkeypatch, config, http_client, base_url):
    import thumbor_video_engine.engines.ffmpeg as ffmpeg_module

    class ExplodingIterator(object):
        def __init__(self, *args, **kwargs):
            raise AssertionError(
                "probe() should not iterate frames for GIF inputs")

    monkeypatch.setattr(
        ffmpeg_module.ImageSequence, "Iterator", ExplodingIterator)

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)
    assert response.code == 200
    assert open_gif(response.body).is_animated


@pytest.mark.asyncio
async def test_mp4_to_gif_format_filter(mocker, config, http_client, base_url):
    y4m_spy = mocker.spy(FFmpegEngine, "_gifski_y4m")

    response = await http_client.fetch(
        "%s/unsafe/filters:format(gif)/hotdog.mp4" % base_url,
        headers=GIF_HEADERS)

    assert response.code == 200
    assert response.headers.get("content-type") == "image/gif"
    im = open_gif(response.body)
    assert im.is_animated

    assert y4m_spy.call_count == 1


@pytest.mark.asyncio
async def test_gifski_missing_binary_falls_back_to_legacy(
        mocker, config, http_client, base_url):
    config.GIFSKI_PATH = "/nonexistent/gifski"
    legacy_spy = mocker.spy(FFmpegEngine, "_gif_legacy")
    gifski_spy = mocker.spy(FFmpegEngine, "_transcode_to_gif_gifski")

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    im = open_gif(response.body)
    assert im.size == (100, 75)
    assert im.is_animated

    assert legacy_spy.call_count == 1
    assert gifski_spy.call_count == 0


@pytest.mark.asyncio
async def test_gifski_failure_returns_error(config, http_client, base_url):
    # `false` resolves on PATH but exits non-zero, exercising the
    # pipeline's "raise on either non-zero return code" path
    config.GIFSKI_PATH = which("false") or "/usr/bin/false"

    with pytest.raises(Exception) as exc_info:
        await http_client.fetch(
            "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)
    assert exc_info.value.code == 500


@pytest.mark.asyncio
async def test_gifsicle_pass_flag(mocker, config, http_client, base_url):
    config.GIFSKI_GIFSICLE_PASS = True
    gifsicle_spy = mocker.spy(FFmpegEngine, "_gifsicle_optimize_file")

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    im = open_gif(response.body)
    assert im.size == (100, 75)
    assert im.is_animated
    assert gifsicle_spy.call_count == 1


@pytest.mark.asyncio
async def test_large_target_routes_to_legacy(mocker, config, http_client, base_url):
    # 100x75 = 7,500 target pixels; any threshold below that forces the
    # bounded-memory legacy path
    config.GIFSKI_MAX_TARGET_PIXELS = 7499
    legacy_spy = mocker.spy(FFmpegEngine, "_gif_legacy")
    y4m_spy = mocker.spy(FFmpegEngine, "_gifski_y4m")

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    im = open_gif(response.body)
    assert im.size == (100, 75)
    assert im.is_animated

    assert legacy_spy.call_count == 1
    assert y4m_spy.call_count == 0


@pytest.mark.asyncio
async def test_target_pixel_switch_disabled_when_zero(
        mocker, config, http_client, base_url):
    config.GIFSKI_MAX_TARGET_PIXELS = 0
    legacy_spy = mocker.spy(FFmpegEngine, "_gif_legacy")
    y4m_spy = mocker.spy(FFmpegEngine, "_gifski_y4m")

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    assert y4m_spy.call_count == 1
    assert legacy_spy.call_count == 0


@pytest.mark.asyncio
async def test_animated_webp_source_uses_legacy(mocker, config, http_client, base_url):
    # animated webp -> gif: gif_info is None (not a gif) but PIL opened the
    # image, so the gifski pipeline routes to the timing-exact legacy path
    legacy_spy = mocker.spy(FFmpegEngine, "_gif_legacy")
    y4m_spy = mocker.spy(FFmpegEngine, "_gifski_y4m")
    png_spy = mocker.spy(FFmpegEngine, "_gifski_png_frames")

    response = await http_client.fetch(
        "%s/unsafe/filters:format(gif)/hotdog.webp" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    assert response.headers.get("content-type") == "image/gif"
    assert open_gif(response.body).is_animated

    assert legacy_spy.call_count == 1
    assert y4m_spy.call_count == 0
    assert png_spy.call_count == 0


@pytest.mark.asyncio
async def test_png_route_gifsicle_pass(mocker, config, http_client, base_url):
    config.GIFSKI_GIFSICLE_PASS = True
    png_spy = mocker.spy(FFmpegEngine, "_gifski_png_frames")
    gifsicle_spy = mocker.spy(FFmpegEngine, "_gifsicle_optimize_file")

    response = await http_client.fetch(
        "%s/unsafe/100x100/pbj-time.gif" % base_url, headers=GIF_HEADERS)

    assert response.code == 200
    im = open_gif(response.body)
    assert has_transparency(im)
    # transparent gif -> PNG-frames route, then the optional gifsicle -O3 pass
    assert png_spy.call_count == 1
    assert gifsicle_spy.call_count == 1
