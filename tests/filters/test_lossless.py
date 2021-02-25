from io import BytesIO

import pytest
from PIL import Image

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine

from thumbor_video_engine.ffprobe import ffprobe


@pytest.fixture
def config(config):
    config.FILTERS = ['thumbor_video_engine.filters.lossless']
    return config


@pytest.mark.gen_test(timeout=10)
def test_webm_lossless_filter(mocker, http_client, base_url, ffmpeg_path):
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch(
        "%s/unsafe/filters:lossless()/hotdog.webm" % (base_url))

    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-lossless' in cmd
    assert cmd[cmd.index('-lossless') + 1] == '1'

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/webm'

    file_info = ffprobe(response.body)

    expected = {
        'codec_name': 'vp9',
        'width': 200,
        'height': 150,
        'pix_fmt': 'yuv420p',
    }
    actual = {k: file_info.get(k) for k in expected}
    assert expected == actual


@pytest.mark.gen_test(timeout=15)
def test_webp_lossless_filter(mocker, http_client, base_url, ffmpeg_path):
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch(
        "%s/unsafe/filters:lossless()/hotdog.webp" % (base_url))

    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-lossless' in cmd
    assert cmd[cmd.index('-lossless') + 1] == '1'

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/webp'

    im = Image.open(BytesIO(response.body))

    assert im.format == 'WEBP'
    assert im.is_animated is True
    assert im.size == (200, 150)
