import shutil
import os.path

import pytest

from thumbor_video_engine.engines.video import Engine as VideoEngine


@pytest.fixture
def config(config):
    config.RESULT_STORAGE = 'thumbor_video_engine.result_storages.file_storage'
    config.RESULT_STORAGE_STORES_UNSAFE = True
    config.AUTO_WEBP = True
    config.FFMPEG_GIF_AUTO_H264 = True
    return config


@pytest.mark.gen_test
@pytest.mark.parametrize('subdir,accept', [
    ('default', '*/*'),
    ('auto_webp', 'image/webp'),
    ('auto_mp4', 'video/*'),
])
def test_file_result_storage_save(config, http_client, base_url, tmp_path, subdir, accept):
    config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH = str(tmp_path)
    response = yield http_client.fetch("%s/unsafe/hotdog.gif" % base_url,
        headers={'Accept': accept})
    assert response.code == 200
    assert (tmp_path / subdir / "ba/68/88258f0b20357d15380b611a7b31da32f19b").exists()


@pytest.mark.gen_test
@pytest.mark.parametrize('subdir,accept,ext', [
    ('default', '*/*', 'gif'),
    ('auto_webp', 'image/webp', 'webp'),
    ('auto_mp4', 'video/*', 'mp4'),
])
def test_file_result_storage_retrieve(
        config, mocker, http_client, base_url, tmp_path, storage_path, subdir, accept, ext):
    config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH = str(tmp_path)

    src_file = "%s/hotdog.%s" % (storage_path, ext)

    os.makedirs("%s/%s/ba/68" % (tmp_path, subdir))

    shutil.copyfile(
        src_file,
        "%s/%s/ba/68/88258f0b20357d15380b611a7b31da32f19b" % (tmp_path, subdir))

    mocker.spy(VideoEngine, "load")

    response = yield http_client.fetch("%s/unsafe/hotdog.gif" % base_url,
        headers={'Accept': accept})
    assert response.code == 200
    assert VideoEngine.load.call_count == 0

    response = yield http_client.fetch(
        "%s/unsafe/pbj-time.gif" % base_url,
        headers={'Accept': accept})
    assert response.code == 200
    assert VideoEngine.load.call_count == 1


@pytest.mark.gen_test
@pytest.mark.parametrize('subdir,accept,ext', [
    ('', '*/*', 'gif'),
    ('/webp', 'image/webp', 'webp'),
    ('/mp4', 'video/*', 'mp4'),
])
def test_file_result_storage_legacy_retrieve(
        config, mocker, http_client, base_url, tmp_path, storage_path, subdir, accept, ext):
    config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH = str(tmp_path)

    src_file = "%s/hotdog.%s" % (storage_path, ext)

    os.makedirs("%s/v2%s/un/sa/unsafe" % (tmp_path, subdir))

    shutil.copyfile(
        src_file,
        "%s/v2%s/un/sa/unsafe/hotdog.gif" % (tmp_path, subdir))

    mocker.spy(VideoEngine, "load")

    response = yield http_client.fetch("%s/unsafe/hotdog.gif" % base_url,
        headers={'Accept': accept})
    assert response.code == 200
    assert VideoEngine.load.call_count == 0

    response = yield http_client.fetch(
        "%s/unsafe/pbj-time.gif" % base_url,
        headers={'Accept': accept})
    assert response.code == 200
    assert VideoEngine.load.call_count == 1
