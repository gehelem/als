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
        self._observers = []
        self._session = Session()
        self._web_server_is_running = False
        self._web_server_ip = ""
        self._stack_size = 0
        self._pre_processor_queue_size = 0
        self._stacker_queue_size = 0
        self._post_processor_queue_size = 0
        self._saver_queue_size = 0
        self._post_process_result = None
        self._histogram_container: HistogramContainer = None
        self._pre_process_queue = SignalingQueue()
        self._stacker_queue = SignalingQueue()
        self._process_queue = SignalingQueue()
        self._save_queue = SignalingQueue()
        self._pre_processor_status = ""
        self._stacker_status = ""
        self._post_processor_status = ""
        self._saver_status = ""
        self._levels_parameters: ProcessingParameter = None

        self._session.status_changed_signal.connect(self._notify_observers)

    @property
    def histogram_container(self):
        """
        Gets histogram container

        :return: the histogram container
        :rtype: HistogramContainer
        """
        return self._histogram_container

    @histogram_container.setter
    def histogram_container(self, container):
        """
        Sets the histogram container

        :param container: the container
        :type container: HistogramContainer
        """
        self._histogram_container = container

    @property
    def levels_parameters(self) -> ProcessingParameter:
        """
        Get levels processing parameter list

        :return the levels processing parameter list
        :rtype: List[ProcessingParameter]
        """
        return self._levels_parameters

    @levels_parameters.setter
    def levels_parameters(self, parameters):
        """
        Get levels processing parameter list

        :param parameters: the parameter list
        """
        self._levels_parameters = parameters

    @property
    def pre_processor_status(self):
        """
        Retrieves pre-processor published status
        """
        return self._pre_processor_status

    @pre_processor_status.setter
    def pre_processor_status(self, status):
        """
        Sets new pre-processor published status and notify observers

        :param status: new pre-processor published status
        :type status: str
        """
        self._pre_processor_status = status
        self._notify_observers()

    @property
    def stacker_status(self):
        """
        Retrieves stacker published status
        """
        return self._stacker_status

    @stacker_status.setter
    def stacker_status(self, status):
        """
        Sets new stacker published status and notify observers

        :param status: new stacker published status
        :type status: str
        """
        self._stacker_status = status
        self._notify_observers()

    @property
    def post_processor_status(self):
        """
        Retrieves post-processor published status
        """
        return self._post_processor_status

    @post_processor_status.setter
    def post_processor_status(self, status):
        """
        Sets new post-processor published status and notify observers

        :param status: new post-processor published status
        :type status: str
        """
        self._post_processor_status = status
        self._notify_observers()

    @property
    def saver_status(self):
        """
        Retrieves saver published status
        """
        return self._saver_status

    @saver_status.setter
    def saver_status(self, status):
        """
        Sets new saver published status and notify observers

        :param status: new saver published status
        :type status: str
        """
        self._saver_status = status
        self._notify_observers()

    @property
    def web_server_ip(self):
        """
        Retrieves web server ip

        :return: web server ip
        :rtype: str
        """
        return self._web_server_ip

    @web_server_ip.setter
    def web_server_ip(self, ip_address):
        """
        Sets web server ip

        :param ip_address: ip address
        :type ip_address: str
        """
        self._web_server_ip = ip_address

    @property
    def pre_processor_queue_size(self):
        """
        Retrieves the pre-process queue size

        :return: the pre-process queue size
        :rtype: int
        """
        return self._pre_processor_queue_size

    @pre_processor_queue_size.setter
    def pre_processor_queue_size(self, size):
        """
        Sets the pre-process queue size

        :param size: the pre-process queue size
        :type size: int
        """
        old_size = self._pre_processor_queue_size
        self._pre_processor_queue_size = size
        if size != old_size:
            self._notify_observers()

    @property
    def stacker_queue_size(self):
        """
        Retrieves the stack queue size

        :return: the stack queue size
        :rtype: int
        """
        return self._stacker_queue_size

    @stacker_queue_size.setter
    def stacker_queue_size(self, size):
        """
        Sets the stack queue size

        :param size: the stack queue size
        :type size: int
        """
        old_size = self._stacker_queue_size
        self._stacker_queue_size = size
        if size != old_size:
            self._notify_observers()

    @property
    def post_processor_queue_size(self):
        """
        Retrieves the process queue size

        :return: the process queue size
        :rtype: int
        """
        return self._post_processor_queue_size

    @post_processor_queue_size.setter
    def post_processor_queue_size(self, size):
        """
        Sets the process queue size

        :param size: the process queue size
        :type size: int
        """
        old_size = self._post_processor_queue_size
        self._post_processor_queue_size = size
        if size != old_size:
            self._notify_observers()

    @property
    def saver_queue_size(self):
        """
        Retrieves the save queue size

        :return: the save queue size
        :rtype: int
        """
        return self._saver_queue_size

    @saver_queue_size.setter
    def saver_queue_size(self, size):
        """
        Sets the save queue size

        :param size: the save queue size
        :type size: int
        """
        old_size = self._saver_queue_size
        self._saver_queue_size = size
        if size != old_size:
            self._notify_observers()

    @property
    def stack_size(self):
        """
        Retrieves the published stack size

        :return: the published stack size
        :rtype: int
        """
        return self._stack_size

    @stack_size.setter
    def stack_size(self, size):
        """
        Sets published stack size

        :param size: the new published stack size
        :type size: int
        """
        old_size = self._stack_size
        self._stack_size = size
        if size != old_size:
            self._notify_observers()

    @property
    def session(self):
        """
        Retrieves the session instance

        :return: the session
        :rtype: Session
        """
        return self._session

    @property
    def save_queue(self):
        """
        Retrieves save queue

        :return: the save queue
        :rtype: SignalingQueue
        """
        return self._save_queue

    @property
    def post_process_result(self):
        """
        Retrieves latest published process result

        :return: the latest published process result
        :rtype: Image
        """
        return self._post_process_result

    @post_process_result.setter
    def post_process_result(self, image):
        """
        Record the latest process result

        :param image: the latest process result
        :type: Image
        """
        self._post_process_result = image
        self._notify_observers(image_only=True)

    @property
    def process_queue(self):
        """
        Retrieves the processing queue

        :return: the processing queue
        :rtype: SignalingQueue
        """
        return self._process_queue

    @property
    def stacker_queue(self):
        """
        Retrieves the stack queue

        :return: the stack queue
        :type: SignalingQueue
        """
        return self._stacker_queue

    @property
    def pre_process_queue(self):
        """
        Retrieves the pre_process queue.

        :return: the pre-process queue
        :rtype: SignalingQueue
        """
        return self._pre_process_queue

    @property
    def web_server_is_running(self):
        """
        Is web server running.

        :return: True if webserver is running, False otherwise
        :rtype: bool
        """
        return self._web_server_is_running

    @web_server_is_running.setter
    def web_server_is_running(self, running):
        """
        Sets flag for webserver running status.

        :param running: is webserver running
        :type running: bool
        """
        self._web_server_is_running = running
        self._notify_observers()

    @log
    def add_observer(self, observer):
        """
        Adds an observer to our observers list.

        :param observer: the new observer
        :type observer: any
        """
        self._observers.append(observer)

    @log
    def remove_observer(self, observer):
        """
        Removes observer from our observers list.

        :param observer: the observer to remove
        :type observer: any
        """
        if observer in self._observers:
            self._observers.remove(observer)

    @log
    def _notify_observers(self, image_only=False):
        """
        Tells all registered observers to update their display
        """
        for observer in self._observers:
            observer.update_display(image_only)


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
