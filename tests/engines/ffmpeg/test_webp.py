import pytest

from ...utils import ffprobe


@pytest.mark.gen_test
def test_transcode_webp_to_h264(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(h264)/hotdog.webp" % base_url)

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
        'width': 266,
        'height': 200,
        'nb_frames': '35',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_transcode_webp_to_webm(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(webm)/hotdog.webp" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'video/webm'

    file_info = ffprobe(response.body)

    assert file_info.get('errors') is None
    assert 'streams' in file_info and 'format' in file_info
    assert 'webm' in file_info['format']['format_name']
    assert len(file_info['streams']) == 1

    stream = file_info['streams'][0]

    expected = {
        'codec_type': 'video',
        'codec_name': 'vp9',
        'width': 266,
        'height': 200,
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual


@pytest.mark.gen_test
def test_transcode_webp_to_hevc(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:format(hevc)/hotdog.webp" % base_url)

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
        'width': 266,
        'height': 200,
        'nb_frames': '35',
        'pix_fmt': 'yuv420p',
    }

    actual = {k: stream.get(k) for k in expected}

    assert expected == actual
