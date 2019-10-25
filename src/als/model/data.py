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
        self._stacking_mode = ""
        self._align_before_stacking = True
        self._stack_size = 0
        self._pre_processor_queue_size = 0
        self._stacker_queue_size = 0
        self._post_processor_queue_size = 0
        self._saver_queue_size = 0
        self._save_every_image: bool = False
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
        return self._histogram_container

    @histogram_container.setter
    def histogram_container(self, container):
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
    def save_every_image(self):
        """
        Retrieves the flag that tells if we need to save every process result image

        :return: the flag that tells if we need to save every process result image
        :rtype: bool
        """
        return self._save_every_image

    @save_every_image.setter
    def save_every_image(self, save_every_image):
        """
        Sets the flag that tells if we need to save every process result image

        :param save_every_image: flag that tells if we need to save every process result image
        :type save_every_image: bool
        """
        self._save_every_image = save_every_image

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
    def align_before_stacking(self):
        """
        Retrieves alignment switch

        :return: is alignment ON ?
        :rtype: bool
        """
        return self._align_before_stacking

    @align_before_stacking.setter
    def align_before_stacking(self, align: bool):
        """
        Sets alignment switch

        :param align: is alignment ON ?
        :type align: bool
        """
        self._align_before_stacking = align

    @property
    def stacking_mode(self):
        """
        Retrieves stacking mode.

        :return: String representation of user chosen stacking mode.
        :rtype: str
        """
        return self._stacking_mode

    @stacking_mode.setter
    def stacking_mode(self, text: str):
        """
        Sets stacking mode.

        :param text: String representation of user chosen stacking mode. Allowed values are :

          - Sum : Stacking mode is sum
          - Mean : stacking mode is mean

        If unknown value is received, fallback to Mean

        :type text: str
        """
        if text.strip() in [STACKING_MODE_MEAN, STACKING_MODE_SUM]:
            self._stacking_mode = text
        else:
            self._stacking_mode = STACKING_MODE_MEAN

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
    """
    @log
    def __init__(self):
        self._histograms: List[np.ndarray] = list()
        self._global_maximum: int = 0

    @log
    def add_histogram(self, histogram: np.ndarray):
        self._histograms.append(histogram)

    @log
    def get_histograms(self) -> List[np.ndarray]:
        return self._histograms

    @property
    def global_maximum(self) -> int:
        return self._global_maximum

    @global_maximum.setter
    def global_maximum(self, value: int):
        self._global_maximum = value

    @property
    @log
    def bin_count(self):
        return len(self._histograms[0]) if len(self._histograms) > 0 else 0


DYNAMIC_DATA = DynamicData()
