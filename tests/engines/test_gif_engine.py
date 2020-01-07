from io import BytesIO

import pytest

from PIL import Image
from thumbor.engines import BaseEngine

from thumbor_video_engine.engines.gif import Engine as GifEngine


@pytest.fixture
def config(config):
    config.GIF_ENGINE = 'thumbor_video_engine.engines.gif'
    return config


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
