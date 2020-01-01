from io import BytesIO
import pytest

from thumbor.app import ThumborServiceApp
from thumbor.context import Context, RequestParameters, ServerParameters
from thumbor.engines import BaseEngine
from thumbor.engines.gif import Engine as GifEngine
from thumbor.engines.pil import Engine as PilEngine
from thumbor.importer import Importer
from thumbor.server import configure_log
from thumbor.utils import which

from PIL import Image

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine

from ..utils import ffprobe


@pytest.fixture
def app(context):
    return ThumborServiceApp(context)


@pytest.fixture
def context(config, base_url):
    config.ENGINE = 'thumbor_video_engine.engines.video'
    config.FILTERS = ['thumbor_video_engine.filters.format']
    configure_log(config, 'DEBUG')

    importer = Importer(config)
    importer.import_modules()

    http_port = int(base_url.rpartition(':')[-1])
    server = ServerParameters(http_port, 'localhost', 'thumbor.conf', None, 'info', None)
    server.security_key = config.SECURITY_KEY
    server.gifsicle_path = which('gifsicle')

    context = Context(server=server, config=config, importer=importer)
    context.request = RequestParameters()
    context.request.engine = context.modules.engine

    return context


@pytest.mark.gen_test
def test_mp4_loads(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/hotdog.mp4" % base_url)

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
        'width': 200,
        'height': 150,
        'duration_ts': 420000,
        'nb_frames': '42',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_gif_loads(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/hotdog.gif" % base_url)

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
        'nb_frames': '42',
        'pix_fmt': 'bgra',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_dispatch_to_image_engine(mocker, http_client, base_url):
    mocker.spy(PilEngine, 'load')

    response = yield http_client.fetch("%s/unsafe/filters:format(jpg)/hotdog.png" % base_url)

    assert response.code == 200
    assert PilEngine.load.call_count == 1
    assert BaseEngine.get_mimetype(response.body) == 'image/jpeg'


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
