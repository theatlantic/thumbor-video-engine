from __future__ import unicode_literals

from contextlib import contextmanager
import copy
from decimal import Decimal
from fractions import Fraction
from glob import glob
from io import BytesIO, open
import os
import re
from shutil import which
from subprocess import Popen, PIPE, DEVNULL
import threading

from PIL import Image, ImageSequence
from thumbor.engines import BaseEngine
from thumbor.utils import logger

from thumbor_video_engine.exceptions import FFmpegError
from thumbor_video_engine.ffprobe import ffprobe
from thumbor_video_engine.utils import (
    named_tmp_file, make_tmp_dir, has_transparency, parse_gif, GifParseError)


# Cap for constant-frame-rate conversion of video sources to gif; gif delays
# are whole centiseconds, so anything above 50fps quantizes badly anyway
MAX_VIDEO_GIF_FPS = Fraction(50)
DEFAULT_VIDEO_GIF_FPS = Fraction(20)


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
        self.gif_info = None
        self.source_frame_rate = None
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
        self.gif_info = None
        self.source_frame_rate = None
        mimetype = self.get_mimetype(buffer)
        if mimetype and mimetype.startswith('image/'):
            self.image = Image.open(BytesIO(buffer))
        else:
            # self.image cannot be None, or the thumbor handler returns a 400
            self.image = ''
        if bytes(buffer[:6]) in (b'GIF87a', b'GIF89a'):
            try:
                self.gif_info = parse_gif(buffer)
            except GifParseError:
                self.gif_info = None

        # Only the gif->gif path is gated; converting a GIF source to
        # video/webp/avif streams through ffmpeg with bounded memory (and is
        # the efficient way to serve a large animated gif), so it is allowed.
        max_pixels = self.context.config.MAX_ANIMATED_GIF_PIXELS
        requested_format = getattr(self.context.request, 'format', None)
        out_format = requested_format or FORMATS.get(self.extension)
        if (self.gif_info and max_pixels and out_format == 'gif'
                and self.gif_info.total_pixels > max_pixels):
            logger.warning(
                "Animated gif too large for gif output: %dx%d x %d frames "
                "(%d pixels > MAX_ANIMATED_GIF_PIXELS=%d) for url `%s`",
                self.gif_info.width, self.gif_info.height,
                self.gif_info.frame_count, self.gif_info.total_pixels,
                max_pixels, getattr(self.context.request, 'url', None))
            # engine.image == None makes the thumbor handler respond with a 400
            self.image = None
            return

        self.probe()

    def _route(self, label, method, src_file, *args):
        """Dispatch to a gif-transcode route (``method``), labelled for
        observability. Override to record per-route metrics/traces. Defaults
        to simply calling the method."""
        return method(src_file, *args)

    def has_transparency(self):
        if self.image:
            return has_transparency(self.image)
        else:
            return False

    def probe(self):
        if self.gif_info is not None:
            # Size and duration come from the single-pass block parser; no
            # need to decode every frame canvas with PIL just to sum durations
            self.original_size = self.gif_info.width, self.gif_info.height
            self.duration = self.gif_info.duration
        elif self.image:
            # An animated image (e.g. webp) that ffmpeg cannot yet decode,
            # but pillow can.
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
            self.source_frame_rate = (
                ffprobe_data.get('avg_frame_rate')
                or ffprobe_data.get('r_frame_rate'))

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
        if (self.context.config.FFMPEG_GIF_PIPELINE == 'gifski'
                and self._gifski_path() is not None):
            return self._transcode_to_gif_gifski(src_file)
        return self._route('legacy', self._gif_legacy, src_file)

    def _gifski_path(self):
        configured = self.context.config.GIFSKI_PATH
        return which(configured) if configured else which('gifski')

    def _input_flags(self, src_file):
        # text files in concat-format require additional input flags
        return ['-f', 'concat', '-safe', '0'] if src_file.endswith('.txt') else []

    def _transcode_to_gif_gifski(self, src_file):
        # gifski's quantizer working set grows with output dimensions
        # (~450MB at 1600x900 for a 125-frame animation, vs ~200MB for the
        # legacy pipeline); above the threshold, trade wall time for bounded
        # subprocess memory.
        width, height = self.image_size
        max_target = self.context.config.GIFSKI_MAX_TARGET_PIXELS
        if max_target and width * height > max_target:
            return self._gifski_oversized_target(src_file)

        info = self.gif_info
        if info is None:
            if self.image:
                # Animated webp input (or an unparseable gif that PIL could
                # still open): per-frame timing is unknown to us, so use the
                # timing-exact legacy path.
                return self._route('legacy', self._gif_legacy, src_file)
            # Video source: constant frame rate from ffprobe
            return self._route(
                'y4m', self._gifski_y4m, src_file, self._video_fps(), "0")

        if not info.is_uniform_delay:
            # Variable frame delays can't be represented in a constant frame
            # rate y4m stream; the legacy path preserves them exactly.
            return self._route('legacy', self._gif_legacy, src_file)

        repeat = "-1" if info.loop_count is None else str(info.loop_count)
        if self._gif_visibly_transparent(info):
            return self._route(
                'png', self._gifski_png_frames, src_file, info.uniform_fps, repeat)
        return self._route(
            'y4m', self._gifski_y4m, src_file, info.uniform_fps, repeat)

    def _gifski_oversized_target(self, src_file):
        """Chosen when the target output exceeds ``GIFSKI_MAX_TARGET_PIXELS``
        (gifski's quantizer memory grows with output size). Override to serve
        something faster (e.g. a quick low-quality pass with a background
        re-encode). Defaults to the bounded-memory legacy path."""
        return self._route('legacy_large', self._gif_legacy, src_file)

    def _gif_visibly_transparent(self, info):
        """GCE transparency flags over-approximate: optimized opaque GIFs
        routinely set them for inter-frame patching. Check whether frame 0
        actually has non-opaque pixels (cheap: one frame), and whether any
        frame can expose the background via disposal. False positives just
        take the PNG route, which is also correct for opaque GIFs."""
        if not info.has_transparency_flags:
            return False
        try:
            if self.has_transparency():
                return True
        except Exception:
            return True
        return info.has_transparent_disposal

    def _video_fps(self):
        try:
            fps = Fraction(self.source_frame_rate)
        except (TypeError, ValueError, ZeroDivisionError):
            fps = DEFAULT_VIDEO_GIF_FPS
        if fps <= 0:
            fps = DEFAULT_VIDEO_GIF_FPS
        return min(fps, MAX_VIDEO_GIF_FPS)

    def _gifski_quality(self):
        """Quality (1-100) passed to gifski. Override to vary it per request
        (e.g. a low-quality fast pass)."""
        return self.context.config.GIFSKI_QUALITY

    def _gifski_extra_args(self):
        """Extra flags for the gifski command (e.g. ``['--fast']``). Override
        to add them; defaults to none."""
        return []

    def _gifski_gifsicle_pass(self):
        """Whether to run a final geometry-free ``gifsicle -O3`` pass over
        gifski's output. Override to vary it per request (e.g. skip it for a
        quick low-quality pass). Defaults to the ``GIFSKI_GIFSICLE_PASS``
        config."""
        return self.context.config.GIFSKI_GIFSICLE_PASS

    def _gifski_cmd(self, out_file, fps):
        width, height = self.image_size
        return [
            self._gifski_path(),
            "--quiet",
            "--quality", "%s" % self._gifski_quality(),
        ] + self._gifski_extra_args() + [
            "--fps", "%g" % float(fps),
            # gifski caps output at ~800x600 unless explicitly sized; frames
            # are already scaled to exactly this size by ffmpeg
            "--width", "%d" % width,
            "--height", "%d" % height,
            "-o", out_file,
        ]

    def _gifski_y4m(self, src_file, fps, repeat):
        vf = self.ffmpeg_vfilters + ["fps=%s" % fps]
        ffmpeg_cmd = (
            [self.ffmpeg_path, "-hide_banner", "-loglevel", "error"]
            + self._input_flags(src_file)
            + [
                "-i", src_file,
                "-an",
                "-vf", ",".join(vf),
                "-pix_fmt", "yuv444p",
                "-f", "yuv4mpegpipe",
                "-",
            ]
        )
        with named_tmp_file(suffix=".gif") as out_file:
            gifski_cmd = self._gifski_cmd(out_file, fps) + ["--repeat", repeat, "-"]
            self._run_pipeline(ffmpeg_cmd, gifski_cmd)
            if self._gifski_gifsicle_pass():
                return self._gifsicle_optimize_file(out_file)
            with open(out_file, mode="rb") as f:
                return f.read()

    def _gifski_png_frames(self, src_file, fps, repeat):
        vf = self.ffmpeg_vfilters + ["fps=%s" % fps]
        with make_tmp_dir() as tmp_dir:
            self.run_cmd(
                [self.ffmpeg_path, "-hide_banner", "-loglevel", "error"]
                + self._input_flags(src_file)
                + [
                    "-i", src_file,
                    "-an",
                    "-vf", ",".join(vf),
                    # gifski preserves alpha from PNG input. -compression_level 0
                    # makes the (lossless) dump much faster at the cost of
                    # scratch disk.
                    "-compression_level", "0",
                    os.path.join(tmp_dir, "%05d.png"),
                ]
            )
            frame_files = sorted(glob(os.path.join(tmp_dir, "*.png")))
            if not frame_files:
                raise FFmpegError(
                    "ffmpeg produced no frames for url `%s`"
                    % getattr(self.context.request, "url", None))
            with named_tmp_file(suffix=".gif") as out_file:
                gifski_cmd = (
                    self._gifski_cmd(out_file, fps)
                    + ["--repeat", repeat]
                    + frame_files
                )
                self.run_cmd(gifski_cmd)
                if self._gifski_gifsicle_pass():
                    return self._gifsicle_optimize_file(out_file)
                with open(out_file, mode="rb") as f:
                    return f.read()

    def _run_pipeline(self, src_cmd, sink_cmd):
        """Run ``src_cmd | sink_cmd``, streaming src's stdout into sink's
        stdin. Raises :class:`FFmpegError` if either process exits non-zero."""
        logger.debug("Running `%s | %s`", " ".join(src_cmd), " ".join(sink_cmd))
        src_proc = Popen(src_cmd, stdout=PIPE, stderr=PIPE, stdin=DEVNULL)
        try:
            sink_proc = Popen(
                sink_cmd, stdin=src_proc.stdout, stdout=DEVNULL, stderr=PIPE)
        except Exception:
            src_proc.kill()
            src_proc.stdout.close()
            src_proc.stderr.close()
            src_proc.wait()
            raise
        # Drop our duplicate of the write end so that, if the sink dies, the
        # source gets SIGPIPE instead of blocking forever
        src_proc.stdout.close()

        src_stderr = []

        def drain():
            src_stderr.append(src_proc.stderr.read())
            src_proc.stderr.close()

        drain_thread = threading.Thread(target=drain)
        drain_thread.start()
        try:
            _, sink_stderr = sink_proc.communicate()
        finally:
            src_proc.wait()
            drain_thread.join()

        if src_proc.returncode != 0 or sink_proc.returncode != 0:
            err_msg = "%s | %s => %s, %s" % (
                " ".join(src_cmd), " ".join(sink_cmd),
                src_proc.returncode, sink_proc.returncode)
            err_msg += "\n%s\n%s" % (
                b"".join(src_stderr).decode("utf-8", "replace"),
                (sink_stderr or b"").decode("utf-8", "replace"))
            if self.context.request:
                err_msg += "\n%s" % self.context.request.url
            raise FFmpegError(err_msg)

    def _gif_legacy(self, src_file):
        """The palettegen/paletteuse pipeline. Geometry is applied at the
        target size in ffmpeg (rather than re-encoding at original resolution
        and letting gifsicle resize), and output goes through a temp file
        rather than buffering the whole animation on stdout. Because ffmpeg
        performs all geometry, the gifsicle stage (when FFMPEG_USE_GIFSICLE_ENGINE
        is on) is purely a geometry-free optimization pass."""
        vf = ",".join(self.ffmpeg_vfilters) if self.ffmpeg_vfilters else "null"
        input_flags = self._input_flags(src_file)

        with named_tmp_file(suffix=".png") as palette_file:
            self.run_cmd(
                [self.ffmpeg_path, "-hide_banner"]
                + input_flags
                + [
                    "-i", src_file,
                    "-lavfi", "%s,palettegen" % vf,
                    "-y", palette_file,
                ]
            )
            with named_tmp_file(suffix=".gif") as out_file:
                self.run_cmd(
                    [self.ffmpeg_path, "-hide_banner"]
                    + input_flags
                    + [
                        "-i", src_file,
                        "-i", palette_file,
                        "-lavfi", "%s[x];[x][1:v]paletteuse" % vf,
                        "-f", "gif",
                        "-y", out_file,
                    ]
                )
                if self.use_gif_engine:
                    return self._gifsicle_optimize_file(out_file)
                with open(out_file, mode="rb") as f:
                    return f.read()

    def _gifsicle_optimize_file(self, src_path):
        """Run a geometry-free ``gifsicle -O3`` (plus GIFSICLE_ARGS) over a
        file on the scratch filesystem. Working file-to-file keeps the
        whole-animation buffers out of the Python heap entirely: only the
        final optimized bytes are ever read."""
        gifsicle_path = (
            getattr(self.context.server, "gifsicle_path", None)
            or self.context.config.GIFSICLE_PATH
            or which("gifsicle"))
        if not gifsicle_path:
            raise FFmpegError(
                "a gifsicle optimization pass was requested (via "
                "FFMPEG_USE_GIFSICLE_ENGINE or GIFSKI_GIFSICLE_PASS) but the "
                "gifsicle binary cannot be found")
        extra_args = [
            str(arg) for arg in (self.context.config.GIFSICLE_ARGS or [])]
        with named_tmp_file(suffix=".gif") as out_file:
            self.run_cmd(
                [gifsicle_path, "-O3"] + extra_args + [src_path, "-o", out_file])
            with open(out_file, mode="rb") as f:
                buf = f.read()
        # Mirror thumbor's gif engine: make sure gifsicle produced a valid
        # gif before returning it
        try:
            with BytesIO(buf) as verify_buf:
                Image.open(verify_buf).verify()
        except Exception:
            raise FFmpegError(
                "gifsicle produced invalid output for url `%s`"
                % getattr(self.context.request, "url", None))
        return buf

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
