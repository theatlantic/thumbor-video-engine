import pytest

from thumbor_video_engine.engines.ffmpeg import Engine as FfmpegEngine

from tests.utils import ffprobe


@pytest.fixture
def config(config):
    config.FILTERS = [
        'thumbor_video_engine.filters.tune',
        'thumbor_video_engine.filters.format',
    ]
    return config


@pytest.mark.gen_test(timeout=10)
def test_h264_tune_filter(mocker, http_client, base_url, ffmpeg_path):
    mocker.spy(FfmpegEngine, 'run_cmd')

    response = yield http_client.fetch(
        "%s/unsafe/filters:tune(animation)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FfmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FfmpegEngine.run_cmd.mock_calls[0].args[1]

    assert '-tune' in cmd
    assert cmd[cmd.index('-tune') + 1] == 'animation'

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
        'nb_frames': '42',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test(timeout=10)
def test_h265_tune_filter(mocker, http_client, base_url, ffmpeg_path):
    mocker.spy(FfmpegEngine, 'run_cmd')

    response = yield http_client.fetch(
        "%s/unsafe/filters:tune(animation):format(h265)/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

    FfmpegEngine.run_cmd.assert_called_once_with(mocker.ANY, mocker.ANY)

    cmd = FfmpegEngine.run_cmd.mock_calls[0].args[1]

    assert '-tune' in cmd
    assert cmd[cmd.index('-tune') + 1] == 'animation'

    file_info = ffprobe(response.body)

    assert file_info.get('errors') is None
    assert 'streams' in file_info and 'format' in file_info
    assert 'mp4' in file_info['format']['format_name']
    assert len(file_info['streams']) == 1

    stream = file_info['streams'][0]

    expected = {
        'codec_type': 'video',
        'codec_name': 'hevc',
        'width': 200,
        'height': 150,
        'duration_ts': 420000,
        'nb_frames': '42',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual
