import subprocess
import sys
import pytest
import tornado.testing

try:
    from tc_aws.aws.bucket import Bucket
except:
    Bucket = None

try:
    import asyncio
except ImportError:
    asyncio = None

from thumbor.engines import BaseEngine
from thumbor_video_engine.engines.video import Engine as VideoEngine


# Subclassed Popen that gets around mirakuru not capturing stderr
class SubprocessStderrPipe(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('stderr', subprocess.PIPE)
        super(SubprocessStderrPipe, self).__init__(*args, **kwargs)


@pytest.fixture
def s3_client(monkeypatch, mocker, config):
    import botocore.session
    from mirakuru import TCPExecutor

    host = '127.0.0.1'
    socket, port = tornado.testing.bind_unused_port()
    socket.close()
    monkeypatch.setenv('TEST_SERVER_MODE', 'true')
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', '')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test-key')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test-secret-key')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'test-session-token')

    endpoint_url = "http://%s:%s" % (host, port)
    config.TC_AWS_ENDPOINT = endpoint_url

    mocker.patch('subprocess.Popen', side_effect=SubprocessStderrPipe)

    executor = TCPExecutor(
        (sys.executable, '-m', 'moto.server', '-H', host, '-p', str(port), "s3"),
        host=host, port=port, timeout=10)
    try:
        with executor:
            yield botocore.session.get_session().create_client('s3', endpoint_url=endpoint_url)

    finally:
        if asyncio is not None:
            event_loop = asyncio.get_event_loop()
            instances = getattr(Bucket, "_instances", None) or {}
            for bucket in instances.values():
                event_loop.run_until_complete(bucket._client.close())
        Bucket._instances = {}


@pytest.fixture
def config(config, s3_client):
    config.RESULT_STORAGE = 'thumbor_video_engine.result_storages.s3_storage'
    config.APP_CLASS = 'thumbor_video_engine.app.ThumborServiceApp'
    config.RESULT_STORAGE_STORES_UNSAFE = True
    config.AUTO_WEBP = True
    config.FFMPEG_GIF_AUTO_H264 = True
    config.TC_AWS_RESULT_STORAGE_BUCKET = 'my-bucket'

    s3_client.create_bucket(Bucket='my-bucket')
    return config


@pytest.mark.gen_test
@pytest.mark.skipif(Bucket is None, reason="tc_aws unavailable")
@pytest.mark.parametrize('auto_suffix,mime_type', [
    ('', 'image/gif'),
    ('/webp', 'image/webp'),
    ('/mp4', 'video/mp4'),
])
def test_s3_result_storage_save(mocker, config, http_client, base_url, auto_suffix,
                                mime_type, s3_client):
    mocker.spy(Bucket, "put")
    response = yield http_client.fetch("%s/unsafe/hotdog.gif" % base_url,
        headers={'Accept': mime_type})

    assert response.code == 200

    bucket_key = "unsafe/hotdog.gif%s" % auto_suffix
    Bucket.put.assert_called_once()
    Bucket.put.mock_calls[0].args == (mocker.ANY, bucket_key, mocker.ANY)
    assert BaseEngine.get_mimetype(response.body) == mime_type
    assert response.headers.get("vary") == "Accept"


@pytest.mark.gen_test
@pytest.mark.skipif(Bucket is None, reason="tc_aws unavailable")
@pytest.mark.parametrize('auto_gif', (False, True))
@pytest.mark.parametrize('bucket_key,mime_type,accepts', [
    ('unsafe/hotdog.gif', 'image/gif', '*/*'),
    ('unsafe/hotdog.png', 'image/png', '*/*'),
    ('unsafe/hotdog.gif/webp', 'image/webp', 'image/webp'),
    ('unsafe/hotdog.gif/mp4', 'video/mp4', 'video/*'),
])
def test_s3_result_storage_load(mocker, config, http_client, base_url, auto_gif,
                                bucket_key, mime_type, accepts, s3_client, storage_path):
    config.AUTO_WEBP = auto_gif
    config.FFMPEG_GIF_AUTO_H264 = auto_gif

    if mime_type == 'image/gif':
        config.FFMPEG_GIF_AUTO_H264 = False

    mocker.spy(VideoEngine, "load")

    if not auto_gif and mime_type != 'image/png':
        bucket_key = 'unsafe/hotdog.gif'
        mime_type = 'image/gif'

    ext = mime_type.rpartition('/')[-1]

    with open("%s/hotdog.%s" % (storage_path, ext), mode='rb') as f:
        im_bytes = f.read()

    s3_client.put_object(
        Bucket='my-bucket',
        Key=bucket_key,
        Body=im_bytes,
        ContentType=mime_type)

    req_ext = "png" if mime_type == "image/png" else "gif"
    response = yield http_client.fetch("%s/unsafe/hotdog.%s" % (base_url, req_ext),
        headers={'Accept': mime_type})

    assert response.code == 200
    assert response.headers.get("content-type") == mime_type
    assert response.body == im_bytes
    if auto_gif:
        assert response.headers.get("vary") == "Accept"
    else:
        assert response.headers.get("vary") is None
    assert VideoEngine.load.call_count == 0


@pytest.mark.skipif(Bucket is None, reason="tc_aws unavailable")
def test_normalize_path_tc_aws_settings(config, context):
    config.TC_AWS_RANDOMIZE_KEYS = True
    config.TC_AWS_RESULT_STORAGE_ROOT_PATH = 'root'
    config.TC_AWS_ROOT_IMAGE_NAME = 'image'
    path = 'unsafe/hotdog.gif/'
    result_storage = context.modules.result_storage
    norm_path = result_storage._normalize_path(path)
    assert norm_path == (
        "540642062b67435de4adc8900893823660dd3a2c/root/unsafe/hotdog.gif/image")
