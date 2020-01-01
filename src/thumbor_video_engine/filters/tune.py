from thumbor.filters import BaseFilter, filter_method, PHASE_PRE_LOAD


class Filter(BaseFilter):
    phase = PHASE_PRE_LOAD

    @filter_method(BaseFilter.String)
    def tune(self, value):
        self.context.request.tune = value
