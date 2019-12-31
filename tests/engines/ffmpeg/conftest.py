import pytest


@pytest.fixture
def config(config):
    config.FILTERS = ['thumbor_video_engine.filters.format']
    return config
