Thumbor Video Engine
====================

This package provides a thumbor engine that can read, crop, and transcode mp4
and webm videos using ffmpeg.

Usage
-----

To enable this engine, add the following setting to your thumbor.conf:

.. code-block:: python

    ENGINE = 'thumbor_video_engine.engines.video'

For non-video files, this engine will fall back to using ``'thumbor.engines.pil'``.

To enable transcoding to mp4 (h264 or hevc), webm, and animated gif from other
video formats, add ``'thumbor_video_engine.filters.format'`` to your
``FILTERS`` setting. If ``'thumbor.filters.format'`` is already there, replace
it with the filter from this package.
