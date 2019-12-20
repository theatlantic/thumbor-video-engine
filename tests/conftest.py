import os
import pytest

from thumbor.config import Config
from thumbor.context import Context
from thumbor.utils import which


CURR_DIR = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def storage_path():
    return os.path.join(CURR_DIR, 'data')


@pytest.fixture
def ffmpeg_path():
    return os.getenv('FFMPEG_PATH') or which('ffmpeg')


@pytest.fixture
def config(storage_path, ffmpeg_path):
    Config.allow_environment_variables()
    return Config(
        SECURITY_KEY='changeme',
        LOADER='thumbor.loaders.file_loader',
        FILTERS=[],
        FILE_LOADER_ROOT_PATH=storage_path,
        FFMPEG_PATH=ffmpeg_path,
        FFPROBE_PATH=(os.getenv('FFPROBE_PATH') or which('ffprobe')),
        STORAGE='thumbor.storages.no_storage')


@pytest.fixture
def context(config):
    return Context(config=config)
