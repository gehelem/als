"""
Provides a set of utilities aimed at app developpers
"""
import logging


def log(func):
    """
    Decorates a function to add logging

    A log entry (DEBUG level) is printed with decorated function's qualified name and all its params
    If the decorated function returns anything, a log entry (DEBUG level) is printed with decorated function
    qualified name and return value(s)

    Logs are issued using is the logger named after the decorated function's enclosing module

    :param func: The function to decorate
    :return: The decorated function
    """
    def wrapped(*args, **kwargs):
        function_name = func.__qualname__
        logger = logging.getLogger(func.__module__)
        logger.debug(function_name + "() called with : " + str(args) + str(kwargs))
        result = func(*args, **kwargs)
        if result is not None:
            logger.debug(function_name + "() returned : " + str(result))
        return result
    return wrapped
