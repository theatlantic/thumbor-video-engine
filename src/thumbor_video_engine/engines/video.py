from thumbor.engines import BaseEngine
from thumbor.utils import logger

from thumbor_video_engine.utils import (
    named_tmp_file, is_mp4, is_qt, is_animated, is_animated_gif)


def patch_baseengine_get_mimetype():
    """
    Monkey-patch BaseEngine.get_mimetype() to recognize all mp4 files as video/mp4
    """
    orig_get_mimetype = BaseEngine.get_mimetype

    def get_mimetype(cls, buffer):
        mimetype = orig_get_mimetype(buffer)
        if mimetype is not None:
            return mimetype
        elif is_qt(buffer):
            return 'video/quicktime'
        elif is_mp4(buffer):
            return 'video/mp4'

    BaseEngine.get_mimetype = classmethod(get_mimetype)


patch_baseengine_get_mimetype()


class Engine(object):
    """An engine that dispatches video files to ffmpeg, and others to PIL"""

    def __init__(self, context):
        self.engine = None
        self.context = context
        self.ffmpeg_handle_animated_gif = context.config.FFMPEG_HANDLE_ANIMATED_GIF
        self.ffmpeg_handle_animated_webp = True
        self.use_gif_engine = context.config.FFMPEG_USE_GIFSICLE_ENGINE

    @property
    def image_engine(self):
        self.context.modules.importer.import_item('IMAGE_ENGINE', 'Engine')
        return self.context.modules.importer.image_engine(self.context)

    @property
    def ffmpeg_engine(self):
        if not hasattr(self.context.modules, 'ffmpeg_engine'):
            # Instantiate the video engine class from the config (default is
            # thumbor_video_engine.engines.ffmpeg)
            self.context.modules.importer.import_item('FFMPEG_ENGINE', 'Engine')
            self.context.modules.ffmpeg_engine = (
                self.context.modules.importer.ffmpeg_engine(self.context))
        return self.context.modules.ffmpeg_engine

    def get_engine(self, buffer, extension):
        mime = BaseEngine.get_mimetype(buffer)

        is_gif = extension == '.gif'
        is_webp = extension == '.webp'
        accepts_video = getattr(self.context.request, "accepts_video", False)
        accepts_webp = self.context.request.accepts_webp

        if is_webp and self.ffmpeg_handle_animated_webp and is_animated(buffer):
            return self.ffmpeg_engine
        elif is_gif and self.ffmpeg_handle_animated_gif and is_animated_gif(buffer):
            if self.context.config.FFMPEG_GIF_AUTO_H265:
                self.context.request.should_vary = True
                if accepts_video:
                    logger.debug("FFMPEG_GIF_AUTO_H265 setting format to h264")
                    self.context.request.format = 'h265'
            elif self.context.config.FFMPEG_GIF_AUTO_H264:
                self.context.request.should_vary = True
                if accepts_video:
                    logger.debug("FFMPEG_GIF_AUTO_H264 setting format to h264")
                    self.context.request.format = 'h264'
            elif self.context.config.FFMPEG_GIF_AUTO_WEBP:
                self.context.request.should_vary = True
                if accepts_webp:
                    logger.debug("FFMPEG_GIF_AUTO_WEBP setting format to webp")
                    self.context.request.format = 'webp'
            return self.ffmpeg_engine
        elif is_gif and self.use_gif_engine:
            return self.context.modules.gif_engine
        elif mime.startswith('video/'):
            return self.ffmpeg_engine
        else:
            return self.image_engine

    def load(self, buffer, extension):
        self.engine = self.get_engine(buffer, extension)
        if self.context.request.format and not self.context.request.filters:
            # RequestParameters.filters is an empty list when none are in the url,
            # and ImagingHandler._write_results_to_client assumes that if
            # context.request.format is set then it came from the format filter.
            # Since we set the format in the engine this causes a TypeError,
            # so we need to ensure that it is a string here.
            self.context.request.filters = ""
        logger.debug("Set engine to %s (extension %s)" % (
            type(self.engine).__module__, extension))
        still_frame_pos = getattr(self.context.request, 'still_position', None)
        # Are we requesting a still frame?
        if self.engine is self.ffmpeg_engine and still_frame_pos:
            with named_tmp_file(data=buffer, suffix=extension) as src_file:
                buffer = self.ffmpeg_engine.run_ffmpeg(
                    src_file, 'png', ['-ss', still_frame_pos, '-frames:v', '1'])
                self.engine = self.image_engine
                extension = '.png'
                if not self.context.request.format:
                    self.context.request.format = 'jpg'

        # Change the default extension if we're transcoding video
        if self.engine is self.ffmpeg_engine and extension == ".jpg":
            extension = ".mp4"

        self.extension = extension
        self.engine.load(buffer, extension)

    def is_multiple(self):
        return False

    def cleanup(self):
        pass

    def __getattr__(self, attr):
        if not self.__dict__.get('engine'):
            raise AttributeError("'Engine' object has no attribute '%s'" % attr)
        return getattr(self.engine, attr)

    def __setattr__(self, attr, value):
        if attr in ('engine', 'ffmpeg_handle_animated_gif', 'use_gif_engine'):
            self.__dict__[attr] = value
        elif attr in ('context', 'extension'):
            self.__dict__[attr] = value
            if self.engine:
                setattr(self.engine, attr, value)
        elif self.engine:
            setattr(self.engine, attr, value)
        else:
            self.__dict__[attr] = value
