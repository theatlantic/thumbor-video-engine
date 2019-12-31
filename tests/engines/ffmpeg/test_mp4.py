from io import BytesIO

import pytest
from PIL import Image

from ...utils import ffprobe


@pytest.mark.gen_test
def test_transcode_mp4_to_webm(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(webm)/hotdog.mp4" % base_url)

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


@pytest.mark.gen_test
@pytest.mark.parametrize("config_key,config_val", [
    ('FFMPEG_USE_GIFSICLE_ENGINE', False),
    ('FFMPEG_USE_GIFSICLE_ENGINE', True),
])
def test_transcode_mp4_to_gif(config_key, config_val, http_client, base_url, config):
    setattr(config, config_key, config_val)

    response = yield http_client.fetch("%s/unsafe/filters:format(gif)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/gif'

    file_info = ffprobe(response.body)

    assert file_info.get('errors') is None
    assert 'streams' in file_info and 'format' in file_info
    assert file_info['format']['format_name'] == 'gif'
    assert len(file_info['streams']) == 1

    stream = file_info['streams'][0]

    expected = {
        'codec_type': 'video',
        'codec_name': 'gif',
        'width': 200,
        'height': 150,
        'pix_fmt': 'bgra',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_transcode_h264_to_hevc(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(hevc)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    file_info = ffprobe(response.body)

    assert file_info.get('errors') is None
    assert 'streams' in file_info and 'format' in file_info
    assert 'mp4' in file_info['format']['format_name']
    assert len(file_info['streams']) == 1

    stream = file_info['streams'][0]

    expected = {
        'codec_type': 'video',
        'codec_name': 'hevc',
        'width': 200,
        'height': 150,
        'duration_ts': 420000,
        'nb_frames': '42',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_h264_resize_odd_dimensions(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/100x75/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    file_info = ffprobe(response.body)

    assert file_info.get('errors') is None
    assert 'streams' in file_info and 'format' in file_info
    assert 'mp4' in file_info['format']['format_name']
    assert len(file_info['streams']) == 1

    stream = file_info['streams'][0]

    expected = {
        'codec_type': 'video',
        'codec_name': 'h264',
        'width': 100,
        'height': 74,
        'nb_frames': '42',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_h265_resize_odd_dimensions(http_client, base_url):
    response = yield http_client.fetch(
        "%s/unsafe/100x75/filters:format(hevc)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    file_info = ffprobe(response.body)

    assert file_info.get('errors') is None
    assert 'streams' in file_info and 'format' in file_info
    assert 'mp4' in file_info['format']['format_name']
    assert len(file_info['streams']) == 1

    stream = file_info['streams'][0]

    expected = {
        'codec_type': 'video',
        'codec_name': 'hevc',
        'width': 100,
        'height': 74,
        'nb_frames': '42',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_transcode_mp4_to_webp(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(webp)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/webp'

    im = Image.open(BytesIO(response.body))

    assert im.format == 'WEBP'
    assert im.is_animated is True
    assert im.n_frames == 42
    assert im.size == (200, 150)
