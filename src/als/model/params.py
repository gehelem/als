"""
Holds types used for processing parameters
"""

import logging
from typing import Any

from als.code_utilities import log

_LOGGER = logging.getLogger(__name__)


class ProcessingParameter:

    @log
    def __init__(self, name: str, description: str, default: Any, value: Any):

        self.name = name
        self.description = description
        self.default = default
        self.value = value


class RangeParameter(ProcessingParameter):
    @log
    def __init__(self, name: str, description: str, default: Any, value: Any,
                 minimum: int, maximum: int, steps: int = 255):

        super().__init__(name, description, default, value)
        self.minimum = minimum
        self.maximum = maximum
        self.steps = steps
