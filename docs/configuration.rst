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

The path to the gifsicle binary. It defaults to ``None``, in which case it
looks for gifsicle in ``PATH``. This is only used if ``GIF_ENGINE`` is set to
``'thumbor_video_engines.engines.gif'``. As of version 6.7.0, thumbor does not
support configuring this value.

FFMPEG\_USE\_GIFSICLE\_ENGINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Equivalent to USE\_GIFSICLE\_ENGINE, but for the FFmpeg engine. It defaults to
``False``. If ``True``, it will perform any image operations on animated gifs
(e.g. cropping and resizing) using gifsicle (by way of ``GIF_ENGINE``).

FFMPEG\_HANDLE\_ANIMATED\_GIF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Whether to process animated gifs with the FFmpeg engine. It defaults to
``True``.

FFMPEG\_GIF\_AUTO\_WEBP
~~~~~~~~~~~~~~~~~~~~~~~

Specifies whether animated WebP format should be used automatically if the
source image is an animated gif and the request accepts it (via Accept header).
It defaults to ``True``, but only works when ``AUTO_WEBP`` is also enabled.

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
