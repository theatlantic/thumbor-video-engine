from thumbor.filters import BaseFilter, filter_method, PHASE_PRE_LOAD
from thumbor_video_engine.compat import filter_retval


class Filter(BaseFilter):
    phase = PHASE_PRE_LOAD

    @filter_method(BaseFilter.String)
    def tune(self, value):
        self.context.request.tune = value
        return filter_retval()
