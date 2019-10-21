"""
Holds types used for processing parameters
"""

import logging
from typing import Any

from als.code_utilities import log

_LOGGER = logging.getLogger(__name__)


class ProcessingParameter:
    """
    Base class for all processing parameters
    """
    @log
    def __init__(self, name: str, description: str, default: Any, value: Any):

        self.name = name
        self.description = description
        self.default = default
        self.value = value

    @log
    def reset(self):
        """
        Reset parameter value to parameter default
        """
        self.value = self.default


class RangeParameter(ProcessingParameter):
    """
    Represents a parameter of type range
    """
    @log
    def __init__(self, name: str, description: str, default: Any, value: Any,
                 minimum: int, maximum: int):

        super().__init__(name, description, default, value)
        self.minimum = minimum
        self.maximum = maximum


class SwitchParameter(ProcessingParameter):
    """
    Represents an ON / OFF switch
    """
