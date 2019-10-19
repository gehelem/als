"""
Holds types used for processing parameters
"""

import logging
from typing import Any

from als.code_utilities import log

_LOGGER = logging.getLogger(__name__)


class ProcessingParameter:

    @log
    def __init__(self, name: str, description: str, default: Any):

        self.name = name
        self.description = description
        self.default = default


class RangeParameter(ProcessingParameter):
    @log
    def __init__(self, name: str, description: str, default: int, minimum: int, maximum: int, steps: int = 255):
        super().__init__(name, description, default)
        self.min = minimum
        self.max = maximum
        self.steps = steps
