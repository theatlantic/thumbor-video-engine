Changelog
=========

**1.1.0 (unreleased)***

* Added support for python 3 and thumbor 7 alpha

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
