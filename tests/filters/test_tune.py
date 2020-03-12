import pytest

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine

from thumbor_video_engine.ffprobe import ffprobe


@pytest.fixture
def config(config):
    config.FILTERS = [
        'thumbor_video_engine.filters.tune',
        'thumbor_video_engine.filters.format',
    ]
    return config


@pytest.mark.gen_test(timeout=10)
def test_h264_tune_filter(mocker, http_client, base_url, ffmpeg_path):
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch(
        "%s/unsafe/filters:tune(animation)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-tune' in cmd
    assert cmd[cmd.index('-tune') + 1] == 'animation'

    file_info = ffprobe(response.body)

    expected = {
        'codec_name': 'h264',
        'width': 200,
        'height': 150,
        'pix_fmt': 'yuv420p',
    }
    actual = {k: file_info.get(k) for k in expected}
    assert expected == actual


@pytest.mark.gen_test(timeout=10)
def test_h265_tune_filter(mocker, http_client, base_url, ffmpeg_path):
    mocker.spy(FFmpegEngine, 'run_cmd')

    response = yield http_client.fetch(
        "%s/unsafe/filters:tune(animation):format(h265)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FFmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FFmpegEngine.run_cmd.mock_calls[0][1][1]

    assert '-tune' in cmd
    assert cmd[cmd.index('-tune') + 1] == 'animation'

    file_info = ffprobe(response.body)

    expected = {
        'codec_name': 'hevc',
        'width': 200,
        'height': 150,
        'pix_fmt': 'yuv420p',
    }
    actual = {k: file_info.get(k) for k in expected}
    assert expected == actual
