import pytest
import json

from ...utils import ffprobe


@pytest.mark.gen_test
def test_transcode_webm_to_h264(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(h264)/hotdog.webm" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

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


@pytest.mark.gen_test
def test_transcode_webm_to_gif(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(gif)/hotdog.webm" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/gif'

    file_info = ffprobe(response.body)

    assert file_info.get('errors') is None
    assert 'streams' in file_info and 'format' in file_info
    assert file_info['format']['format_name'] == 'gif'
    assert len(file_info['streams']) == 1

    stream = file_info['streams'][0]

    expected = {
        'codec_type': 'video',
        'codec_name': 'gif',
        'width': 200,
        'height': 150,
        'pix_fmt': 'bgra',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_transcode_webm_to_hevc(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(hevc)/hotdog.webm" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/mp4'

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
        'nb_frames': '42',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual
