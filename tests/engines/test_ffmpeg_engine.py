import pytest

from tornado.httpclient import HTTPClientError
from thumbor_video_engine.exceptions import FFmpegError
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


@pytest.mark.gen_test
@pytest.mark.parametrize('has_ctx_request', [True, False])
def test_error_handling_run_cmd(storage_path, mocker, context, has_ctx_request):
    if not has_ctx_request:
        context.request = None
    with open("%s/corrupt.mp4" % storage_path, mode='rb') as f:
        buf = f.read()
    engine = FFmpegEngine(context)
    engine.buffer = buf
    engine.extension = '.mp4'
    engine.original_size = (200, 150)
    with pytest.raises(FFmpegError):
        engine.read(".mp4", quality=80)


def test_returns_original(context, mp4_buffer):
    engine = FFmpegEngine(context)
    engine.load(mp4_buffer, '.mp4')
    result = engine.read('.mp4')
    assert result == mp4_buffer


def test_invalid_output_format(context, mp4_buffer):
    context.request.format = 'xyz'
    engine = FFmpegEngine(context)
    engine.load(mp4_buffer, '.mp4')
    with pytest.raises(FFmpegError) as exc:
        engine.read('.mp4', 80)
    assert str(exc.value) == "Invalid video format 'xyz' requested"
