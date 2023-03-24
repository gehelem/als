"""
Provides features for in-app communications
"""
from logging import getLogger

from PyQt5.QtCore import QObject, pyqtSignal, QCoreApplication

from als.code_utilities import get_timestamp, AlsLogAdapter


class MessageHub(QObject):
    """
    Responsible of collecting all messages and dispatching to whoever wants to listen to them.

    Any object can register, as soon as it has a on_message(str) function
    """
    message_signal = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)

    def _dispatch_message(self, log_func, flag: str, message: str, values: list):
        """
        Dispatches message to log function and Qt signal.

        Message is formatted if values list is not None

        :param log_func: logging function
        :type log_func: function
        :param flag: textual flag describing message level (INFO, WARN, ERROR)
        :type flag: str
        :param message: the message
        :type message: str
        :param values: values used for formatting
        :type values: list
        """

        if values:
            log_func(message.format(*values))
            self.message_signal.emit(
                get_timestamp() + " " + flag.ljust(8) + ": " + QCoreApplication.translate("", message).format(*values))

        else:
            log_func(message)
            self.message_signal.emit(
                get_timestamp() + " " + flag.ljust(8) + ": " + QCoreApplication.translate("", message))

    def dispatch_info(self, name: str, message: str, values: list = None):
        """
        Dispatches information message.

        :param name: the logger name
        :type name: str
        :param message: the message
        :type message: str
        :param values: values used for message formatting
        :type values: list
        """

        self._dispatch_message(AlsLogAdapter(getLogger(name), {}).info, "INFO", message, values)

    def dispatch_warning(self, name: str, message: str, values: list = None):
        """
        Dispatches warning message.

        :param name: the logger name
        :type name: str
        :param message: the message
        :type message: str
        :param values: values used for message formatting
        :type values: list
        """

        self._dispatch_message(AlsLogAdapter(getLogger(name), {}).warning, "WARNING", message, values)

    def dispatch_error(self, name: str, message: str, values: list = None):
        """
        Dispatches error message.

        :param name: the logger name
        :type name: str
        :param message: the message
        :type message: str
        :param values: values used for message formatting
        :type values: list
        """

        self._dispatch_message(AlsLogAdapter(getLogger(name), {}).error, "ERROR", message, values)

    def add_receiver(self, receiver):
        """
        Connects  message signal to a receiver

        :param receiver: the receiver
        :type receiver: any. It must have a on_message(str) function.
        """
        self.message_signal[str].connect(receiver.on_message)


MESSAGE_HUB = MessageHub()
