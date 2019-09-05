"""
Provides a set of utilities aimed at app developpers
"""
import logging
from time import time


def log(func):
    """
    Decorates a function to add logging

    A log entry (DEBUG level) is printed with decorated function's qualified name and all its params
    If the decorated function returns anything, a log entry (DEBUG level) is printed with decorated
    function qualified name and return value(s)

    Logs are issued using is the logger named after the decorated function's enclosing module

    :param func: The function to decorate
    :return: The decorated function
    """
    def wrapped(*args, **kwargs):
        function_name = func.__qualname__
        logger = logging.getLogger(func.__module__)
        logger.debug("%s() called with : %s - %s",
                     function_name,
                     str(args),
                     str(kwargs))
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        logger.debug("%s() returned %s in %0.3f ms",
                     function_name,
                     str(result),
                     (end_time - start_time) * 1000)
        return result
    return wrapped
