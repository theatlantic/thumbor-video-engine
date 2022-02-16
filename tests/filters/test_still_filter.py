from io import BytesIO

import pytest

from thumbor.engines import BaseEngine
from PIL import Image


@pytest.fixture
def config(config):
    config.FILTERS = [
        'thumbor_video_engine.filters.format',
        'thumbor_video_engine.filters.still',
        'thumbor.filters.watermark',
    ]
    config.QUALITY = 95
    return config


@pytest.mark.gen_test
@pytest.mark.parametrize('pos', ['', '00:00:00'])
def test_still_filter(http_client, base_url, pos):
    response = yield http_client.fetch(
        "%s/unsafe/filters:still(%s)/hotdog.mp4" % (base_url, pos))

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/jpeg'

    assert BaseEngine.get_mimetype(response.body) == 'image/jpeg'


@pytest.mark.gen_test
@pytest.mark.parametrize('format,mime_type', [
    ('webp', 'image/webp'),
    ('jpg', 'image/jpeg'),
    ('zpg', 'image/jpeg'),
])
def test_still_filter_with_format(http_client, base_url, format, mime_type):
    response = yield http_client.fetch(
        "%s/unsafe/filters:still():format(%s)/hotdog.mp4" % (base_url, format))

    assert response.code == 200
    assert response.headers.get('content-type') == mime_type

    assert BaseEngine.get_mimetype(response.body) == mime_type


@pytest.mark.gen_test
def test_still_filter_with_watermark(http_client, base_url):
    response = yield http_client.fetch(
        "%s/unsafe/filters:still():format(png):"
        "watermark(watermark.png,0,0,0)/hotdog.mp4" % (base_url))
    assert response.code == 200
    im = Image.open(BytesIO(response.body))
    assert im.getpixel((85, 55))[:3] == (255, 255, 255)
    assert response.headers.get('content-type') == 'image/png'
