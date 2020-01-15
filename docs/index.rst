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

In your thumbor configuration file, change the ``ENGINE`` setting to enable
video support:

.. code-block:: python

    ENGINE = 'thumbor_video_engine.engines.video'

This will allow thumbor to support video files in addition to whatever image
formats it already supports. If the file passed to thumbor is an image, it will
use the Engine specified by the configuration setting ``IMAGING_ENGINE``
(which defaults to ``'thumbor.engines.pil'``).

Contents
--------

.. toctree::
   :maxdepth: 2

   configuration
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
