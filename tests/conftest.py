import asyncio
import os

import pytest
import pytest_asyncio

import tornado.httpclient
import tornado.httpserver
import tornado.testing

from thumbor.config import Config
from thumbor.context import Context, ServerParameters, RequestParameters
from thumbor.importer import Importer
from thumbor.server import configure_log, get_application

try:
    from shutil import which
except ImportError:
    from thumbor.utils import which

try:
    from thumbor.context import ThreadPool
except ImportError:  # pragma: no cover
    ThreadPool = None

try:
    from tests.mock_aio_server import s3_server, s3_client, session  # noqa
except:  # noqa

    @pytest.fixture
    def s3_server():
        yield "http://does.not.exist"

    @pytest.fixture
    def s3_client():
        return None


CURR_DIR = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture(autouse=True)
def reset_thumbor_threadpool():
    """thumbor's ThreadPool is a process-wide singleton that can otherwise
    hold a reference to a previous test's (now closed) event loop."""
    if ThreadPool is not None and getattr(ThreadPool, "_instance", None):
        for thread_pool in ThreadPool._instance.values():
            thread_pool.cleanup()
    yield
    if ThreadPool is not None:
        ThreadPool._instance = None


@pytest.fixture
def storage_path():
    return os.path.join(CURR_DIR, "data")


@pytest.fixture
def ffmpeg_path():
    return os.getenv("FFMPEG_PATH") or which("ffmpeg")


@pytest.fixture
def mp4_buffer(storage_path):
    with open(os.path.join(storage_path, "hotdog.mp4"), mode="rb") as f:
        return f.read()


@pytest.fixture
def config(storage_path, ffmpeg_path):
    Config.allow_environment_variables()
    return Config(
        SECURITY_KEY="changeme",
        LOADER="thumbor.loaders.file_loader",
        APP_CLASS="thumbor_video_engine.app.ThumborServiceApp",
        FILTERS=[],
        FILE_LOADER_ROOT_PATH=storage_path,
        FFMPEG_PATH=ffmpeg_path,
        FFPROBE_PATH=(os.getenv("FFPROBE_PATH") or which("ffprobe")),
        STORAGE="thumbor.storages.no_storage",
    )


@pytest.fixture
def context(config):
    config.ENGINE = "thumbor_video_engine.engines.video"

    importer = Importer(config)
    importer.import_modules()

    server = ServerParameters(
        None,
        "localhost",
        "thumbor.conf",
        None,
        "info",
        config.APP_CLASS,
        gifsicle_path=which("gifsicle"),
    )
    server.security_key = config.SECURITY_KEY

    req = RequestParameters()

    configure_log(config, "DEBUG")

    with Context(server=server, config=config, importer=importer) as context:
        context.request = req
        context.request.engine = context.modules.engine
        yield context


@pytest.fixture
def app(context):
    return get_application(context)


@pytest.fixture
def _unused_port():
    return tornado.testing.bind_unused_port()


@pytest.fixture
def http_port(_unused_port):
    return _unused_port[1]


@pytest.fixture
def base_url(http_port):
    return "http://localhost:%d" % http_port


@pytest_asyncio.fixture
async def http_server(app, _unused_port):
    server = tornado.httpserver.HTTPServer(app)
    server.add_socket(_unused_port[0])
    await asyncio.sleep(0)
    yield server
    server.stop()
    await server.close_all_connections()


@pytest_asyncio.fixture
async def http_client(http_server):
    client = tornado.httpclient.AsyncHTTPClient()
    yield client
    client.close()
