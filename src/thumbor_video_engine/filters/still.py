from thumbor.filters import BaseFilter, filter_method, PHASE_PRE_LOAD
from thumbor.utils import logger

from thumbor_video_engine.compat import filter_retval


class Filter(BaseFilter):
    phase = PHASE_PRE_LOAD

    @filter_method(r'(?P<pos>\-?(?:(?:\d\d:)?\d\d:\d\d(?:\.\d+?)?|\d+(?:\.\d+?)?))')
    def still(self, position='0'):
        logger.debug('Setting still frame at position %s' % position)
        self.context.request.still_position = position
        return filter_retval()
