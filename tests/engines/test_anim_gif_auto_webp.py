from io import BytesIO

from PIL import Image

import pytest


WEBP_HEADERS = {"Accept": 'image/webp,*/*;q=0.8'}


@pytest.fixture
def config(config):
    config.AUTO_WEBP = True
    config.GIF_ENGINE = 'thumbor_video_engine.engines.gif'
    config.FFMPEG_USE_GIFSICLE_ENGINE = True
    config.FFMPEG_HANDLE_ANIMATED_GIF = True
    return config


@pytest.mark.gen_test
@pytest.mark.parametrize('accepts_webp', (True, False))
@pytest.mark.parametrize('ffmpeg_conf_gif_auto_webp', (True, False))
def test_auto_webp_transcodes_anim_gif(http_client, base_url, accepts_webp,
                                       config, ffmpeg_conf_gif_auto_webp):
    config.FFMPEG_GIF_AUTO_WEBP = ffmpeg_conf_gif_auto_webp

    response = yield http_client.fetch("%s/unsafe/hotdog.gif" % base_url,
        headers=(WEBP_HEADERS if accepts_webp else {}))

    img_format = 'webp' if accepts_webp and ffmpeg_conf_gif_auto_webp else 'gif'

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/%s' % img_format

    im = Image.open(BytesIO(response.body))

    assert im.format == img_format.upper()
    assert im.is_animated is True
    assert im.size == (200, 150)

    if ffmpeg_conf_gif_auto_webp:
        vary_header = (response.headers.get('vary') or '').lower()
        assert 'accept' in vary_header
