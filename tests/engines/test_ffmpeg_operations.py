import pytest

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine
from thumbor_video_engine.ffprobe import ffprobe


@pytest.fixture
def config(config):
    config.FILTERS = [
        'thumbor.filters.grayscale',
        'thumbor.filters.rotate',
    ]
    return config


@pytest.mark.gen_test
def test_crop(mocker, http_client, base_url):
    mocker.spy(FFmpegEngine, 'crop')
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch("%s/unsafe/50x25:150x125/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FFmpegEngine.crop.assert_called_once_with(mocker.ANY, 50, 25, 150, 125)
    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-vf' in cmd
    assert cmd[cmd.index('-vf') + 1] == 'crop=100:100:50:25'

    file_info = ffprobe(response.body)
    assert (file_info['width'], file_info['height']) == (100, 100)


@pytest.mark.gen_test
def test_flip_horizontally(mocker, http_client, base_url):
    mocker.spy(FFmpegEngine, 'flip_horizontally')
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch("%s/unsafe/-200x150/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FFmpegEngine.flip_horizontally.assert_called_once()
    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-vf' in cmd
    assert cmd[cmd.index('-vf') + 1] == 'hflip'

    file_info = ffprobe(response.body)
    assert (file_info['width'], file_info['height']) == (200, 150)


@pytest.mark.gen_test
def test_flip_vertically(mocker, http_client, base_url):
    mocker.spy(FFmpegEngine, 'flip_vertically')
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch("%s/unsafe/200x-150/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FFmpegEngine.flip_vertically.assert_called_once()
    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-vf' in cmd
    assert cmd[cmd.index('-vf') + 1] == 'vflip'

    file_info = ffprobe(response.body)
    assert (file_info['width'], file_info['height']) == (200, 150)


@pytest.mark.gen_test
def test_filter_grayscale(mocker, http_client, base_url):
    mocker.spy(FFmpegEngine, 'convert_to_grayscale')
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch("%s/unsafe/filters:grayscale()/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FFmpegEngine.convert_to_grayscale.assert_called_once()
    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-vf' in cmd
    assert cmd[cmd.index('-vf') + 1] == 'hue=s=0'

    file_info = ffprobe(response.body)
    assert (file_info['width'], file_info['height']) == (200, 150)


@pytest.mark.gen_test
def test_filter_rotate(mocker, http_client, base_url):
    mocker.spy(FFmpegEngine, 'rotate')
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch("%s/unsafe/filters:rotate(90)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FFmpegEngine.rotate.assert_called_once_with(mocker.ANY, 90)
    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-vf' in cmd
    assert cmd[cmd.index('-vf') + 1] == 'rotate=90'

    file_info = ffprobe(response.body)
    assert (file_info['width'], file_info['height']) == (200, 150)


@pytest.mark.gen_test
def test_reorientate(mocker, config, http_client, base_url):
    config.RESPECT_ORIENTATION = True

    mocker.spy(FFmpegEngine, 'reorientate')
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch("%s/unsafe/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FFmpegEngine.reorientate.assert_called_once()
