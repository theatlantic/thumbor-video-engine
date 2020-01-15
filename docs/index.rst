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
