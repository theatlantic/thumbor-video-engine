import pytest

from thumbor.engines import BaseEngine


@pytest.fixture
def config(config):
    config.FILTERS = ['thumbor_video_engine.filters.still']
    return config


@pytest.mark.gen_test
def test_still_default_argument(http_client, base_url):
    response = yield http_client.fetch("%s/unsafe/filters:still()/hotdog.mp4" % base_url)

    assert response.code == 200
    assert response.headers.get('content-type') == 'image/jpeg'

    assert BaseEngine.get_mimetype(response.body) == 'image/jpeg'
