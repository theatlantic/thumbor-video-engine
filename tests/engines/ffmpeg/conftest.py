import pytest


from thumbor.context import Context, ServerParameters
from thumbor.importer import Importer
from thumbor.server import configure_log, get_application
from thumbor.utils import which


@pytest.fixture
def context(config, base_url):
    config.ENGINE = 'thumbor_video_engine.engines.video'
    config.FILTERS = [
        'thumbor_video_engine.filters.format',
        'thumbor_video_engine.filters.still',
    ]

    importer = Importer(config)
    importer.import_modules()

    http_port = int(base_url.rpartition(':')[-1])
    server = ServerParameters(
        http_port, 'localhost', 'thumbor.conf', None, 'info', 'thumbor.app.ThumborServiceApp',
        gifsicle_path=which('gifsicle'))
    server.security_key = config.SECURITY_KEY

    configure_log(config, 'DEBUG')

    with Context(server=server, config=config, importer=importer) as context:
        yield context


@pytest.fixture
def app(context):
    return get_application(context)
