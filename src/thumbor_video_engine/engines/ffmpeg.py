from __future__ import unicode_literals

from contextlib import contextmanager
import copy
from decimal import Decimal
from io import BytesIO, open
import re
from subprocess import Popen, PIPE

from PIL import Image, ImageSequence
from thumbor.engines import BaseEngine
from thumbor.utils import logger

from thumbor_video_engine.exceptions import FFmpegError
from thumbor_video_engine.ffprobe import ffprobe
from thumbor_video_engine.utils import named_tmp_file, make_tmp_dir, has_transparency


FORMATS = {
    '.mp4': 'mp4',
    '.webm': 'webm',
    '.gif': 'gif',
    '.gifv': 'mp4',
    '.webp': 'webp',
}


class Engine(BaseEngine):

    def __init__(self, context):
        self.original_size = 1, 1
        self.duration = 0
        self.crop_info = 1, 1, 0, 0
        self.image_size = 1, 1
        self.rotate_degrees = 0
        self.flipped_vertically = False
        self.flipped_horizontally = False
        self.resized = False
        self.cropped = False
        self.grayscale = False
        super(Engine, self).__init__(context)
        self.ffmpeg_path = self.context.config.FFMPEG_PATH
        self.ffprobe_path = self.context.config.FFPROBE_PATH

    @property
    def use_gif_engine(self):
        return self.context.config.FFMPEG_USE_GIFSICLE_ENGINE

    @property
    def size(self):
        return self.image_size

    @property
    def source_width(self):
        return self.original_size[0]

    @source_width.setter
    def source_width(self, width):
        orig_w, orig_h = self.original_size
        self.original_size = (width, orig_h)

    @property
    def source_height(self):
        return self.original_size[1]

    @source_height.setter
    def source_height(self, height):
        orig_w, orig_h = self.original_size
        self.original_size = (orig_w, height)

    @property
    def original_size(self):
        return self._original_size

    @original_size.setter
    def original_size(self, value):
        width, height = value
        self._original_size = width, height
        self.crop_info = width, height, 0, 0
        self.image_size = width, height

    def is_multiple(self):
        return False

    def can_convert_to_webp(self):
        """
        We wouldn't want to auto-convert videos to webp, but animated gifs
        should be fair game
        """
        return self.context.config.FFMPEG_GIF_AUTO_WEBP and self.extension == '.gif'

    def resize(self, width, height):
        width, height = int(width), int(height)
        self.resized = True
        self.operations.append(('resize', (width, height)))
        logger.debug('resize {0} {1}'.format(width, height))
        self.image_size = width, height

    def crop(self, left, top, right, bottom):
        left, top, right, bottom = int(left), int(top), int(right), int(bottom)
        self.cropped = True
        self.operations.append(('crop', (left, top, right, bottom)))
        logger.debug('crop {0} {1} {2} {3}'.format(left, top, right, bottom))
        old_out_width, old_out_height, old_left, old_top = self.crop_info
        old_width, old_height = self.image_size

        width = right - left
        height = bottom - top
        self.image_size = width, height

        out_width = int(1.0 * width / old_width * old_out_width)
        out_height = int(1.0 * height / old_height * old_out_height)
        new_left = int(old_left + 1.0 * left / old_width * old_out_width)
        new_top = int(old_top + 1.0 * top / old_height * old_out_height)
        self.crop_info = out_width, out_height, new_left, new_top

    def rotate(self, degrees):
        self.operations.append(('rotate', (degrees,)))
        self.rotate_degrees = degrees

    def flip_vertically(self):
        self.operations.append(('flip_vertically', tuple()))
        self.flipped_vertically = not self.flipped_vertically

    def flip_horizontally(self):
        self.operations.append(('flip_horizontally', tuple()))
        self.flipped_horizontally = not self.flipped_horizontally

    def convert_to_grayscale(self, update_image=True, alpha=True):
        self.operations.append(('convert_to_grayscale', tuple()))
        self.grayscale = True

    # mp4 have no exif data and thus can't be auto oriented
    def reorientate(self, override_exif=True):
        pass

    def load(self, buffer, extension):
        self.extension = extension
        self.buffer = buffer
        self.operations = []
        if self.get_mimetype(buffer).startswith('image/'):
            self.image = Image.open(BytesIO(buffer))
        else:
            # self.image cannot be None, or the thumbor handler returns a 400
            self.image = ''
        self.probe()

    def has_transparency(self):
        if self.image:
            return has_transparency(self.image)
        else:
            return False

    def probe(self):
        # If self.image, we have an animated image (e.g. webp) that ffmpeg
        # cannot yet decode, but pillow can.
        if self.image:
            self.original_size = self.image.size
            duration_ms = 0
            # Load all frames, get the sum of all frames' durations
            for frame in ImageSequence.Iterator(self.image):
                frame.load()
                duration_ms += frame.info['duration']
            self.image.seek(0)
            self.duration = Decimal(duration_ms) / Decimal(1000)
        else:
            ffprobe_data = ffprobe(self.buffer, extension=self.extension)
            self.original_size = ffprobe_data['width'], ffprobe_data['height']
            self.duration = Decimal(ffprobe_data['duration'])

    def read(self, extension=None, quality=None):
        if quality is None:
            return self.buffer  # return the original data
        return self.transcode(extension)

    def transcode(self, extension):
        if getattr(self.context.request, 'format', None):
            out_format = self.context.request.format
            if out_format in ('hevc', 'h264', 'h265'):
                extension = '.mp4'
                self.context.request.format = 'mp4'
        else:
            out_format = FORMATS[extension]

        with self.make_src_file(extension) as src_file:
            if out_format == 'webp':
                return self.transcode_to_webp(src_file)
            elif out_format in ('webm', 'vp9'):
                return self.transcode_to_vp9(src_file)
            elif out_format in ('mp4', 'h264'):
                return self.transcode_to_h264(src_file)
            elif out_format in ('hevc', 'h265'):
                return self.transcode_to_h265(src_file)
            elif out_format == 'gif':
                return self.transcode_to_gif(src_file)
            else:
                raise FFmpegError("Invalid video format '%s' requested" % out_format)

    @contextmanager
    def make_src_file(self, extension):
        mime = self.get_mimetype(self.buffer)
        is_webp = mime == 'image/webp'
        if not is_webp:
            with named_tmp_file(data=self.buffer, suffix=extension) as src_file:
                yield src_file
        else:
            with make_tmp_dir() as tmp_dir:
                im = self.image
                num_frames = im.n_frames
                num_digits = len(str(num_frames))
                format_str = "%(dir)s/%(idx)0{}d.tif".format(num_digits)
                concat_buf = BytesIO()
                concat_buf.write(b"ffconcat version 1.0\n")
                concat_buf.write(b"# %dx%d\n" % im.size)
                for i, frame in enumerate(ImageSequence.Iterator(im)):
                    frame.load()
                    duration_ms = im.info['duration']
                    out_file = format_str % {'dir': tmp_dir, 'idx': i}
                    frame.save(out_file, lossless=True)
                    concat_buf.write(b"file '%s'\n" % out_file.encode('utf-8'))
                    duration_str = "%s" % (Decimal(duration_ms) / Decimal(1000))
                    concat_buf.write(b"duration %s\n" % duration_str.encode('utf-8'))
                self.buffer = concat_buf.getvalue()
                with named_tmp_file(data=self.buffer, suffix='.txt') as src_file:
                    yield src_file

    def get_config(self, prop, format):
        req_val = getattr(self.context.request, prop, None)
        if req_val is not None:
            return req_val
        else:
            config_key = ('ffmpeg_%s_%s' % (format, prop)).upper()
            return getattr(self.context.config, config_key)

    def transcode_to_webp(self, src_file):
        is_lossless = self.get_config('lossless', 'webp')
        if is_lossless or self.has_transparency():
            pix_fmt = 'rgba'
        else:
            pix_fmt = 'yuv420p'

        vf_flags = ['-vf', ','.join(self.ffmpeg_vfilters)] if self.ffmpeg_vfilters else []

        flags = [
            '-loop', '0', '-an', '-pix_fmt', pix_fmt, '-movflags', 'faststart',
        ] + vf_flags + ['-f', 'webp']

        if is_lossless:
            flags += ['-lossless', '1']
        if self.context.config.FFMPEG_WEBP_PRESET:
            flags += ['-preset', "%s" % self.context.config.FFMPEG_WEBP_PRESET]
        if self.context.config.FFMPEG_WEBP_COMPRESSION_LEVEL is not None:
            flags += [
                '-compression_level',
                "%s" % self.context.config.FFMPEG_WEBP_COMPRESSION_LEVEL]
        if self.context.config.FFMPEG_WEBP_QSCALE is not None:
            flags += ['-qscale', "%s" % self.context.config.FFMPEG_WEBP_QSCALE]

        return self.run_ffmpeg(src_file, 'webp', flags=flags, two_pass=False)

    def transcode_to_gif(self, src_file):
        with named_tmp_file(suffix='.png') as palette_file:
            if not self.use_gif_engine and self.ffmpeg_vfilters:
                libav_filter = ','.join(self.ffmpeg_vfilters)
            else:
                libav_filter = 'scale=%d:%d:flags=lanczos' % self.original_size

            input_flags = ['-f', 'concat', '-safe', '0'] if src_file.endswith('.txt') else []

            self.run_cmd([
                self.ffmpeg_path, '-hide_banner',
            ] + input_flags + [
                '-i', src_file,
                '-lavfi', "%s,palettegen" % libav_filter,
                '-y', palette_file,
            ])

            gif_buffer = self.run_cmd([
                self.ffmpeg_path, '-hide_banner',
            ] + input_flags + [
                '-i', src_file,
                '-i', palette_file,
                '-lavfi', "%s[x];[x][1:v]paletteuse" % libav_filter,
                '-f', 'gif',
                '-',
            ])

            if not self.use_gif_engine:
                return gif_buffer
            else:
                gif_engine = self.context.modules.gif_engine
                gif_engine.load(gif_buffer, '.gif')
                gif_engine.operations.append('-O3')

                for op_fn, op_args in self.operations:
                    gif_engine_method = getattr(gif_engine, op_fn)
                    gif_engine_method(*op_args)

            return gif_engine.read()

    @property
    def ffmpeg_vfilters(self):
        vfilters = []
        if self.grayscale:
            vfilters.append('hue=s=0')
        if self.flipped_vertically:
            vfilters.append('vflip')
        if self.flipped_horizontally:
            vfilters.append('hflip')
        if self.rotate_degrees != 0:
            vfilters.append('rotate={0}'.format(self.rotate_degrees))
        if self.cropped:
            vfilters.append('crop={0}'.format(':'.join([str(i) for i in self.crop_info])))
        # scale must be the last one
        if self.resized:
            vfilters.append(
                'scale={0}:flags=lanczos'.format(':'.join([str(s) for s in self.image_size])))
        return vfilters

    def transcode_to_vp9(self, src_file):
        vf_flags = ['-vf', ','.join(self.ffmpeg_vfilters)] if self.ffmpeg_vfilters else []
        flags = [
            '-c:v', 'libvpx-vp9', '-loop', '0', '-an', '-pix_fmt', 'yuv420p',
            '-movflags', 'faststart',
        ] + vf_flags + ['-f', 'webm']

        if self.context.config.FFMPEG_VP9_VBR is not None:
            flags += ['-b:v', "%s" % self.context.config.FFMPEG_VP9_VBR]
        if self.context.config.FFMPEG_VP9_CRF is not None:
            flags += ['-crf', "%s" % self.context.config.FFMPEG_VP9_CRF]
        if self.context.config.FFMPEG_VP9_DEADLINE:
            flags += ['-deadline', "%s" % self.context.config.FFMPEG_VP9_DEADLINE]
        if self.context.config.FFMPEG_VP9_CPU_USED is not None:
            flags += ['-cpu-used', "%s" % self.context.config.FFMPEG_VP9_CPU_USED]
        if self.context.config.FFMPEG_VP9_ROW_MT:
            flags += ['-row-mt', '1']
        if self.get_config('lossless', 'vp9'):
            flags += ['-lossless', '1']
        if self.context.config.FFMPEG_VP9_MAXRATE:
            flags += ['-maxrate', "%s" % self.context.config.FFMPEG_VP9_MAXRATE]
        if self.context.config.FFMPEG_VP9_MINRATE:
            flags += ['-minrate', "%s" % self.context.config.FFMPEG_VP9_MINRATE]

        two_pass = self.context.config.FFMPEG_VP9_TWO_PASS
        return self.run_ffmpeg(src_file, 'webm', flags=flags, two_pass=two_pass)

    def transcode_to_h264(self, src_file):
        width, height = self.image_size
        # libx264 width and height must be divisible by 2
        if width % 2 or height % 2:
            width = (width // 2) * 2
            height = (height // 2) * 2
            self.resize(width, height)

        vf_flags = ['-vf', ','.join(self.ffmpeg_vfilters)] if self.ffmpeg_vfilters else []

        flags = [
            '-c:v', 'libx264', '-an', '-pix_fmt', 'yuv420p', '-movflags', 'faststart',
        ] + vf_flags + ['-f', 'mp4']

        if self.get_config('tune', 'h264'):
            flags += ['-tune', self.get_config('tune', 'h264')]
        if self.context.config.FFMPEG_H264_VBR is not None:
            flags += ['-b:v', "%s" % self.context.config.FFMPEG_H264_VBR]
        if self.context.config.FFMPEG_H264_CRF is not None:
            flags += ['-crf', "%s" % self.context.config.FFMPEG_H264_CRF]
        if self.context.config.FFMPEG_H264_LEVEL:
            flags += ['-level', "%s" % self.context.config.FFMPEG_H264_LEVEL]
        if self.context.config.FFMPEG_H264_PROFILE:
            flags += ['-profile:v', "%s" % self.context.config.FFMPEG_H264_PROFILE]
        if self.context.config.FFMPEG_H264_PRESET:
            flags += ['-preset', "%s" % self.context.config.FFMPEG_H264_PRESET]
        if self.context.config.FFMPEG_H264_BUFSIZE is not None:
            flags += ['-bufsize', "%s" % self.context.config.FFMPEG_H264_BUFSIZE]
        if self.context.config.FFMPEG_H264_MAXRATE:
            flags += ['-maxrate', "%s" % self.context.config.FFMPEG_H264_MAXRATE]
        if self.context.config.FFMPEG_H264_QMIN:
            flags += ['-qmin', "%s" % self.context.config.FFMPEG_H264_QMIN]
        if self.context.config.FFMPEG_H264_QMAX:
            flags += ['-qmax', "%s" % self.context.config.FFMPEG_H264_QMAX]

        two_pass = self.context.config.FFMPEG_H264_TWO_PASS
        return self.run_ffmpeg(src_file, 'mp4', flags=flags, two_pass=two_pass)

    def transcode_to_h265(self, src_file):
        width, height = self.image_size
        # libx265 width and height must be divisible by 2
        if width % 2 or height % 2:
            width = (width // 2) * 2
            height = (height // 2) * 2
            self.resize(width, height)

        vf_flags = ['-vf', ','.join(self.ffmpeg_vfilters)] if self.ffmpeg_vfilters else []

        flags = [
            '-c:v', 'hevc', '-tag:v', 'hvc1', '-an', '-pix_fmt', 'yuv420p',
            '-movflags', 'faststart',
        ] + vf_flags + ['-f', 'mp4']

        x265_params = []

        if self.get_config('tune', 'h265'):
            flags += ['-tune', self.get_config('tune', 'h265')]
        if self.context.config.FFMPEG_H265_VBR is not None:
            flags += ['-b:v', "%s" % self.context.config.FFMPEG_H265_VBR]
        if self.context.config.FFMPEG_H265_CRF is not None:
            flags += ['-crf', "%s" % self.context.config.FFMPEG_H265_CRF]
        if self.context.config.FFMPEG_H265_PROFILE:
            flags += ['-profile:v', "%s" % self.context.config.FFMPEG_H265_PROFILE]
        if self.context.config.FFMPEG_H265_PRESET:
            flags += ['-preset', "%s" % self.context.config.FFMPEG_H265_PRESET]
        if self.context.config.FFMPEG_H265_BUFSIZE is not None:
            x265_params += ["vbv-bufsize=%s" % self.context.config.FFMPEG_H265_BUFSIZE]
        if self.context.config.FFMPEG_H265_MAXRATE:
            x265_params += ["vbv-maxrate=%s" % self.context.config.FFMPEG_H265_MAXRATE]
        if self.context.config.FFMPEG_H265_CRF_MIN:
            x265_params += ["crf-min=%s" % self.context.config.FFMPEG_H265_CRF_MIN]
        if self.context.config.FFMPEG_H265_CRF_MAX:
            x265_params += ["crf-max=%s" % self.context.config.FFMPEG_H265_CRF_MAX]

        flags += ["-x265-params", ":".join(x265_params)]

        two_pass = self.context.config.FFMPEG_H265_TWO_PASS
        return self.run_ffmpeg(src_file, 'mp4', flags=flags, two_pass=two_pass)

    def run_ffmpeg(self, input_file, out_format, flags=None, two_pass=False):
        flags = flags or []

        input_flags = []
        # text files in concat-format require additional input flags
        if input_file.endswith('.txt'):
            input_flags += ['-f', 'concat', '-safe', '0']
            txt_src = self.buffer.decode('utf-8')
            # If all frames have the same duration, set the -r flag to ensure
            # that no frames get dropped
            durations = set(re.findall(r'duration ([\d\.]+)', txt_src))
            if len(durations) == 1:
                duration = list(durations)[0]
                input_flags += ['-r', '1/%s' % duration]
                flags += ['-r', '1/%s' % duration]

        with named_tmp_file(suffix='.%s' % out_format) as out_file:
            if not two_pass:
                self.run_cmd([
                    self.ffmpeg_path, '-hide_banner',
                ] + input_flags + [
                    '-i', input_file,
                ] + flags + ['-y', out_file])
                with open(out_file, mode='rb') as f:
                    return f.read()

            with named_tmp_file(suffix='.log') as passlogfile:
                if '-x265-params' in flags:
                    params_idx = flags.index('-x265-params') + 1
                    if flags[params_idx]:
                        x265_params = flags[params_idx].split(":")
                    else:
                        x265_params = []
                    pass_one_flags = copy.copy(flags)
                    pass_two_flags = copy.copy(flags)
                    pass_one_flags[params_idx] = ":".join(
                        x265_params + ['pass=1', 'stats=%s' % passlogfile])
                    pass_two_flags[params_idx] = ":".join(
                        x265_params + ['pass=2', 'stats=%s' % passlogfile])
                else:
                    pass_one_flags = flags + [
                        '-pass', '1', '-passlogfile', passlogfile]
                    pass_two_flags = flags + [
                        '-pass', '2', '-passlogfile', passlogfile]

                self.run_cmd([
                    self.ffmpeg_path, '-hide_banner',
                ] + input_flags + [
                    '-i', input_file,
                ] + pass_one_flags + ['-y', '/dev/null'])

                self.run_cmd([
                    self.ffmpeg_path, '-hide_banner',
                ] + input_flags + [
                    '-i', input_file,
                ] + pass_two_flags + ['-y', out_file])

                with open(out_file, mode='rb') as f:
                    return f.read()

    def run_cmd(self, command):
        logger.debug("Running `%s`" % " ".join(command))
        proc = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        proc.command = command
        stdout, stderr = proc.communicate()
        logger.debug(stderr)
        if proc.returncode == 0:
            return stdout
        else:
            err_msg = "%s => %s" % (" ".join(command), proc.returncode)
            err_msg += "\n%s" % stderr
            if self.context.request:
                err_msg += "\n%s" % self.context.request.url
            raise FFmpegError(err_msg)
