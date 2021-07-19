from os.path import join
import tc_aws.result_storages.s3_storage
from tornado.concurrent import return_future
from .base import BaseStorage


class Storage(BaseStorage, tc_aws.result_storages.s3_storage.Storage):
    # @return_future
    # def put(self, bytes, callback=None):
    #     import ipdb; ipdb.set_trace()
    #     super(Storage, self).put(bytes, callback=callback)

    # @return_future
    # def set(self, bytes, abspath, callback=None):
    #     super(Storage, self).set(bytes, abspath, callback)

    def _normalize_path(self, path):
        """
        Adapts path based on configuration (root_path for instance)
        :param string path: Path to adapt
        :return: Adapted path
        :rtype: string
        """
        path = path.lstrip('/')  # Remove leading '/'
        path_segments = [path]

        root_path = self._get_config('ROOT_PATH')
        if root_path and root_path is not '':
            path_segments.insert(0, root_path)

        transcode_segment = self.get_auto_path_component()

        if transcode_segment:
            path_segments.append(transcode_segment)

        if self._should_randomize_key():
            path_segments.insert(0, self._generate_digest(path_segments))

        if len(path_segments) > 1:
            normalized_path = join(path_segments[0], *path_segments[1:]).lstrip('/')
        else:
            normalized_path = path_segments[0]

        if normalized_path.endswith('/'):
            normalized_path += self.context.config.TC_AWS_ROOT_IMAGE_NAME
        return normalized_path
