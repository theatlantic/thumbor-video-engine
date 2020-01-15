Thumbor Video Engine
====================

|build_badge| |coverage_badge| |docs_badge|

.. |build_badge| image:: https://travis-ci.org/theatlantic/thumbor-video-engine.svg?branch=master
    :target: https://travis-ci.org/theatlantic/thumbor-video-engine
.. |coverage_badge| image:: https://codecov.io/gh/theatlantic/thumbor-video-engine/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/theatlantic/thumbor-video-engine
.. |docs_badge| image:: https://readthedocs.org/projects/thumbor-video-engine/badge/?version=latest
    :target: https://thumbor-video-engine.readthedocs.io/en/latest/

This package provides a thumbor engine that can read, crop, and transcode
audio-less video files. It supports input and output of animated GIF, animated
WebP, WebM (VP9) video, and MP4 (default H.264, but HEVC is also supported).

Usage
-----

To enable this engine, add the following setting to your thumbor.conf:

.. code-block:: python

    ENGINE = 'thumbor_video_engine.engines.video'

For non-video files, this engine will fall back to using ``'thumbor.engines.pil'``.
An alternative image engine fallback can be configured by setting ``IMAGING_ENGINE``.

To enable transcoding between formats, add ``'thumbor_video_engine.filters.format'``
to your ``FILTERS`` setting. If ``'thumbor.filters.format'`` is already there,
replace it with the filter from this package.
