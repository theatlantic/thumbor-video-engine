from thumbor.engines import BaseEngine

import pytest


VIDEO_HEADERS = {"Accept": 'video/*,*/*;q=0.8'}


@pytest.mark.gen_test
@pytest.mark.parametrize('accepts_video', (True, False))
@pytest.mark.parametrize('setting_key,setting_val,format_box', [
    ('FFMPEG_GIF_AUTO_H264', True, b'avcC'),
    ('FFMPEG_GIF_AUTO_H265', True, b'hvcC'),
    ('FFMPEG_GIF_AUTO_H264', False, None),
])
def test_auto_h26x_transcodes_anim_gif(http_client, base_url, accepts_video,
                                       config, setting_key, setting_val, format_box):
    setattr(config, setting_key, setting_val)

    response = yield http_client.fetch("%s/unsafe/hotdog.gif" % base_url,
        headers=(VIDEO_HEADERS if accepts_video else {}))

    mime_type = 'video/mp4' if accepts_video and setting_val else 'image/gif'

    assert response.code == 200
    assert response.headers.get('content-type') == mime_type

    assert BaseEngine.get_mimetype(response.body) == mime_type

    if format_box and accepts_video:
        # Check that the correct format atom appears near the beginning of the
        # file (to verify whether the video is correctly h264 or h265)
        assert format_box in response.body[:800]

    if setting_val is True:
        vary_header = (response.headers.get('vary') or '').lower()
        assert 'accept' in vary_header
