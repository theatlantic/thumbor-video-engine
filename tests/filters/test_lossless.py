from io import BytesIO

import pytest
from PIL import Image

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine

from tests.utils import ffprobe


@pytest.fixture
def config(config):
    config.FILTERS = ['thumbor_video_engine.filters.lossless']
    return config


@pytest.mark.gen_test(timeout=10)
@pytest.mark.parametrize("filter_val", ["1"])
def test_webm_lossless_filter(mocker, http_client, base_url, ffmpeg_path, filter_val):
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch(
        "%s/unsafe/filters:lossless(%s)/hotdog.webm" % (base_url, filter_val))

    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0].args[1]

    assert '-lossless' in cmd
    assert cmd[cmd.index('-lossless') + 1] == '1'

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/webm'

    file_info = ffprobe(response.body)

    assert file_info.get('errors') is None
    assert 'streams' in file_info and 'format' in file_info
    assert 'webm' in file_info['format']['format_name']
    assert len(file_info['streams']) == 1

    stream = file_info['streams'][0]

    expected = {
        'codec_type': 'video',
        'codec_name': 'vp9',
        'width': 200,
        'height': 150,
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test(timeout=15)
@pytest.mark.parametrize("filter_val", ["1"])
def test_webp_lossless_filter(mocker, http_client, base_url, ffmpeg_path, filter_val):
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch(
        "%s/unsafe/filters:lossless(%s)/hotdog.webp" % (base_url, filter_val))

    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0].args[1]

    assert '-lossless' in cmd
    assert cmd[cmd.index('-lossless') + 1] == '1'

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/webp'

    im = Image.open(BytesIO(response.body))

    assert im.format == 'WEBP'
    assert im.is_animated is True
    assert im.n_frames == 34
    assert im.size == (266, 200)
