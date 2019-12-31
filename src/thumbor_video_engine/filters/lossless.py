from thumbor.filters import BaseFilter, filter_method, PHASE_PRE_LOAD


class Filter(BaseFilter):
    phase = PHASE_PRE_LOAD

    @filter_method(BaseFilter.Boolean)
    def lossless(self, enabled=True):
        self.context.request.lossless = enabled
