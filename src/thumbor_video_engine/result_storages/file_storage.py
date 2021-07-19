import hashlib
from os.path import join
from six.moves.urllib.parse import unquote

from thumbor.result_storages import file_storage
from .base import BaseStorage


class Storage(BaseStorage, file_storage.Storage):
    def normalize_path(self, path):
        digest = hashlib.sha1(unquote(path).encode("utf-8")).hexdigest()

        auto_path_component = self.get_auto_path_component()

        return "%s/%s/%s/%s/%s" % (
            self.context.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH.rstrip('/'),
            "auto_%s" % auto_path_component if auto_path_component else "default",
            digest[:2],
            digest[2:4],
            digest[4:]
        )

    def normalize_path_legacy(self, path):
        try:
            # Python 2
            path = unquote(path).decode('utf-8')
        except AttributeError:
            # Python 3
            path = unquote(path)

        path_segments = [
            self.context.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH.rstrip("/"),
            file_storage.Storage.PATH_FORMAT_VERSION,
        ]

        auto_path_component = self.get_auto_path_component()
        if auto_path_component:
            path_segments.append(auto_path_component)

        path_segments.extend([self.partition(path), path.lstrip("/")])

        normalized_path = join(*path_segments).replace("http://", "")
        return normalized_path
