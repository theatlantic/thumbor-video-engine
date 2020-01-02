import pytest

from tornado.httpclient import HTTPClientError
from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine


def test_is_multiple(context):
    engine = FFmpegEngine(context)
    assert engine.is_multiple() is False


def test_can_convert_to_webp(context):
    engine = FFmpegEngine(context)
    assert engine.can_convert_to_webp() is False


def test_source_width(context):
    engine = FFmpegEngine(context)
    engine.original_size = 200, 150
    assert engine.source_width == 200


def test_source_height(context):
    engine = FFmpegEngine(context)
    engine.original_size = 200, 150
    assert engine.source_height == 150


@pytest.mark.gen_test
def test_error_handling(mocker, http_client, base_url):
    with pytest.raises(HTTPClientError) as exc_info:
        yield http_client.fetch("%s/unsafe/corrupt.mp4" % base_url)
    assert exc_info.value.code == 500
