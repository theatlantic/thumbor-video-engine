from thumbor.config import Config


__version__ = "1.3.0"


Config.define(
    'IMAGE_ENGINE',
    'thumbor.engines.pil',
    'The engine to use for non-video files',
    'Imaging')

Config.define(
    'FFMPEG_ENGINE',
    'thumbor_video_engine.engines.ffmpeg',
    'The engine to use for video files',
    'Video')

Config.define(
    'GIFSICLE_PATH',
    None,
    'The path to the gifsicle binary',
    'Imaging')

Config.define(
    'GIFSICLE_ARGS',
    [],
    'Additional CLI arguments to pass to gifsicle',
    'Imaging')

Config.define(
    'FFMPEG_USE_GIFSICLE_ENGINE',
    False,
    'Equivalent to USE_GIFSICLE_ENGINE, but for the ffmpeg engine',
    'Video')

Config.define(
    'FFMPEG_GIF_PIPELINE',
    'legacy',
    "Which GIF->GIF transcode pipeline to use. 'legacy' uses the "
    "palettegen/paletteuse pipeline (scaling to the target size in ffmpeg, "
    "with on-disk intermediates and, when FFMPEG_USE_GIFSICLE_ENGINE is on, "
    "a final geometry-free gifsicle -O3 optimization pass). 'gifski' streams "
    "frames from ffmpeg into the gifski encoder at the target size, falling "
    "back to the legacy path for inputs gifski cannot represent (variable "
    "frame delays) or when the gifski binary is not available.",
    'Video')

Config.define(
    'GIFSKI_PATH',
    None,
    'Path to the gifski binary. If None, gifski is looked up on PATH. Only '
    'used when FFMPEG_GIF_PIPELINE is "gifski". Note: gifski is licensed '
    'under the AGPL-3.0; it is invoked as an unmodified subprocess and is '
    'never a hard dependency of this package.',
    'Video')

Config.define(
    'GIFSKI_QUALITY',
    90,
    'Quality (1-100) passed to gifski (--quality) when encoding GIFs',
    'Video')

Config.define(
    'GIFSKI_MAX_TARGET_PIXELS',
    1440000,
    'Above this output size (target width * height), the gifski pipeline '
    'routes through the legacy palettegen/paletteuse + gifsicle path '
    "instead. gifski's quantizer working set grows with output dimensions "
    "while the legacy path's memory stays bounded, at the cost of wall "
    'time. A value of 0 disables the switch. Defaults to 1440000 (1600x900).',
    'Video')

Config.define(
    'GIFSKI_GIFSICLE_PASS',
    False,
    'If True, run a final geometry-free gifsicle -O3 pass (plus '
    'GIFSICLE_ARGS, e.g. --lossy) over gifski output to reduce file size',
    'Video')

Config.define(
    'MAX_ANIMATED_GIF_PIXELS',
    0,
    'Maximum total pixels (width * height * frame_count) for an animated GIF '
    'that is being transcoded to GIF. Sources over this limit fail with a 400 '
    "response (thumbor's MAX_PIXELS is per-frame and does not bound frame "
    'count). Only the gif->gif path is gated; conversions of a GIF source to '
    'video/webp/avif are memory-bounded and are the efficient way to serve '
    'large animated gifs, so they are not affected. A value of 0 (the default) '
    'disables the check.',
    'Video')

Config.define(
    'FFMPEG_HANDLE_ANIMATED_GIF',
    True,
    'Whether to process animated gifs with the ffmpeg engine',
    'Video')

Config.define(
    'FFMPEG_GIF_AUTO_WEBP',
    True,
    'Specifies whether animated WebP format should be used automatically if '
    'the source image is an animated gif and the request accepts it (via '
    'Accept header)',
    'Video')

Config.define(
    'FFPROBE_PATH',
    '/usr/local/bin/ffprobe',
    'Path for the ffprobe binary',
    'Video')

Config.define(
    'FFMPEG_H264_TWO_PASS',
    False,
    'Whether to use two-pass encoding for h264 in ffmpeg',
    'Video')

Config.define(
    'FFMPEG_H264_PRESET',
    None,
    'The -preset flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_LEVEL',
    None,
    'The -level flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_PROFILE',
    None,
    'The -profile:v flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_TUNE',
    None,
    'The -tune flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_CRF',
    None,
    'The -crf flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_VBR',
    None,
    'The average bitrate to be used by ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_MAXRATE',
    None,
    'The -maxrate flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_BUFSIZE',
    None,
    'The -bufsize flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_QMIN',
    None,
    'The -qmin flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H264_QMAX',
    None,
    'The -qmax flag passed to ffmpeg for h264 encoding',
    'Video')

Config.define(
    'FFMPEG_H265_TWO_PASS',
    False,
    'Whether to use two-pass encoding for h265 in ffmpeg',
    'Video')

Config.define(
    'FFMPEG_H265_PRESET',
    None,
    'The -preset flag passed to ffmpeg for h265 encoding',
    'Video')

Config.define(
    'FFMPEG_H265_LEVEL',
    None,
    'The -level flag passed to ffmpeg for h265 encoding',
    'Video')

Config.define(
    'FFMPEG_H265_MAXRATE',
    None,
    'The --vbv-maxrate flag passed to ffmpeg for h265 encoding',
    'Video')

Config.define(
    'FFMPEG_H265_BUFSIZE',
    None,
    'The --vbv-bufsize flag passed to libx265',
    'Video')

Config.define(
    'FFMPEG_H265_CRF_MIN',
    None,
    'The --crf-min flag passed to libx265',
    'Video')

Config.define(
    'FFMPEG_H265_CRF_MAX',
    None,
    'The --crf-max flag passed to libx265',
    'Video')

Config.define(
    'FFMPEG_H265_PROFILE',
    None,
    'The -profile:v flag passed to ffmpeg for h265 encoding',
    'Video')

Config.define(
    'FFMPEG_H265_TUNE',
    None,
    'The -tune flag passed to ffmpeg for h265 encoding',
    'Video')

Config.define(
    'FFMPEG_H265_CRF',
    None,
    'The -crf flag passed to ffmpeg for h265 encoding',
    'Video')

Config.define(
    'FFMPEG_H265_VBR',
    None,
    'The average bitrate to be used by ffmpeg for h265 encoding',
    'Video')

Config.define(
    'FFMPEG_VP9_TWO_PASS',
    False,
    'Whether to use two-pass encoding for vp9 in ffmpeg',
    'Video')

Config.define(
    'FFMPEG_VP9_VBR',
    None,
    'The average bitrate to be used by ffmpeg for vp9 encoding',
    'Video')

Config.define(
    'FFMPEG_VP9_LOSSLESS',
    False,
    'Whether to use lossless vp9 encoding',
    'Video')

Config.define(
    'FFMPEG_VP9_DEADLINE',
    None,
    'The -deadline flag passed to ffmpeg for vp9 encoding',
    'Video')

Config.define(
    'FFMPEG_VP9_CRF',
    None,
    'The constant quality (-crf) to use by ffmpeg for vp9 encoding',
    'Video')

Config.define(
    'FFMPEG_VP9_CPU_USED',
    None,
    'The -cpu-used flag passed to ffmpeg for vp9 encoding',
    'Video')

Config.define(
    'FFMPEG_VP9_ROW_MT',
    False,
    'Whether to enable row-based multithreading (-row-mt 1) for vp9 encoding in ffmpeg',
    'Video')

Config.define(
    'FFMPEG_VP9_MINRATE',
    None,
    'The -minrate flag passed to ffmpeg for vp9 encoding',
    'Video')

Config.define(
    'FFMPEG_VP9_MAXRATE',
    None,
    'The -maxrate flag passed to ffmpeg for vp9 encoding',
    'Video')

Config.define(
    'FFMPEG_WEBP_LOSSLESS',
    False,
    '(-lossless) Enables/disables use of lossless mode. libwebp default is False',
    'Video')

Config.define(
    'FFMPEG_WEBP_COMPRESSION_LEVEL',
    None,
    '(-compression_level) range 0-6, default 4. Higher values give better '
    'quality but slower speed. For lossless, it controls the size/speed trade-off',
    'Video')

Config.define(
    'FFMPEG_WEBP_QSCALE',
    None,
    '(-qscale) For lossy encoding, controls quality 0 to 100. For lossless, '
    'controls cpu and time spent compressing. libwebp built-in default 75.',
    'Video')

Config.define(
    'FFMPEG_WEBP_PRESET',
    None,
    '(-preset) Configuration preset. Consult ffmpeg libwebp codec documentation '
    'for more information.',
    'Video')

Config.define(
    'FFMPEG_GIF_AUTO_H264',
    False,
    'Specifies whether an H264 mp4 should be returned automatically if '
    'the source image is an animated gif and the request accepts it (via '
    'Accept: video/* header)',
    'Video')

Config.define(
    'FFMPEG_GIF_AUTO_H265',
    False,
    'Specifies whether an H265 mp4 should be returned automatically if '
    'the source image is an animated gif and the request accepts it (via '
    'Accept: video/* header)',
    'Video')


Config.define(
    'FFMPEG_PRESERVE_AUDIO',
    False,
    'If True, thumbor-video-engine will not strip the audio track. Defaults to '
    'False',
    'Video')
