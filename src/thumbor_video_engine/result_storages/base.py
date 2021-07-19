from os.path import join


class BaseStorage(object):
    @property
    def is_auto_webp(self):
        return (
            self.context.config.AUTO_WEBP and
            hasattr(self.context, 'request') and
            getattr(self.context.request, "accepts_webp", False))

    @property
    def is_auto_video(self):
        auto_video = (
            self.context.config.FFMPEG_GIF_AUTO_H264 or
            self.context.config.FFMPEG_GIF_AUTO_H265)
        return (
            auto_video and
            hasattr(self.context, 'request') and
            getattr(self.context.request, "accepts_video", False))

    def get_auto_path_component(self):
        if self.is_auto_video:
            return "mp4"
        elif self.is_auto_webp:
            return "webp"
