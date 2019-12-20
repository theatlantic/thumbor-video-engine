import pytest


from thumbor.app import ThumborServiceApp
from thumbor.context import Context, RequestParameters, ServerParameters
from thumbor.importer import Importer
from thumbor.server import configure_log
from thumbor.utils import which


@pytest.fixture
def app(context):
    return ThumborServiceApp(context)


@pytest.fixture
def context(config, base_url):
    config.ENGINE = 'thumbor_video_engine.engines.video'
    config.FILTERS = [
        'thumbor_video_engine.filters.format',
        'thumbor_video_engine.filters.still',
    ]

    importer = Importer(config)
    importer.import_modules()

    req = RequestParameters()

    http_port = int(base_url.rpartition(':')[-1])
    server = ServerParameters(http_port, 'localhost', 'thumbor.conf', None, 'info', None)
    server.security_key = config.SECURITY_KEY
    server.gifsicle_path = which('gifsicle')

    context = Context(server=server, config=config, importer=importer)
    context.request = req
    context.request.engine = context.modules.engine

    configure_log(config, 'DEBUG')
    return context
