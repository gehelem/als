"""
Provides base application data
"""
from logging import getLogger
from typing import List

import numpy as np
from PyQt5.QtCore import QObject

import als
from als.code_utilities import SignalingQueue, log, AlsLogAdapter
from als.model.base import Session

_LOGGER = AlsLogAdapter(getLogger(__name__), {})

VERSION = als.__version__

WORKER_STATUS_IDLE = "-"

IMAGE_SAVE_TYPE_TIFF = "tiff"
IMAGE_SAVE_TYPE_PNG = "png"
IMAGE_SAVE_TYPE_JPEG = "jpg"

STACKED_IMAGE_FILE_NAME_BASE = "stack_image"
WEB_SERVED_IMAGE_FILE_NAME_BASE = "web_image"


# pylint: disable=R0903
class I18n(QObject):
    """
    Holds global localized strings.

    All strings are initialized with dummy text and MUST be defined in setup()
    """

    STACKING_MODE_SUM = "TEMP"
    STACKING_MODE_MEAN = "TEMP"
    WORKER_STATUS_BUSY = "TEMP"

    SCANNER = "TEMP"
    OF = "TEMP"

    PROFILE = "TEMP"
    VISUAL = "TEMP"

    RUNNING_M = "TEMP"
    RUNNING_F = "TEMP"
    STOPPED_M = "TEMP"
    STOPPED_F = "TEMP"
    PAUSED = "TEMP"

    WEB_SERVER = "TEMP"
    ADDRESS = "TEMP"

    TOOLTIP_BLACK_LEVEL = "TEMP"
    TOOLTIP_MIDTONES_LEVEL = "TEMP"
    TOOLTIP_WHITE_LEVEL = "TEMP"
    TOOLTIP_RED_LEVEL = "TEMP"
    TOOLTIP_GREEN_LEVEL = "TEMP"
    TOOLTIP_BLUE_LEVEL = "TEMP"
    TOOLTIP_STRETCH_STRENGTH = "TEMP"
    TOOLTIP_RGB_ACTIVE = "TEMP"
    TOOLTIP_STRETCH_ACTIVE = "TEMP"
    TOOLTIP_LEVELS_ACTIVE = "TEMP"

    STACK_SIZE = "TEMP"

    SESSION = "TEMP"

    def setup(self):
        """
        Sets real values for localized strings
        """
        I18n.STACKING_MODE_SUM = self.tr("sum")
        I18n.STACKING_MODE_MEAN = self.tr("mean")
        I18n.WORKER_STATUS_BUSY = self.tr("busy")
        I18n.SCANNER = self.tr("scanner")
        I18n.OF = self.tr("of")
        I18n.PROFILE = self.tr("Profile")
        I18n.VISUAL = self.tr("Visual")
        I18n.RUNNING_M = self.tr("running", "gender m")
        I18n.RUNNING_F = self.tr("running", "gender f")
        I18n.STOPPED_M = self.tr("stopped", "gender m")
        I18n.STOPPED_F = self.tr("stopped", "gender f")
        I18n.PAUSED = self.tr("paused")
        I18n.WEB_SERVER = self.tr("web server")
        I18n.ADDRESS = self.tr("address")
        I18n.TOOLTIP_RED_LEVEL = self.tr("Red level")
        I18n.TOOLTIP_GREEN_LEVEL = self.tr("Green level")
        I18n.TOOLTIP_BLUE_LEVEL = self.tr("Blue level")
        I18n.TOOLTIP_BLACK_LEVEL = self.tr("Black level")
        I18n.TOOLTIP_MIDTONES_LEVEL = self.tr("Midtones level")
        I18n.TOOLTIP_WHITE_LEVEL = self.tr("White level")
        I18n.TOOLTIP_STRETCH_STRENGTH = self.tr("Autostretch strength")
        I18n.TOOLTIP_RGB_ACTIVE = self.tr("RGB balance active")
        I18n.TOOLTIP_STRETCH_ACTIVE = self.tr("Autostretch active")
        I18n.TOOLTIP_LEVELS_ACTIVE = self.tr("Levels active")
        I18n.STACK_SIZE = self.tr("stack size")
        I18n.SESSION = self.tr("Session")


# pylint: disable=R0902, R0903
class DynamicData:
    """
    Holds and maintain application dynamic data and notify observers on significant changes
    """
    def __init__(self):
        self.session = Session()
        self.web_server_is_running = False
        self.web_server_ip = ""
        self.stack_size = 0
        self.post_processor_result = None
        self.histogram_container: HistogramContainer = None
        self.pre_process_queue = SignalingQueue()
        self.stacker_queue = SignalingQueue()
        self.process_queue = SignalingQueue()
        self.save_queue = SignalingQueue()
        self.pre_processor_busy = False
        self.stacker_busy = False
        self.post_processor_busy = False
        self.saver_busy = False
        self.has_new_warnings = False
        self.is_first_run = True
        self.post_processor_result_qimage = None
        self.last_timing = 0
        self.total_exposure_time: int = 0


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
    @log
    def global_maximum(self) -> int:
        """
        Gets the global maximum among all histograms

        :return: the global maximum among all histograms
        :rtype: int
        """
        return self._global_maximum

    @global_maximum.setter
    @log
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
