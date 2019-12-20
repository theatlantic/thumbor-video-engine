from tempfile import NamedTemporaryFile
import json
import os
from os.path import exists
from subprocess import Popen, PIPE

from thumbor.utils import which

import six


FFPROBE_PATH = os.getenv('FFPROBE_PATH', None)


def ffprobe(input_file):
    global FFPROBE_PATH

    if FFPROBE_PATH is None:
        FFPROBE_PATH = which('ffprobe')

    if FFPROBE_PATH is None:
        raise Exception("Could not find ffprobe executable")

    try:
        is_file_path = (isinstance(input_file, six.string_types) and exists(input_file))
    except TypeError:
        is_file_path = False

    if not is_file_path:
        tmp_file = NamedTemporaryFile(delete=False)
        tmp_file.write(input_file)
        tmp_file.close()
        input_file = tmp_file.name
    else:
        tmp_file = None

    try:
        command = [
            FFPROBE_PATH, '-hide_banner', '-loglevel', 'fatal',
            '-show_error', '-show_format', '-show_streams', '-show_private_data',
            '-print_format', 'json',
            '-i', input_file,
        ]

        proc = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)

        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            raise Exception(
                "ffprobe returned error %(returncode)s for command '%(command)s': "
                "%(stdout)s\n%(stderr)s" % {
                    'returncode': proc.returncode,
                    'command': " ".join(command),
                    'stdout': stdout,
                    'stderr': stderr,
                })
        return json.loads(stdout)
    finally:
        if tmp_file:
            os.unlink(tmp_file.name)
