from io import BytesIO
import pytest

from thumbor.engines import BaseEngine
from thumbor.engines.gif import Engine as GifEngine
from thumbor.engines.pil import Engine as PilEngine

from PIL import Image

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine
from thumbor_video_engine.engines.video import Engine as VideoEngine

from tests.utils import color_diff, repr_rgb


def assert_colors_similar(rgb1, rgb2, message):
    delta_e = color_diff(rgb1, rgb2)
    assert delta_e < 0.05, f"{message}: {repr_rgb(rgb1)} != {repr_rgb(rgb2)}"


@pytest.fixture
def config(config):
    config.FILTERS = ['thumbor_video_engine.filters.format', 'thumbor.filters.fill']
    return config


@pytest.mark.gen_test
def test_dispatch_to_video_engine(mocker, http_client, base_url):
    mocker.spy(FFmpegEngine, 'load')

    response = yield http_client.fetch("%s/unsafe/hotdog.mp4" % base_url)

    assert response.code == 200
    assert FFmpegEngine.load.call_count == 1
    assert BaseEngine.get_mimetype(response.body) == 'video/mp4'


@pytest.mark.gen_test
def test_dispatch_to_image_engine(mocker, http_client, base_url):
    mocker.spy(PilEngine, 'load')

    response = yield http_client.fetch("%s/unsafe/filters:format(jpg)/hotdog.png" % base_url)

    assert response.code == 200
    assert PilEngine.load.call_count == 1
    assert BaseEngine.get_mimetype(response.body) == 'image/jpeg'


@pytest.mark.gen_test
def test_fill_filter(http_client, base_url):
    response = yield http_client.fetch(
        "%s/unsafe/filters:format(jpg):fill(ffff00,1)/hotdog-transparent.png" % base_url
    )

    assert response.code == 200
    assert BaseEngine.get_mimetype(response.body) == "image/jpeg"

    im = Image.open(BytesIO(response.body))

    top_left_color = im.getpixel((0, 0))[:3]
    assert_colors_similar(top_left_color, (255, 255, 0), "Fill not applied")


@pytest.mark.gen_test
def test_dispatch_non_animated_gif_to_gif_engine(mocker, config, http_client, base_url):
    config.FFMPEG_USE_GIFSICLE_ENGINE = True
    config.FFMPEG_HANDLE_ANIMATED_GIF = True

    mocker.spy(GifEngine, 'load')

    response = yield http_client.fetch("%s/unsafe/100x75/hotdog-still.gif" % base_url)

    assert response.code == 200
    assert GifEngine.load.call_count == 1
    assert BaseEngine.get_mimetype(response.body) == 'image/gif'

    im = Image.open(BytesIO(response.body))
    assert im.size == (100, 75)


@pytest.mark.gen_test
def test_config_handle_animated_gif_false(mocker, config, http_client, base_url):
    config.FFMPEG_USE_GIFSICLE_ENGINE = True
    config.FFMPEG_HANDLE_ANIMATED_GIF = False

    mocker.spy(GifEngine, 'load')

    response = yield http_client.fetch("%s/unsafe/100x75/hotdog.gif" % base_url)

    assert response.code == 200
    assert GifEngine.load.call_count == 1
    assert BaseEngine.get_mimetype(response.body) == 'image/gif'

    im = Image.open(BytesIO(response.body))
    assert im.size == (100, 75)


@pytest.mark.gen_test
def test_config_handle_animated_gif_true_use_gif_engine(mocker, config, http_client, base_url):
    config.FFMPEG_USE_GIFSICLE_ENGINE = True
    config.FFMPEG_HANDLE_ANIMATED_GIF = True

    mocker.spy(GifEngine, 'load')
    mocker.spy(FFmpegEngine, 'load')
    mocker.spy(GifEngine, 'resize')
    mocker.spy(FFmpegEngine, 'resize')

    response = yield http_client.fetch("%s/unsafe/100x75/hotdog.gif" % base_url)

    assert response.code == 200
    assert BaseEngine.get_mimetype(response.body) == 'image/gif'

    im = Image.open(BytesIO(response.body))
    assert im.size == (100, 75)

    assert GifEngine.load.call_count == 1
    assert FFmpegEngine.load.call_count == 1

    GifEngine.resize.assert_called_with(mocker.ANY, 100, 75)
    FFmpegEngine.resize.assert_called_with(mocker.ANY, 100, 75)


@pytest.mark.gen_test
def test_config_handle_animated_gif_true_no_use_gif_engine(mocker, config, http_client, base_url):
    config.FFMPEG_USE_GIFSICLE_ENGINE = False
    config.FFMPEG_HANDLE_ANIMATED_GIF = True

    mocker.spy(GifEngine, 'load')
    mocker.spy(FFmpegEngine, 'load')
    mocker.spy(GifEngine, 'resize')
    mocker.spy(FFmpegEngine, 'resize')

    response = yield http_client.fetch("%s/unsafe/100x75/hotdog.gif" % base_url)

    assert response.code == 200
    assert BaseEngine.get_mimetype(response.body) == 'image/gif'

    im = Image.open(BytesIO(response.body))
    assert im.size == (100, 75)

    assert GifEngine.load.call_count == 0
    assert FFmpegEngine.load.call_count == 1

    GifEngine.resize.mock_calls == []
    FFmpegEngine.resize.assert_called_with(mocker.ANY, 100, 75)


def test_video_engine_getattr_dispatch(context):
    video_engine = VideoEngine(context)
    ffmpeg_engine = FFmpegEngine(context)
    video_engine.engine = ffmpeg_engine
    assert video_engine.reorientate == ffmpeg_engine.reorientate


def test_video_engine_setattr_dispatch(mocker, context):
    video_engine = VideoEngine(context)
    mock = mocker.Mock()
    video_engine.engine = mock
    video_engine.foo = 'FOO'
    assert mock.foo == 'FOO'


def test_video_engine_getattr_attributeerror(context):
    video_engine = VideoEngine(context)
    with pytest.raises(AttributeError):
        video_engine.size


@pytest.mark.parametrize('attr,cls,call_count', [
    ('image_engine', PilEngine, 2),
    ('ffmpeg_engine', FFmpegEngine, 1),
])
def test_engine_properties(mocker, context, attr, cls, call_count):
    mocker.spy(context.modules.importer, 'import_item')
    video_engine = VideoEngine(context)
    # Do twice to test value caching
    for i in range(0, 2):
        val = getattr(video_engine, attr)
        assert isinstance(val, cls)
    assert context.modules.importer.import_item.call_count == call_count
