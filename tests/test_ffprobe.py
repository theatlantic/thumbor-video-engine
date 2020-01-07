import pytest

from thumbor_video_engine.exceptions import FFmpegError
import thumbor_video_engine.ffprobe
from thumbor_video_engine.ffprobe import ffprobe


def test_ffprobe_path_which(mocker, monkeypatch, mp4_buffer):
    monkeypatch.setattr(thumbor_video_engine.ffprobe, 'FFPROBE_PATH', None)
    mocker.patch.object(
        thumbor_video_engine.ffprobe, 'which', return_value='/opt/bin/ffprobe')
    mocker.patch.object(
        thumbor_video_engine.ffprobe, 'Popen', side_effect=FFmpegError)
    with pytest.raises(FFmpegError):
        ffprobe(mp4_buffer)
    assert thumbor_video_engine.ffprobe.which.mock_calls == [
        mocker.call('ffprobe')
    ]
    assert thumbor_video_engine.ffprobe.FFPROBE_PATH == '/opt/bin/ffprobe'


def test_ffprobe_path_not_found(mocker, monkeypatch, mp4_buffer):
    monkeypatch.setattr(thumbor_video_engine.ffprobe, 'FFPROBE_PATH', None)
    mocker.patch.object(
        thumbor_video_engine.ffprobe, 'which', return_value=None)
    with pytest.raises(FFmpegError) as exc:
        ffprobe(mp4_buffer)
    assert str(exc.value) == 'Could not find ffprobe executable'


def test_ffprobe_error_code(storage_path):
    with open("%s/corrupt2.mp4" % storage_path, mode="rb") as f:
        corrupt_buf = f.read()
    with pytest.raises(FFmpegError) as exc:
        ffprobe(corrupt_buf)
    assert str(exc.value) == "Invalid data found when processing input (-1094995529)"


@pytest.mark.parametrize("stdout", ['FOO', '[]', '{}'])
def test_ffprobe_invalid_data(mocker, mp4_buffer, stdout):
    mock_proc = mocker.Mock(**{'communicate.return_value': (stdout, '')})
    mocker.patch.object(
        thumbor_video_engine.ffprobe, 'Popen', return_value=mock_proc)
    with pytest.raises(FFmpegError) as exc:
        ffprobe(mp4_buffer)
    assert str(exc.value) == 'ffprobe returned invalid data'


def test_ffprobe_flat(storage_path):
    with open("%s/hotdog.mp4" % storage_path, mode="rb") as f:
        aac_data = f.read()
    ret = ffprobe(aac_data, flat=False)
    assert set(ret.keys()) == {'streams', 'format'}


def test_ffprobe_missing_video_stream(storage_path):
    with open("%s/tearing-me-apart.m4a" % storage_path, mode="rb") as f:
        aac_data = f.read()
    with pytest.raises(FFmpegError) as exc:
        ffprobe(aac_data)
    assert str(exc.value) == 'File is missing a video stream'
