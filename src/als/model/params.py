"""
Holds types used for processing parameters
"""

import logging

from als.code_utilities import log

_LOGGER = logging.getLogger(__name__)


class ProcessingParameter:

    @log
    def __init__(self, name: str, description: str):

        self.name = name
        self.description = description


class RangeParameter(ProcessingParameter):
    @log
    def __init__(self, name: str, description: str, minimum: int, maximum: int, default: int, steps: int = 255):
        super().__init__(name, description)
        self.min = minimum
        self.max = maximum
        self.default = default
        self.steps = steps
