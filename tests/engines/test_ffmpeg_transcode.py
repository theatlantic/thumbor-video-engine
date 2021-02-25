from io import BytesIO

import pytest
from PIL import Image

from thumbor_video_engine.ffprobe import ffprobe
from thumbor_video_engine.utils import has_transparency


@pytest.fixture
def config(config):
    config.FILTERS = ['thumbor_video_engine.filters.format']
    return config


@pytest.mark.gen_test
@pytest.mark.parametrize("src_ext", ['gif', 'mp4', 'h265.mp4', 'webp', 'webm'])
def test_transcode_to_h264(http_client, base_url, src_ext):
    url_filter = "/filters:format(h264)" if src_ext else ""
    if src_ext is None:
        src_ext = "mp4"

    response = yield http_client.fetch(
        "%s/unsafe%s/hotdog.%s" % (base_url, url_filter, src_ext))

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    file_info = ffprobe(response.body)

    expected = {
        'codec_name': 'h264',
        'width': 200,
        'height': 150,
        'pix_fmt': 'yuv420p',
    }
    actual = {k: file_info.get(k) for k in expected}
    assert expected == actual


@pytest.mark.gen_test
@pytest.mark.parametrize("src_ext", ['gif', 'mp4', 'h265.mp4', 'webp', 'webm'])
def test_transcode_to_h265(http_client, base_url, src_ext):
    response = yield http_client.fetch(
        "%s/unsafe/filters:format(h265)/hotdog.%s" % (base_url, src_ext))

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    file_info = ffprobe(response.body)

    expected = {
        'codec_name': 'hevc',
        'width': 200,
        'height': 150,
        'pix_fmt': 'yuv420p',
    }
    actual = {k: file_info.get(k) for k in expected}
    assert expected == actual


@pytest.mark.gen_test
@pytest.mark.parametrize("src_ext", ['gif', 'mp4', 'h265.mp4', 'webp', 'webm', None])
def test_transcode_to_webm(http_client, base_url, src_ext):
    url_filter = "/filters:format(webm)" if src_ext else ""
    if src_ext is None:
        src_ext = "webm"

    response = yield http_client.fetch(
        "%s/unsafe%s/hotdog.%s" % (base_url, url_filter, src_ext))

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


@pytest.mark.gen_test
@pytest.mark.parametrize("src_ext", ['gif', 'mp4', 'h265.mp4', 'webp', 'webm', None])
@pytest.mark.parametrize("config_key,config_val", [
    ('FFMPEG_USE_GIFSICLE_ENGINE', False),
    ('FFMPEG_USE_GIFSICLE_ENGINE', True),
])
def test_transcode_to_gif(config_key, config_val, http_client, base_url, config, src_ext):
    setattr(config, config_key, config_val)

    url_filter = "/filters:format(gif)" if src_ext else ""
    if src_ext is None:
        src_ext = "gif"

    response = yield http_client.fetch(
        "%s/unsafe%s/hotdog.%s" % (base_url, url_filter, src_ext))

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/gif'

    file_info = ffprobe(response.body)

    expected = {
        'codec_name': 'gif',
        'width': 200,
        'height': 150,
        'pix_fmt': 'bgra',
    }
    actual = {k: file_info.get(k) for k in expected}
    assert expected == actual


@pytest.mark.gen_test
@pytest.mark.parametrize("src_ext", ['gif', 'mp4', 'h265.mp4', 'webm', 'webp'])
def test_transcode_to_webp(http_client, base_url, src_ext):
    response = yield http_client.fetch(
        "%s/unsafe/filters:format(webp)/hotdog.%s" % (base_url, src_ext))

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/webp'

    im = Image.open(BytesIO(response.body))

    assert im.format == 'WEBP'
    assert im.is_animated is True
    assert im.size == (200, 150)


@pytest.mark.gen_test
def test_transcode_webp_variable_frame_durations(http_client, base_url):
    response = yield http_client.fetch(
        "%s/unsafe/filters:format(webp)/hotdog-variable-frame-durations.webp" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/webp'

    im = Image.open(BytesIO(response.body))

    assert im.format == 'WEBP'
    assert im.is_animated is True
    assert im.size == (200, 150)

    # Assert that the first frame is 3x longer than the second
    im.seek(0)
    im.load()
    assert im.info['duration'] == 120


@pytest.mark.gen_test
@pytest.mark.parametrize("codec", ['h264', 'hevc'])
def test_mp4_resize_odd_dimensions(http_client, base_url, codec):
    """h264 and h265 require videos to have width and height be even integers"""
    response = yield http_client.fetch(
        "%s/unsafe/100x75/filters:format(%s)/hotdog.mp4" % (base_url, codec))

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    file_info = ffprobe(response.body)

    expected = {
        'codec_name': codec,
        'width': 100,
        'height': 74,
        'pix_fmt': 'yuv420p',
    }
    actual = {k: file_info.get(k) for k in expected}
    assert expected == actual


@pytest.mark.gen_test
@pytest.mark.parametrize("src_ext", ['gif', 'webp'])
def test_alpha_transcode_to_webp(http_client, base_url, src_ext):
    response = yield http_client.fetch(
        "%s/unsafe/filters:format(webp)/pbj-time.%s" % (base_url, src_ext))

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/webp'

    im = Image.open(BytesIO(response.body))

    assert im.mode == 'RGBA'
    assert im.format == 'WEBP'

    assert has_transparency(im)

    assert im.is_animated is True
    assert im.size == (200, 200)


@pytest.mark.gen_test
@pytest.mark.parametrize("src_ext", ['gif', 'webp'])
def test_alpha_transcode_to_gif(http_client, base_url, src_ext):
    response = yield http_client.fetch(
        "%s/unsafe/filters:format(gif)/pbj-time.%s" % (base_url, src_ext))

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/gif'

    im = Image.open(BytesIO(response.body))

    assert im.mode == 'P'
    assert im.info['transparency'] == im.info['background']

    assert has_transparency(im)

    assert im.format == 'GIF'
    assert im.is_animated is True
    assert im.size == (200, 200)
