import pytest


from thumbor_video_engine.utils import is_mp4


@pytest.mark.parametrize('bool_val,buf', [
    (True, b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41'),
    (True, b'\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2mp41'),
    (True, b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41'),
    (False, b'\x00\x00\x00\x20XXXXisom\x00\x00\x02\x00isomiso2avc1mp41'),
    (False, b'\x00\x00\x00\x20ftypeaaaa\x00\x00\x02\x00bbbbccccddddeeee'),
    (False, b'\x00\x00\x00\x1bftypisom\x00\x00\x02\x00isomiso2mp4'),
    (False, b'\x00\x00\x00\x08ftypisom'),
])
def test_is_mp4(bool_val, buf):
    assert is_mp4(buf) is bool_val
