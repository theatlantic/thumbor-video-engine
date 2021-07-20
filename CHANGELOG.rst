Changelog
=========

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
