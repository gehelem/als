"""
Stores all data needed and shared by app modules
"""
import als
from als.code_utilities import log

VERSION = als.__version__


class DataStore:
    """
    Holds and maintain application dynamic data
    """
    def __init__(self):
        self._observers = []
        self._scan_in_progress = False
        self._web_server_is_running = False

    @property
    @log
    def web_server_is_running(self):
        """
        Is web server running.

        :return: True if webserver is running, False otherwise
        :rtype: bool
        """
        return self._web_server_is_running

    @web_server_is_running.setter
    @log
    def web_server_is_running(self, running):
        """
        Sets flag for webserver running status.

        :param running: is webserver running
        :type running: bool
        """
        self._web_server_is_running = running
        self._notify_observers()

    @property
    @log
    def scan_in_progress(self):
        """
        Is scan in progress.

        :return: True if scanner is running, False otherwise
        :rtype: bool
        """
        return self._scan_in_progress

    @scan_in_progress.setter
    @log
    def scan_in_progress(self, in_progress):
        """
        Sets flag for scanner running status.

        :param in_progress: is scanner running
        :type in_progress: bool
        """
        self._scan_in_progress = in_progress
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
        self._observers.remove(observer)

    @log
    def _notify_observers(self):
        """
        Tells all registered observers to update their display
        """
        for observer in self._observers:
            observer.update_according_to_app_state()


STORE = DataStore()


class Image:

    def __init__(self, data):
        self._data = data
        self._bayer_pattern = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    @property
    def bayer_pattern(self):
        return self._bayer_pattern

    @bayer_pattern.setter
    def bayer_pattern(self, bayer_pattern):
        self._bayer_pattern = bayer_pattern

    def needs_debayering(self):
        return self._bayer_pattern is not None

    def is_color(self):
        return len(self._data.shape) > 2
