import re
import sys

import tornado.gen as gen

import thumbor.app
from thumbor.handlers.imaging import ImagingHandler


class VideoEngineImagingHandler(ImagingHandler):
    def _override_write_results_to_client(self, results, content_type):
        # RequestParameters.filters is an empty list when none are in the url,
        # and ImagingHandler._write_results_to_client assumes that if
        # context.request.format is set then it came from the format filter.
        # Since we set the format in the engine this causes a TypeError,
        # so we need to ensure that it is a string here.
        if not self.context.request.filters:
            self.context.request.filters = ""
        # output format is not requested via format filter
        should_vary = not (
            # format is supported by filter
            self.context.request.format and
            # filter is in request
            bool(re.search(r"format\([^)]+\)", self.context.request.filters)))

        if should_vary and getattr(self.context.request, "should_vary", False):
            self.set_header('Vary', 'Accept')

    if sys.version_info[0] == 2:
        def _write_results_to_client(self, results, content_type):
            self._override_write_results_to_client(results, content_type)
            super(VideoEngineImagingHandler, self)._write_results_to_client(results, content_type)
    else:
        exec("\n".join([
            "async def _write_results_to_client(self, results, content_type):",
            "    self._override_write_results_to_client(results, content_type)",
            "    await ImagingHandler._write_results_to_client(self, results, content_type)",
        ]))

    def _override_execute_image_operations(self):
        self.context.request.accepts_video = (
            'video/' in self.request.headers.get('Accept', ''))

    if sys.version_info[0] == 2:
        @gen.coroutine
        def execute_image_operations(self):
            self._override_execute_image_operations()
            yield super(VideoEngineImagingHandler, self).execute_image_operations()
    else:
        exec("\n".join([
            "async def execute_image_operations(self):",
            "    self._override_execute_image_operations()",
            "    await ImagingHandler.execute_image_operations(self)",
        ]))


class ThumborServiceApp(thumbor.app.ThumborServiceApp):
    def get_handlers(self):
        handlers = super(ThumborServiceApp, self).get_handlers()
        for i, handler in list(enumerate(handlers)):
            url_regex, handler_cls, ctx = handler[0], handler[1], handler[2:]
            if issubclass(handler_cls, ImagingHandler):
                # Replace with our custom imaging handler
                handlers[i] = (url_regex, VideoEngineImagingHandler) + ctx
        return handlers
