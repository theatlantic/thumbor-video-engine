import pytest
from unittest import mock

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = type("Fake", (object,), {"fixture": pytest.fixture})
else:
    import asyncio
try:
    import thumbor_aws.s3_client
except ImportError:
    thumbor_aws = None

from thumbor.engines import BaseEngine
from thumbor_video_engine.engines.video import Engine as VideoEngine

import tornado.httpserver
import tornado.httpclient


@pytest_asyncio.fixture(autouse=True)
async def io_loop(request):
    io_loop = tornado.ioloop.IOLoop.current()
    assert io_loop.asyncio_loop is asyncio.get_event_loop()

    def _close():
        io_loop.close(all_fds=True)

    request.addfinalizer(_close)
    return io_loop


@pytest_asyncio.fixture
async def http_server(_unused_port, app):
    server = tornado.httpserver.HTTPServer(app)
    server.add_socket(_unused_port[0])
    await asyncio.sleep(0)
    yield server
    server.stop()
    await server.close_all_connections()


@pytest_asyncio.fixture
async def http_client(http_server, s3_client):
    await s3_client.create_bucket(Bucket="my-bucket")
    client = tornado.httpclient.AsyncHTTPClient()
    yield client
    client.close()


@pytest.fixture
def config(config, s3_client, s3_server):
    config.RESULT_STORAGE = "thumbor_video_engine.result_storages.aws_storage"
    config.APP_CLASS = "thumbor_video_engine.app.ThumborServiceApp"
    config.RESULT_STORAGE_STORES_UNSAFE = True
    config.AUTO_WEBP = True
    config.FFMPEG_GIF_AUTO_H264 = True
    config.THUMBOR_AWS_RUN_IN_COMPATIBILITY_MODE = True
    config.TC_AWS_RESULT_STORAGE_BUCKET = (
        config.AWS_RESULT_STORAGE_BUCKET_NAME
    ) = "my-bucket"
    config.TC_AWS_ENDPOINT = s3_server
    config.AWS_LOADER_S3_ENDPOINT_URL = s3_server
    config.AWS_DEFAULT_LOCATION = s3_server
    return config


@pytest.mark.skipif(thumbor_aws is None, reason="thumbor_aws unavailable")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auto_suffix,mime_type",
    [
        ("", "image/gif"),
        ("/webp", "image/webp"),
        ("/mp4", "video/mp4"),
    ],
)
async def test_s3_result_storage_save(
    mocker, config, http_client, base_url, auto_suffix, mime_type, s3_client
):
    mocker.spy(thumbor_aws.s3_client.S3Client, "upload")
    response = await http_client.fetch(
        "%s/unsafe/hotdog.gif" % base_url, headers={"Accept": mime_type}
    )

    assert response.code == 200
    bucket_key = "unsafe/hotdog.gif%s" % auto_suffix
    assert thumbor_aws.s3_client.S3Client.upload.mock_calls == [
        mock.call(mocker.ANY, bucket_key, mocker.ANY, mocker.ANY, mocker.ANY)
    ]
    assert BaseEngine.get_mimetype(response.body) == mime_type
    assert response.headers.get("vary") == "Accept"


@pytest.mark.skipif(thumbor_aws is None, reason="thumbor_aws unavailable")
@pytest.mark.asyncio
@pytest.mark.parametrize("auto_gif", (False, True))
@pytest.mark.parametrize(
    "bucket_key,mime_type,accepts",
    [
        ("unsafe/hotdog.gif", "image/gif", "*/*"),
        ("unsafe/hotdog.png", "image/png", "*/*"),
        ("unsafe/hotdog.gif/webp", "image/webp", "image/webp"),
        ("unsafe/hotdog.gif/mp4", "video/mp4", "video/*"),
    ],
)
async def test_s3_result_storage_load(
    mocker,
    config,
    http_client,
    base_url,
    auto_gif,
    bucket_key,
    mime_type,
    accepts,
    s3_client,
    storage_path,
):
    config = config
    config.AUTO_WEBP = auto_gif
    config.FFMPEG_GIF_AUTO_H264 = auto_gif

    if mime_type == "image/gif":
        config.FFMPEG_GIF_AUTO_H264 = False

    mocker.spy(VideoEngine, "load")

    if not auto_gif and mime_type != "image/png":
        bucket_key = "unsafe/hotdog.gif"
        mime_type = "image/gif"

    ext = mime_type.rpartition("/")[-1]

    with open("%s/hotdog.%s" % (storage_path, ext), mode="rb") as f:
        im_bytes = f.read()

    await s3_client.put_object(
        Bucket="my-bucket", Key=bucket_key, Body=im_bytes, ContentType=mime_type
    )

    req_ext = "png" if mime_type == "image/png" else "gif"
    response = await http_client.fetch(
        "%s/unsafe/hotdog.%s" % (base_url, req_ext), headers={"Accept": accepts}
    )

    assert response.code == 200
    assert response.headers.get("content-type") == mime_type
    assert response.body == im_bytes
    if auto_gif:
        assert response.headers.get("vary") == "Accept"
    else:
        assert response.headers.get("vary") is None
    assert VideoEngine.load.call_count == 0


@pytest.mark.parametrize(
    "accepts,bucket_key",
    [
        (None, "35cc347e42ac84494cc01bd09c2f00e0199330fb/unsafe/hotdog.gif"),
        ("webp", "7376d420d176b808de02128d747d4baa776e417a/unsafe/hotdog.gif/webp"),
        ("video", "5062b049349be02a856b065e5895c5ca1714e1d4/unsafe/hotdog.gif/mp4"),
    ],
)
@pytest.mark.skipif(thumbor_aws is None, reason="thumbor_aws unavailable")
def test_normalize_path_thumbor_aws_tc_aws_compat_settings(config, context, accepts, bucket_key):
    config.TC_AWS_RANDOMIZE_KEYS = True
    path = "unsafe/hotdog.gif"
    result_storage = context.modules.result_storage
    if accepts == "video":
        result_storage.context.request.accepts_video = True
    elif accepts == "webp":
        result_storage.context.request.accepts_webp = True
    assert result_storage.normalize_path(path) == bucket_key
