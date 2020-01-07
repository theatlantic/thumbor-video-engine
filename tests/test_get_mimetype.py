import pytest

from thumbor_video_engine.engines.video import BaseEngine


@pytest.mark.parametrize('fname,mime_type', [
    ('hotdog.mp4', 'video/mp4'),
    ('hotdog.h265.mp4', 'video/mp4'),
    ('corrupt2.mp4', None),
])
def test_get_mimetype_monkeypatch(storage_path, fname, mime_type):
    with open("%s/%s" % (storage_path, fname), mode='rb') as f:
        buf = f.read()
    assert BaseEngine.get_mimetype(buf) == mime_type
