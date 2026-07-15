Changelog
=========

**1.3.1 (Jul 15, 2026)**

* Renamed the misleadingly-named ``_route`` method on the ffmpeg engine to
  ``_gif_route``.

**1.3.0 (Jul 13, 2026)**

* Fixed: animated-gif transcodes no longer exhaust memory on large inputs.
  ``probe()`` now reads gif size and duration from a single-pass header parser
  (``thumbor_video_engine.utils.parse_gif``) instead of decoding every frame
  with Pillow, and ``transcode_to_gif()`` applies all geometry in ffmpeg at the
  target size with on-disk intermediates. When ``FFMPEG_USE_GIFSICLE_ENGINE`` is
  enabled, gifsicle now runs as a geometry-free ``-O3`` optimization pass
  file-to-file rather than loading the full-resolution animation into thumbor's
  gif engine. Python heap usage is now bounded regardless of source resolution
  or frame count.
* **Behavior change:** for animated gifs, the ffmpeg engine's gifsicle
  optimization pass now invokes ``gifsicle`` directly (still honoring
  ``GIFSICLE_PATH`` and ``GIFSICLE_ARGS``) on the already-resized output,
  instead of routing through ``GIF_ENGINE``. ``GIF_ENGINE`` is still used for
  non-animated gifs. If you set ``GIF_ENGINE`` to a subclass of
  ``thumbor_video_engine.engines.gif.Engine`` in order to customize *animated*
  gif handling, those overrides no longer take effect there; move them into a
  subclass of the ffmpeg engine (``FFMPEG_ENGINE``) that overrides
  ``_gif_legacy`` or ``_gifsicle_optimize_file``.
* Feature: optional streaming ``gifski`` pipeline, enabled with
  ``FFMPEG_GIF_PIPELINE = 'gifski'`` (plus ``GIFSKI_PATH``, ``GIFSKI_QUALITY``,
  ``GIFSKI_MAX_TARGET_PIXELS``, ``GIFSKI_GIFSICLE_PASS``). Streams frames from
  ffmpeg into gifski at the target size for faster, higher-quality gifs, falling
  back to the legacy pipeline for variable-delay gifs, oversized targets, or when
  the gifski binary is absent. gifski is AGPL-3.0 and is never a hard dependency;
  it is invoked as an unmodified subprocess only when configured.
* Feature: ``MAX_ANIMATED_GIF_PIXELS`` rejects an animated-GIF source whose
  ``width * height * frame_count`` exceeds the limit with a ``400`` response,
  but only when the output is also gif (conversions to video/webp/avif are
  memory-bounded and unaffected). Disabled by default.
* Drop support for python 2.7 and thumbor 6

**1.2.5 (Jul 8, 2024)**

* Fixed: Compatibility with the thumbor "fill" filter. Fixes `#12`_.
* Fixed: Allow the same base formats as thumbor in the format filter. Fixes
  `#23`_.

.. _#12: https://github.com/theatlantic/thumbor-video-engine/issues/12
.. _#23: https://github.com/theatlantic/thumbor-video-engine/issues/23

**1.2.4 (Jan 4, 2024)**

* Feature: support thumbor-aws result storage

**1.2.3 (Feb 15, 2022)**

* Fixed: issue with using the still filter in conjunction with the watermark
  filter. Fixes #2.

**1.2.2 (Aug 14, 2021)**

* Support source videos in quicktime/mov format. Fixes #9.

**1.2.1 (Jul 20, 2021)**

* Ensure that ``Vary: Accept`` header is returned for requests to animated
  gifs that can be auto-converted to other formats when that image is
  returned from result storage.

**1.2.0 (Jul 19, 2021)**

* Added an ``APP_CLASS`` ``"thumbor_video_engine.app.ThumborServiceApp"``
  that ensures appropriate ``Vary: Accept`` header is returned for requests
  that automatically convert animated gifs based on Accept headers.
* Added settings ``FFMPEG_GIF_AUTO_H264`` and ``FFMPEG_GIF_AUTO_H265`` that
  enable auto-conversion of animated gifs to H264 or H265 (respectively) when
  ``video/*`` is present in a request's ``Accept`` header.
* Added custom result storage classes that ensures animated gifs auto-converted
  to mp4 are stored distinctly from animated gifs or auto-webp images.

**1.1.1 (Feb 25, 2021)**

* Added ``GIFSICLE_ARGS`` setting, which allows customization of arguments
  passed to the gifsicle binary.

**1.1.0 (May 29, 2020)***

* Added support for python 3 and thumbor 7 alpha
* Fixed: conversion to animated webp now retains alpha transparency (from gif or webp)

**1.0.2 (Jan 11, 2020)**

* Feature: Support auto conversion of animated gif to animated webp if
  ``AUTO_WEBP`` is ``True``.
* Fixed: Ensure that all mp4s, regardless of ``ftyp`` box size, are recognized
  as such.

**1.0.1 (Jan 8, 2020)**

* Fixed: Addressed an issue where frames would sometimes get dropped when
  transcoding animated webp files.

**1.0.0 (Jan 2, 2020)**

* Initial release
