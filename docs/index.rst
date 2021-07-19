.. thumbor-video-engine documentation master file

====================
thumbor-video-engine
====================

thumbor-video-engine provides a thumbor engine that can read, crop, and
transcode audio-less video files. It supports input and output of animated
GIF, animated WebP, WebM (VP9) video, and MP4 (default H.264, but HEVC is also
supported).

Installation
============

.. code-block:: bash

    pip install thumbor-video-engine

Go to `GitHub <https://github.com/theatlantic/thumbor-video-engine>`_ if you
need to download or install from source, or to report any issues.

Setup
=====

In your thumbor configuration file, change the ``ENGINE`` setting to
``'thumbor_video_engine.engines.video'`` to enable video support.
This will allow thumbor to support video files in addition to whatever image
formats it already supports. If the file passed to thumbor is an image, it will
use the Engine specified by the configuration setting ``IMAGING_ENGINE``
(which defaults to ``'thumbor.engines.pil'``).

To enable transcoding between formats, add ``'thumbor_video_engine.filters.format'``
to your ``FILTERS`` setting. If ``'thumbor.filters.format'`` is already present,
replace it with the filter from this package.

.. code-block:: python

    ENGINE = 'thumbor_video_engine.engines.video'
    FILTERS = [
        'thumbor_video_engine.filters.format',
        'thumbor_video_engine.filters.still',
    ]

To enable automatic transcoding to animated gifs to webp, you can set
``FFMPEG_GIF_AUTO_WEBP`` to ``True``. To use this feature you **cannot** set
``USE_GIFSICLE_ENGINE`` to ``True``; this causes thumbor to bypass the
custom ``ENGINE`` altogether. If you still want gifsicle to handle animated
gifs you should set ``FFMPEG_USE_GIFSICLE_ENGINE`` to ``True`` and set
``GIF_ENGINE`` to ``"thumbor_video_engine.engines.gif"``.

You can also tell thumbor-video-engine to auto-transcode animated gifs to
h264 or h265 when an HTTP request has ``video/*`` in its ``Accept`` header
by enabling ``FFMPEG_GIF_AUTO_H264`` or ``FMPEG_GIF_AUTO_H265``, respectively.
If it possible to use these settings along with ``FFMPEG_GIF_AUTO_WEBP``. If
a request were to send an ``Accept`` header for both webp and video (e.g.
``image/webp, video/*``) the engine would return an h264/h265 mp4. However,
at the time this documentation is written there aren't any major browsers that
accept both webp *and* videos for images.

If your thumbor application is behind a CDN or caching proxy and you're using
any of the automatic gif transcoding options, you will need to set
``APP_CLASS`` to ``"thumbor_video_engine.app.ThumborServiceApp"`` to ensure
that thumbor returns ``Vary: Accept`` when appropriate.

If you want to use auto-mp4 gif conversion with result storage, you will need
to set your ``RESULT_STORAGE`` to one that stores the auto-converted mp4
videos separately from auto-webp or non-auto-converted gifs. This module
provides a subclassed version of ``thumbor.result_storages.file_storage`` in
``thumbor_video_engine.result_storages.file_storage``. For those using the s3
result_storage class from tc_aws you can set ``RESULT_STORAGE`` to
``thumbor_video_engine.result_storages.s3_storage`` to enable storage of gifs
autoconverted to mp4.

.. code-block:: python

    ENGINE = 'thumbor_video_engine.engines.video'
    GIF_ENGINE = 'thumbor_video_engine.engines.gif'
    FFMPEG_USE_GIFSICLE_ENGINE = True
    FFMPEG_GIF_AUTO_WEBP = True
    FFMPEG_GIF_AUTO_H265 = True
    APP_CLASS = 'thumbor_video_engine.app.ThumborServiceApp'
    RESULT_STORAGE = 'thumbor_video_engine.result_storages.file_storage'

Contents
--------

.. toctree::
   :maxdepth: 2

   configuration
   filters
   changelog

License
-------

This code is licensed under the `MIT License  <https://opensource.org/licenses/MIT>`_.
View the ``LICENSE`` file under the root directory for complete license and
copyright information.

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
