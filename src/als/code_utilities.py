"""
Provides a set of utilities aimed at app developpers
"""
import logging
from functools import wraps
from queue import Queue
from time import time

from PyQt5.QtCore import QObject, pyqtSignal


def log(func):
    """
    Decorates a function to add logging.

    A log entry (DEBUG level) is printed with decorated function's qualified name and all its params.

    If the decorated function returns anything, a log entry (DEBUG level) is printed with decorated
    function's qualified name and return value(s).

    Logs are issued using is the logger named after the decorated function's enclosing module.

    :param func: The function to decorate
    :return: The decorated function
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        function_name = func.__qualname__
        logger = logging.getLogger(func.__module__)
        logger.debug(f"{function_name}() called with : {str(args)} - {str(kwargs)}")
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        logger.debug(f"{function_name}() returned {str(result)} in {(end_time - start_time) * 1000:0.3f} ms")
        return result
    return wrapped


# pylint: disable=W0201
class Timer:
    """
    A context manager, timing any portion of code it encloses.

    Basic usage :

    .. code-block:: python

        with Timer() as t:

            # your code here
            # it can be many lines
            pass

        _LOGGER.info(f"code ran in {t.elapsed_in_milli} ms.")

    The context manager exposes 2 attributes :

        - elapsed_in_milli (float) = elapsed time
        - elapsed_in_milli_as_str (str) = string representation of elapsed time with only 3 decimal positions

    """
    def __enter__(self):
        self.start = time()
        return self

    def __exit__(self, *args):
        self.end = time()
        self.elapsed_in_milli = (self.end - self.start) * 1000
        self.elapsed_in_milli_as_str = "%0.3f" % self.elapsed_in_milli


class AlsException(Exception):
    """
    Base class for all custom errors
    """
    @log
    def __init__(self, message, details):
        Exception.__init__(self)
        self.message = message
        self.details = details


class SignalingQueue(Queue, QObject):
    """
    Queue subclass that emits a Qt signal when items are added or removed from the queue.

    Signal is :

      - size_changed_signal

    and carries the new queue size
    """

    size_changed_signal = pyqtSignal(int)
    """
    Qt signal stating that a new item has just been pushed to the queue.

    :param: the new size of the queue
    :type: int
    """

    @log
    def __init__(self, maxsize=0):
        Queue.__init__(self, maxsize)
        QObject.__init__(self)

    @log
    def get(self, block=True, timeout=None):
        item = super().get(block, timeout)
        self.size_changed_signal.emit(self.qsize())
        return item

    @log
    def get_nowait(self):
        item = super().get_nowait()
        self.size_changed_signal.emit(self.qsize())
        return item

    @log
    def put(self, item, block=True, timeout=None):
        super().put(item, block, timeout)
        self.size_changed_signal.emit(self.qsize())

    @log
    def put_nowait(self, item):
        super().put_nowait(item)
        self.size_changed_signal.emit(self.qsize())


def human_readable_byte_size(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.3f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.3f %s%s" % (num, 'Yi', suffix)
