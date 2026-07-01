=============
Configuration
=============

All configuration values default to ``None`` unless otherwise specified.
For FFmpeg codec settings, a ``None`` value means that it uses ffmpeg's
own default value for when the flag is unspecified.

Here are some general resources on ffmpeg's encoding flags, and how to choose
encoding settings that fit your use-case.

- `Understanding Rate Control Modes`_
- `Google: VP9 Overview`_
- `FFmpeg H.264 Encoding Guide`_
- `FFmpeg H.265 Encoding Guide`_
- `FFmpeg VP9 Encoding Guide`_
- `FFmpeg codecs documentation`_

.. _Understanding Rate Control Modes: https://slhck.info/video/2017/03/01/rate-control.html
.. _`Google: VP9 Overview`: https://developers.google.com/media/vp9
.. _FFmpeg H.264 Encoding Guide: https://trac.ffmpeg.org/wiki/Encode/H.264
.. _FFmpeg H.265 Encoding Guide: https://trac.ffmpeg.org/wiki/Encode/H.265
.. _FFmpeg VP9 Encoding Guide: https://trac.ffmpeg.org/wiki/Encode/VP9
.. _FFmpeg codecs documentation: http://ffmpeg.org/ffmpeg-codecs.html#Options-27


General
-------

IMAGE\_ENGINE
~~~~~~~~~~~~~

The engine to use for non-video files. It defaults to
``'thumbor.engines.pil'``, which is thumbor's default value for
``ENGINE``

FFMPEG\_ENGINE
~~~~~~~~~~~~~~

The engine to use for video files. It defaults to
``'thumbor_video_engine.engines.ffmpeg'``.

GIFSICLE\_PATH
~~~~~~~~~~~~~~

The path to the gifsicle binary. It defaults to ``None``, in which case gifsicle
is looked up on ``PATH``. It is honored both by the FFmpeg engine's animated-gif
optimization pass (when ``FFMPEG_USE_GIFSICLE_ENGINE`` is enabled) and by the gif
engine for non-animated gifs (when ``GIF_ENGINE`` is set to
``'thumbor_video_engine.engines.gif'``).

GIFSICLE\_ARGS
~~~~~~~~~~~~~~

A list of additional args to pass to gifsicle (e.g. ``['--lossy=80']``). Honored
by the FFmpeg engine's animated-gif optimization pass (when
``FFMPEG_USE_GIFSICLE_ENGINE`` is enabled), by the gifski pipeline's optional
``GIFSKI_GIFSICLE_PASS``, and by the gif engine for non-animated gifs (when
``GIF_ENGINE`` is ``'thumbor_video_engine.engines.gif'``).

FFMPEG\_USE\_GIFSICLE\_ENGINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Equivalent to USE\_GIFSICLE\_ENGINE, but for the FFmpeg engine. It defaults to
``False``. If ``True``, gifsicle runs as a final ``-O3`` optimization pass
(plus ``GIFSICLE_ARGS``) over the gif produced by ffmpeg, reducing file size.
All geometry (cropping, resizing) is applied by ffmpeg at the target size, so
the gifsicle pass performs no resizing of its own and runs file-to-file on
disk — the full animation is never buffered in the Python heap.

This pass invokes ``gifsicle`` directly rather than routing through
``GIF_ENGINE``, so a custom ``GIF_ENGINE`` does not participate in animated-gif
transcodes (it is still used for non-animated gifs). To customize the
animated-gif optimization step, subclass the FFmpeg engine (``FFMPEG_ENGINE``)
and override ``_gif_legacy`` or ``_gifsicle_optimize_file``.

FFMPEG\_HANDLE\_ANIMATED\_GIF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Whether to process animated gifs with the FFmpeg engine. It defaults to
``True``.

FFMPEG\_GIF\_AUTO\_WEBP
~~~~~~~~~~~~~~~~~~~~~~~

Specifies whether animated WebP format should be used automatically if the
source image is an animated gif and the request accepts it (via Accept header).
It defaults to ``True``, but only works when ``AUTO_WEBP`` is also enabled.

FFMPEG\_GIF\_AUTO\_H264
~~~~~~~~~~~~~~~~~~~~~~~

Specifies whether H264 format should be used automatically if the
source image is an animated gif and the request accepts it (via
``Accept: video/*``). It defaults to ``False``.

FFMPEG\_GIF\_AUTO\_H265
~~~~~~~~~~~~~~~~~~~~~~~

Specifies whether H265 format should be used automatically if the
source image is an animated gif and the request accepts it (via
``Accept: video/*``). It defaults to ``False``.

FFMPEG\_GIF\_PIPELINE
~~~~~~~~~~~~~~~~~~~~~

Selects the gif-to-gif transcode pipeline. It defaults to ``'legacy'``.

``'legacy'``
    The ``palettegen``/``paletteuse`` pipeline. ffmpeg applies all geometry
    (crop, resize) at the **target** size, writes intermediates to disk, and
    — when ``FFMPEG_USE_GIFSICLE_ENGINE`` is enabled — runs a final
    geometry-free ``gifsicle -O3`` optimization pass. Only the final output
    bytes ever enter the Python heap, so memory stays bounded regardless of
    the source animation's resolution or frame count.

``'gifski'``
    Streams frames from ffmpeg directly into the `gifski`__ encoder at the
    target size, producing noticeably higher-quality gifs much faster. Inputs
    that gifski cannot represent are routed back to the ``legacy`` path
    automatically:

    - **variable per-frame delays** (gifski emits a constant frame rate),
    - **target sizes above** ``GIFSKI_MAX_TARGET_PIXELS``,
    - and any request when the ``gifski`` binary is not available.

    Visibly-transparent gifs are decoded to PNG frames first (gifski
    preserves alpha from PNG input); opaque gifs and video sources stream
    through a ``yuv4mpegpipe``.

    .. note::
        gifski is licensed under the `AGPL-3.0`__. thumbor-video-engine
        invokes it as an unmodified subprocess (aggregation, not linking) and
        never declares it as a dependency. You must install the ``gifski``
        binary yourself to use this pipeline, and your deployment is
        responsible for AGPL compliance.

.. __: https://gif.ski/
.. __: https://www.gnu.org/licenses/agpl-3.0.html

GIFSKI\_PATH
~~~~~~~~~~~~

Path to the gifski binary. It defaults to ``None``, in which case gifski is
looked up on ``PATH``. Only used when ``FFMPEG_GIF_PIPELINE`` is ``'gifski'``.

GIFSKI\_QUALITY
~~~~~~~~~~~~~~~

Quality (1–100) passed to gifski (``--quality``). Defaults to ``90``.

GIFSKI\_MAX\_TARGET\_PIXELS
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Above this output size (target ``width * height``), the gifski pipeline routes
through the legacy path instead. gifski's quantizer working set grows with
output dimensions, while the legacy path's memory stays bounded — this trades
a bit of wall time for bounded subprocess memory on large outputs. Defaults to
``1440000`` (1600×900). A value of ``0`` disables the switch.

GIFSKI\_GIFSICLE\_PASS
~~~~~~~~~~~~~~~~~~~~~~

If ``True``, run a final geometry-free ``gifsicle -O3`` pass (plus
``GIFSICLE_ARGS``, e.g. ``--lossy``) over gifski's output to further reduce
file size. Defaults to ``False``.

MAX\_ANIMATED\_GIF\_PIXELS
~~~~~~~~~~~~~~~~~~~~~~~~~~

Maximum total pixels (``width * height * frame_count``) for an animated **gif
source that is being transcoded to gif**. Sources over this limit fail with a
``400`` response. thumbor's ``MAX_PIXELS`` is per-frame and does not bound frame
count, so a high-frame-count gif can still be expensive; this gate, evaluated
cheaply at load time from a single-pass header parse (no frame decoding), bounds
the total.

Only the gif→gif path is gated. Converting a GIF source to video/webp/avif
(including the automatic conversions from ``FFMPEG_GIF_AUTO_H264`` /
``FFMPEG_GIF_AUTO_H265`` / ``FFMPEG_GIF_AUTO_WEBP``) streams through ffmpeg with
bounded memory and is the efficient way to serve a large animated gif, so those
are not affected. Defaults to ``0``, which disables the check.

FFPROBE\_PATH
~~~~~~~~~~~~~

Path for the ffprobe binary. It defaults to ``'/usr/local/bin/ffprobe'``.


H.264 (MP4)
-----------

FFMPEG\_H264\_TWO\_PASS
~~~~~~~~~~~~~~~~~~~~~~~

Whether to use `two-pass encoding`__ for h264 in FFmpeg. Default ``False``.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#twopass


FFMPEG\_H264\_CRF
~~~~~~~~~~~~~~~~~

`-crf`__. The constant quality to use by FFmpeg for h264 encoding.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#crf


FFMPEG\_H264\_VBR
~~~~~~~~~~~~~~~~~

`-b:v`__: The average bitrate to be used by FFmpeg for h264 encoding.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#CBRConstantBitRate

FFMPEG\_H264\_MINRATE
~~~~~~~~~~~~~~~~~~~~~

`-minrate`__: minimum bound for bitrate.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#ConstrainedencodingVBVmaximumbitrate


FFMPEG\_H264\_MAXRATE
~~~~~~~~~~~~~~~~~~~~~

`-maxrate`__: maximum bound for bitrate.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#ConstrainedencodingVBVmaximumbitrate


FFMPEG\_H264\_BUFSIZE
~~~~~~~~~~~~~~~~~~~~~

`-bufsize`__: The rate control buffer. Used to determine the range across
which the requested average bitrate and min/max should be enforced.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#ConstrainedencodingVBVmaximumbitrate

FFMPEG\_H264\_PRESET
~~~~~~~~~~~~~~~~~~~~

`-preset`__. A collection of options that will provide a certain
encoding speed to compression ratio. A slower preset will provide better
compression (compression is quality per filesize). This means that, for
example, if you target a certain file size or constant bit rate, you will
achieve better quality with a slower preset. Similarly, for constant quality
encoding, you will simply save bitrate by choosing a slower preset.

Use the slowest preset that you have patience for. The available presets in
descending order of speed are: *ultrafast*, *superfast*, *veryfast*,
*faster*, *fast*, *medium* (default), *slow*, *slower*, *veryslow*

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#Preset

FFMPEG\_H264\_PROFILE
~~~~~~~~~~~~~~~~~~~~~

`-profile`__: Determines h264 compatibility version.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#Compatibility

FFMPEG\_H264\_LEVEL
~~~~~~~~~~~~~~~~~~~

`-level`__: Controls h264 feature set, which affects device compatibility.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#Compatibility

FFMPEG\_H264\_TUNE
~~~~~~~~~~~~~~~~~~

`-tune`__: Change settings based upon the specifics of your input

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#Tune

FFMPEG\_H264\_QMIN
~~~~~~~~~~~~~~~~~~

-qmin: Set the minimum video quantizer scale.

FFMPEG\_H264\_QMAX
~~~~~~~~~~~~~~~~~~

-qmax: Set the maximum video quantizer scale.

H.265 (aka HEVC)
----------------

`FFmpeg H.265 Encoding Guide`_

.. _`FFmpeg H.265 Encoding Guide`: https://trac.ffmpeg.org/wiki/Encode/H.265

FFMPEG\_H265\_TWO\_PASS
~~~~~~~~~~~~~~~~~~~~~~~

Whether to use `two-pass encoding`__ for h265 encoding. Default ``False``.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.265#Two-PassEncoding

FFMPEG\_H265\_PRESET
~~~~~~~~~~~~~~~~~~~~

`-preset`__. A collection of options that will provide a certain
encoding speed to compression ratio. Same values as h264

.. __: https://x265.readthedocs.io/en/default/cli.html#cmdoption-preset

FFMPEG\_H265\_LEVEL
~~~~~~~~~~~~~~~~~~~

`-level`__: Controls h265 feature set, which affects device compatibility.

.. __: https://x265.readthedocs.io/en/default/cli.html#cmdoption-level-idc

FFMPEG\_H265\_MAXRATE
~~~~~~~~~~~~~~~~~~~~~

The `--vbv-maxrate`__ flag passed to FFmpeg for h265 encoding.

.. __: https://x265.readthedocs.io/en/default/cli.html#quality-rate-control-and-rate-distortion-options

FFMPEG\_H265\_BUFSIZE
~~~~~~~~~~~~~~~~~~~~~

The `--vbv-bufsize`__ flag passed to libx265.

.. __: https://x265.readthedocs.io/en/default/cli.html#quality-rate-control-and-rate-distortion-options

FFMPEG\_H265\_CRF\_MIN
~~~~~~~~~~~~~~~~~~~~~~

The `--crf-min`__ flag passed to libx265.

.. __: https://x265.readthedocs.io/en/default/cli.html#quality-rate-control-and-rate-distortion-options

FFMPEG\_H265\_CRF\_MAX
~~~~~~~~~~~~~~~~~~~~~~

The `--crf-max`__ flag passed to libx265.

.. __: https://x265.readthedocs.io/en/default/cli.html#quality-rate-control-and-rate-distortion-options


FFMPEG\_H265\_PROFILE
~~~~~~~~~~~~~~~~~~~~~

`-profile`__: Determines h265 compatibility version.

.. __: https://x265.readthedocs.io/en/default/cli.html#cmdoption-profile

FFMPEG\_H265\_TUNE
~~~~~~~~~~~~~~~~~~

`-tune`__: Change settings based upon the specifics of your input. Same as
h264.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.264#Tune

FFMPEG\_H265\_CRF
~~~~~~~~~~~~~~~~~

`-crf`__: the constant quality to use by FFmpeg for h264 encoding.

.. __: https://trac.ffmpeg.org/wiki/Encode/H.265#ConstantRateFactorCRF

FFMPEG\_H265\_VBR
~~~~~~~~~~~~~~~~~

`-b:v`__: The average bitrate to be used by FFmpeg for h265 encoding.

.. __: https://x265.readthedocs.io/en/default/cli.html#cmdoption-bitrate

VP9 (WebM)
----------

FFMPEG\_VP9\_TWO\_PASS
~~~~~~~~~~~~~~~~~~~~~~

Whether to use `two-pass encoding`__ for VP9 in FFmpeg. Default ``False``.

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#twopass

FFMPEG\_VP9\_VBR
~~~~~~~~~~~~~~~~

`-b:v`__. The average bitrate to be used by FFmpeg for VP9 encoding.

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#averageb

FFMPEG\_VP9\_LOSSLESS
~~~~~~~~~~~~~~~~~~~~~

`-lossless`__. Whether to enable lossless encoding for VP9. Default ``False``.

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#LosslessVP9

FFMPEG\_VP9\_DEADLINE
~~~~~~~~~~~~~~~~~~~~~

`-deadline`__: can be set to:

:good:
    the default and recommended for most applications.

:best:
    recommended if you have lots of time and want the best compression
    efficiency.

:realtime:
    recommended for live / fast encoding.

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#DeadlineQuality

FFMPEG\_VP9\_CRF
~~~~~~~~~~~~~~~~

`-crf`__. The constant quality to use by FFmpeg for VP9 encoding.

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#constantq

FFMPEG\_VP9\_CPU\_USED
~~~~~~~~~~~~~~~~~~~~~~

`-cpu-used`__: Affects compilation speed and quality trade-off

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#CPUUtilizationSpeed

FFMPEG\_VP9\_ROW\_MT
~~~~~~~~~~~~~~~~~~~~

`-row-mt`__. Whether to enable row-based multithreading for VP9 encoding.

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#rowmt

FFMPEG\_VP9\_MINRATE
~~~~~~~~~~~~~~~~~~~~

`-minrate`__: minimum bound for bitrate.

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#constrainedq

FFMPEG\_VP9\_MAXRATE
~~~~~~~~~~~~~~~~~~~~

`-maxrate`__: maximum bound for bitrate.

.. __: https://trac.FFmpeg.org/wiki/Encode/VP9#constrainedq

Animated WebP
-------------

FFMPEG\_WEBP\_LOSSLESS
~~~~~~~~~~~~~~~~~~~~~~

-lossless: enables/disables use of lossless mode. libwebp default is ``False``.

FFMPEG\_WEBP\_COMPRESSION\_LEVEL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-compression_level: range 0-6, default 4. Higher values give better quality
but slower speed. For lossless, it controls the size/speed trade-off.

FFMPEG\_WEBP\_QSCALE
~~~~~~~~~~~~~~~~~~~~

-qscale: For lossy encoding, controls quality 0 to 100. For lossless, controls
cpu and time spent compressing. libwebp built-in default 75.

FFMPEG\_WEBP\_PRESET
~~~~~~~~~~~~~~~~~~~~

-preset Configuration preset. Consult `FFmpeg libwebp codec documentation`__
for more information.

.. __: http://ffmpeg.org/ffmpeg-codecs.html#Options-27

Example Configuration
---------------------

.. code-block:: python

    ENGINE = 'thumbor_video_engine.engines.video'
    FFMPEG_USE_GIFSICLE_ENGINE = True
    FFMPEG_PATH = '/usr/bin/ffmpeg'
    FFPROBE_PATH = '/usr/bin/ffprobe'
    FFMPEG_H264_MAXRATE = '1200k'
    FFMPEG_H264_BUFSIZE = '2400k'
    FFMPEG_H264_CRF = 24
    FFMPEG_H265_MAXRATE = '1500'
    FFMPEG_H265_BUFSIZE = '3000'
    FFMPEG_H265_CRF = 28
    FFMPEG_VP9_VBR = '2M'
    FFMPEG_VP9_CRF = 30
    FFMPEG_VP9_MINRATE = '1500k'
    FFMPEG_VP9_MAXRATE = '2500k'
    FFMPEG_VP9_CPU_USED = 4
    FFMPEG_VP9_ROW_MT = True
    FFMPEG_WEBP_COMPRESSION_LEVEL = 3
    FFMPEG_WEBP_QSCALE = 80
