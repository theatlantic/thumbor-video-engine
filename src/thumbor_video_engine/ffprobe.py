import json
import os
from subprocess import Popen, PIPE

import six
try:
    from shutil import which
except ImportError:
    from thumbor.utils import which

from thumbor_video_engine.exceptions import FFmpegError
from thumbor_video_engine.utils import named_tmp_file


FFPROBE_PATH = os.getenv('FFPROBE_PATH', None)


def ffprobe(buf, extension=None, flat=True):
    """
    Returns a dict based on the json output of ffprobe. If ``flat`` is ``True``,
    the 'format' key-values are made top-level, as well as the first video stream
    in the file (the rest are discarded). Any 'stream' keys that have the same
    name as a key in 'format' are prefixed with ``stream_``.
    """
    global FFPROBE_PATH

    if FFPROBE_PATH is None:
        FFPROBE_PATH = which('ffprobe')

    if FFPROBE_PATH is None:
        raise FFmpegError("Could not find ffprobe executable")

    with named_tmp_file(data=buf, extension=extension) as input_file:
        command = [
            FFPROBE_PATH, '-hide_banner', '-loglevel', 'fatal', '-show_error',
            '-show_format', '-show_streams', '-print_format', 'json',
            '-i', input_file,
        ]

        proc = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)

        stdout, stderr = proc.communicate()

        try:
            probe_data = json.loads(stdout)
        except ValueError:
            probe_data = None

        if not isinstance(probe_data, dict):
            raise FFmpegError("ffprobe returned invalid data")

        if 'error' in probe_data:
            raise FFmpegError("%(string)s (%(code)s)" % probe_data['error'])

        if 'format' not in probe_data or 'streams' not in probe_data:
            raise FFmpegError("ffprobe returned invalid data")

        if not flat:
            return probe_data

        try:
            video_stream = next(s for s in probe_data['streams'] if s['codec_type'] == 'video')
        except StopIteration:
            raise FFmpegError("File is missing a video stream")

        data = probe_data['format']
        for k, v in six.iteritems(video_stream):
            if k in data:
                k = 'stream_%s' % k
            data[k] = v
        return data
