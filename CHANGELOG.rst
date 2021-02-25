Changelog
=========

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
