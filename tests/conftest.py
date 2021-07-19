import os
import pytest

from thumbor.config import Config
from thumbor.context import Context, ServerParameters, RequestParameters
from thumbor.importer import Importer
from thumbor.server import configure_log, get_application
try:
    from shutil import which
except ImportError:
    from thumbor.utils import which


CURR_DIR = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def storage_path():
    return os.path.join(CURR_DIR, 'data')


@pytest.fixture
def ffmpeg_path():
    return os.getenv('FFMPEG_PATH') or which('ffmpeg')


@pytest.fixture
def mp4_buffer(storage_path):
    with open(os.path.join(storage_path, 'hotdog.mp4'), mode='rb') as f:
        return f.read()


@pytest.fixture
def config(storage_path, ffmpeg_path):
    Config.allow_environment_variables()
    return Config(
        SECURITY_KEY='changeme',
        LOADER='thumbor.loaders.file_loader',
        APP_CLASS='thumbor_video_engine.app.ThumborServiceApp',
        FILTERS=[],
        FILE_LOADER_ROOT_PATH=storage_path,
        FFMPEG_PATH=ffmpeg_path,
        FFPROBE_PATH=(os.getenv('FFPROBE_PATH') or which('ffprobe')),
        STORAGE='thumbor.storages.no_storage')


@pytest.fixture
def context(config):
    config.ENGINE = 'thumbor_video_engine.engines.video'

    importer = Importer(config)
    importer.import_modules()

    server = ServerParameters(
        None, 'localhost', 'thumbor.conf', None, 'info', config.APP_CLASS,
        gifsicle_path=which('gifsicle'))
    server.security_key = config.SECURITY_KEY

    req = RequestParameters()

    configure_log(config, 'DEBUG')

    with Context(server=server, config=config, importer=importer) as context:
        context.request = req
        context.request.engine = context.modules.engine
        yield context


@pytest.fixture
def app(context):
    return get_application(context)
