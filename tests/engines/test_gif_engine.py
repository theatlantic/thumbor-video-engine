from io import BytesIO

import pytest

from PIL import Image
from thumbor.engines import BaseEngine
try:
    from shutil import which
except ImportError:
    from thumbor.utils import which

import thumbor_video_engine.engines.gif
from thumbor_video_engine.engines.gif import Engine as GifEngine
from thumbor.engines.gif import Engine as BaseGifEngine


@pytest.fixture
def config(config):
    config.GIF_ENGINE = 'thumbor_video_engine.engines.gif'
    return config


@pytest.fixture
def gif_buffer(storage_path):
    with open("%s/hotdog.gif" % storage_path, mode="rb") as f:
        return f.read()


@pytest.mark.gen_test
def test_operations_resize_colors(mocker, config, http_client, base_url):
    config.FFMPEG_USE_GIFSICLE_ENGINE = True
    config.FFMPEG_HANDLE_ANIMATED_GIF = False

    mocker.spy(GifEngine, 'load')
    mocker.spy(GifEngine, 'run_gifsicle')

    response = yield http_client.fetch("%s/unsafe/100x75/hotdog.gif" % base_url)

    assert GifEngine.run_gifsicle.mock_calls == [
        mocker.call(mocker.ANY, '--info'),
        mocker.call(mocker.ANY, '--resize 100x75 --resize-colors 64'),
    ]

    assert response.code == 200
    assert GifEngine.load.call_count == 1
    assert BaseEngine.get_mimetype(response.body) == 'image/gif'

    im = Image.open(BytesIO(response.body))
    assert im.size == (100, 75)


def test_server_gifsicle_none_calls_which(mocker, context, gif_buffer):
    assert which('gifsicle') is not None, "Test cannot run without gifsicle in PATH"

    mocker.spy(thumbor_video_engine.engines.gif, 'which')
    mocker.spy(GifEngine, 'run_gifsicle')

    context.server.gifsicle_path = None

    engine = GifEngine(context)
    engine.load(gif_buffer, '.gif')

    assert GifEngine.run_gifsicle.mock_calls == [
        mocker.call(mocker.ANY, '--info'),
    ]
    assert thumbor_video_engine.engines.gif.which.mock_calls == [mocker.call('gifsicle')]
    assert context.server.gifsicle_path == which('gifsicle')


def test_server_gifsicle_none_no_which_raises(mocker, context, gif_buffer):
    mocker.patch.object(thumbor_video_engine.engines.gif, 'which', return_value=None)
    mocker.spy(GifEngine, 'run_gifsicle')

    context.server.gifsicle_path = None

    engine = GifEngine(context)
    with pytest.raises(RuntimeError):
        engine.load(gif_buffer, '.gif')

    assert GifEngine.run_gifsicle.mock_calls == [
        mocker.call(mocker.ANY, '--info'),
    ]
    assert thumbor_video_engine.engines.gif.which.mock_calls == [mocker.call('gifsicle')]


@pytest.mark.gen_test
def test_gifsicle_args(mocker, config, http_client, base_url):
    config.FFMPEG_USE_GIFSICLE_ENGINE = True
    config.FFMPEG_HANDLE_ANIMATED_GIF = False
    config.GIFSICLE_ARGS = ["--careful"]

    mocker.spy(GifEngine, 'load')
    mocker.spy(BaseGifEngine, 'run_gifsicle')

    response = yield http_client.fetch("%s/unsafe/100x75/hotdog.gif" % base_url)

    assert BaseGifEngine.run_gifsicle.mock_calls == [
        mocker.call(mocker.ANY, '--info --careful'),
        mocker.call(mocker.ANY, '--resize 100x75 --resize-colors 64 --careful'),
    ]

    assert response.code == 200
    assert GifEngine.load.call_count == 1
    assert BaseEngine.get_mimetype(response.body) == 'image/gif'

    im = Image.open(BytesIO(response.body))
    assert im.size == (100, 75)
