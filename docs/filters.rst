:tocdepth: 2

=======
Filters
=======

format(*image-or-video-format*)
===============================

`<http://thumbor-server/filters:format(webm)/some/video.mp4>`_

This filter specifies the output format of the image or video. The argument
must be one of: "png", "jpeg", "gif", "webp", "h264", "h265", or "vp9". It also
accepts aliases of "mp4" (for h264), "webm" (for vp9), and "hevc" (for h265).

still()
=======

`<http://thumbor-server/1280x800/filters:still()/some/video.mp4>`_

This filter returns the first frame of a video as a still image. The resulting
image is a jpeg by default, but this can be overridden with the format filter.

lossless()
==========

`<http://thumbor-server/filters:lossless:format(webm)/some/video.mp4>`_

This filter enables lossless encoding, if the output format supports it
(currently only animated WebP and VP9 (aka WebM)).
