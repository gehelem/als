"""
Provides base application data
"""
import logging
from typing import List

import numpy as np

import als
from als.code_utilities import SignalingQueue, log
from als.model.base import Session
from als.model.params import ProcessingParameter

_LOGGER = logging.getLogger(__name__)

VERSION = als.__version__

STACKING_MODE_SUM = "Sum"
STACKING_MODE_MEAN = "Mean"

WORKER_STATUS_BUSY = "Busy"
WORKER_STATUS_IDLE = "-"

IMAGE_SAVE_TYPE_TIFF = "tiff"
IMAGE_SAVE_TYPE_PNG = "png"
IMAGE_SAVE_TYPE_JPEG = "jpg"

STACKED_IMAGE_FILE_NAME_BASE = "stack_image"
WEB_SERVED_IMAGE_FILE_NAME_BASE = "web_image"


# pylint: disable=R0902, R0904
class DynamicData:
    """
    Holds and maintain application dynamic data and notify observers on significant changes
    """
    def __init__(self):
        self.session = Session()
        self.web_server_is_running = False
        self.web_server_ip = ""
        self.stack_size = 0
        self.pre_processor_queue_size = 0
        self.stacker_queue_size = 0
        self.post_processor_queue_size = 0
        self.saver_queue_size = 0
        self.post_processor_result = None
        self.histogram_container: HistogramContainer = None
        self.pre_process_queue = SignalingQueue()
        self.stacker_queue = SignalingQueue()
        self.process_queue = SignalingQueue()
        self.save_queue = SignalingQueue()
        self.pre_processor_status = ""
        self.stacker_status = ""
        self.post_processor_status = ""
        self.saver_status = ""
        self.levels_parameters: ProcessingParameter = None


class HistogramContainer:
    """
    Holds histogram data for an image (color or b&w)

    also holds the global maximum among all held histograms and a way to get the number of bins
    """
    @log
    def __init__(self):
        self._histograms: List[np.ndarray] = list()
        self._global_maximum: int = 0

    @log
    def add_histogram(self, histogram: np.ndarray):
        """
        Add an histogram

        :param histogram: the histogram to add
        :type histogram: numpy.ndarray
        :return:
        """
        self._histograms.append(histogram)

    @log
    def get_histograms(self) -> List[np.ndarray]:
        """
        Gets the histograms

        :return: the histograms
        :rtype: List[numpy.ndarray]
        """
        return self._histograms

    @property
    def global_maximum(self) -> int:
        """
        Gets the global maximum among all histograms

        :return: the global maximum among all histograms
        :rtype: int
        """
        return self._global_maximum

    @global_maximum.setter
    def global_maximum(self, value: int):
        """
        Sets the global maximum among all histograms

        :param value: the global maximum among all histograms
        :type value: int
        """
        self._global_maximum = value

    @property
    @log
    def bin_count(self):
        """
        Get the bin count, that is the length of any stored histogram. We check the first one if exists

        :return: the number of bins used to compute the stored histograms.
        :rtype: int
        """
        return len(self._histograms[0]) if self._histograms else 0


DYNAMIC_DATA = DynamicData()
