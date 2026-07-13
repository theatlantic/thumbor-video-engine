from io import BytesIO

import pytest
from PIL import Image

from thumbor_video_engine.ffprobe import ffprobe


GIF_HEADERS = {"Accept": "image/gif,*/*;q=0.8"}

# hotdog.gif is 200x150 x 42 frames = 1,260,000 total pixels
HOTDOG_TOTAL_PIXELS = 200 * 150 * 42


@pytest.fixture
def config(config):
    config.FILTERS = ["thumbor_video_engine.filters.format"]
    config.FFMPEG_GIF_AUTO_WEBP = False
    return config


@pytest.mark.asyncio
async def test_oversized_gif_to_gif_returns_400(config, http_client, base_url):
    config.MAX_ANIMATED_GIF_PIXELS = HOTDOG_TOTAL_PIXELS - 1

    with pytest.raises(Exception) as exc_info:
        await http_client.fetch(
            "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)
    assert exc_info.value.code == 400


@pytest.mark.asyncio
async def test_at_limit_passes(config, http_client, base_url):
    config.MAX_ANIMATED_GIF_PIXELS = HOTDOG_TOTAL_PIXELS

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)
    assert response.code == 200


@pytest.mark.asyncio
async def test_gate_disabled_when_zero(config, http_client, base_url):
    config.MAX_ANIMATED_GIF_PIXELS = 0

    response = await http_client.fetch(
        "%s/unsafe/100x75/hotdog.gif" % base_url, headers=GIF_HEADERS)
    assert response.code == 200
    im = Image.open(BytesIO(response.body))
    assert im.is_animated


@pytest.mark.asyncio
async def test_oversized_gif_to_video_is_not_gated(config, http_client, base_url):
    # a GIF over the limit converted to h265 is the efficient path and must not
    # be rejected -- the gate only applies to gif->gif output
    config.MAX_ANIMATED_GIF_PIXELS = HOTDOG_TOTAL_PIXELS - 1

    response = await http_client.fetch(
        "%s/unsafe/filters:format(h265)/hotdog.gif" % base_url,
        headers={"Accept": "video/*"})
    assert response.code == 200
    assert response.headers.get("content-type") == "video/mp4"
    assert ffprobe(response.body)["codec_name"] == "hevc"
