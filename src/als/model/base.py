"""
Provide base application data types
"""
import logging

from PyQt5.QtCore import pyqtSignal, QObject
import numpy as np

from als.code_utilities import log

_LOGGER = logging.getLogger(__name__)


class Session(QObject):
    """
    Represents an ALS session
    """

    stopped = 0
    running = 1
    paused = 2

    _ALLOWED_STATUSES = [stopped, running, paused]

    status_changed_signal = pyqtSignal()
    """Qt signal to emit when status changes"""

    @log
    def __init__(self, status: int = stopped):
        QObject.__init__(self)
        if status in Session._ALLOWED_STATUSES:
            self._status = status

    @property
    def is_running(self):
        """
        Is session running ?

        :return: True if session is running, False otherwise
        :rtype: bool
        """
        return self._status == Session.running

    @property
    def is_stopped(self):
        """
        Is session stopped ?

        :return: True if session is stopped, False otherwise
        :rtype: bool
        """
        return self._status == Session.stopped

    @property
    def is_paused(self):
        """
        Is session paused ?

        :return: True if session is paused, False otherwise
        :rtype: bool
        """
        return self._status == Session.paused

    @log
    def set_status(self, status: int):
        """
        Sets session status

        :param status: the status to set
        :type status: int
        """
        if status in Session._ALLOWED_STATUSES:
            self._status = status
            self.status_changed_signal.emit()


class Image:
    """
    Represents an image, our basic processing object.

    Image data is a numpy array. Array's data type is unspecified for now
    but we'd surely benefit from enforcing one (float32 for example) as it will
    ease the development of any later processing code

    We also store the bayer pattern the image was shot with, if applicable.

    If image is from a sensor without a bayer array, the bayer pattern must be None.
    """

    def __init__(self, data):
        """
        Constructs an Image

        :param data: the image data
        :type data: numpy.ndarray
        """
        self._data = data
        self._bayer_pattern: str = None
        self._origin: str = "UNDEFINED"
        self._destination: str = "UNDEFINED"

    def clone(self):
        """
        Clone an image

        :return: an image with global copied data
        :rtype: Image
        """
        new = Image(self.data.copy())
        new.bayer_pattern = self.bayer_pattern
        new.origin = self.origin
        new.destination = self.destination
        return new

    @property
    def destination(self):
        """
        Retrieves image destination

        :return: the destination
        :rtype: str
        """
        return self._destination

    @destination.setter
    def destination(self, destination):
        """
        Sets image destination

        :param destination: the image destination
        :type destination: str
        """
        self._destination = destination

    @property
    def data(self):
        """
        Retrieves image data

        :return: image data
        :rtype: numpy.ndarray
        """
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    @property
    def origin(self):
        """
        retrieves info on image origin.

        If Image has been read from a disk file, origin contains the file path

        :return: origin representation
        :rtype: str
        """
        return self._origin

    @origin.setter
    def origin(self, origin):
        self._origin = origin

    @property
    def bayer_pattern(self):
        """
        Retrieves the bayer pattern the image was shot with, if applicable.

        :return: the bayer pattern or None
        :rtype: str
        """
        return self._bayer_pattern

    @property
    def dimensions(self):
        """
        Retrieves image dimensions as a tuple.

        This is basically the underlying array's shape tuple, minus the color axis if image is color

        :return: the image dimensions
        :rtype: tuple
        """
        if self._data.ndim == 2:
            return self._data.shape

        dimensions = list(self.data.shape)
        dimensions.remove(min(dimensions))
        return dimensions

    @property
    def width(self):
        """
        Retrieves image width

        :return: image width in pixels
        :rtype: int
        """
        return max(self.dimensions)

    @property
    def height(self):
        """
        Retrieves image height

        :return: image height in pixels
        :rtype: int
        """
        return min(self.dimensions)

    @bayer_pattern.setter
    def bayer_pattern(self, bayer_pattern):
        self._bayer_pattern = bayer_pattern

    def needs_debayering(self):
        """
        Tells if image needs debayering

        :return: True if a bayer pattern is known and data does not have 3 dimensions
        """
        return self._bayer_pattern is not None and self.data.ndim < 3

    def is_color(self):
        """
        Tells if the image has color information

        image has color information if its data array has more than 2 dimensions

        :return: True if the image has color information, False otherwise
        :rtype: bool
        """
        return self._data.ndim > 2

    def is_bw(self):
        """
        Tells if image is black and white

        :return: True if no color info is stored in data array, False otherwise
        :rtype: bool
        """
        return self._data.ndim == 2 and self._bayer_pattern is None

    def is_same_shape_as(self, other):
        """
        Is this image's shape equal to another's ?

        :param other: other image to compare shape with
        :type other: Image

        :return: True if shapes are equal, False otherwise
        :rtype: bool
        """
        return self._data.shape == other.data.shape

    def set_color_axis_as(self, wanted_axis):
        """
        Reorganise internal data array so color information is on a specified axis

        :param wanted_axis: The 0-based number of axis we want color info to be

        Image data is modified in place
        """

        if self._data.ndim > 2:

            # find what axis are the colors on.
            # axis 0-based index is the index of the smallest data.shape item
            shape = self._data.shape
            color_axis = shape.index(min(shape))

            if color_axis != wanted_axis:
                self._data = np.moveaxis(self._data, color_axis, wanted_axis)

    def __repr__(self):
        representation = (f'{self.__class__.__name__}('
                          f'Color={self.is_color()}, '
                          f'Needs Debayer={self.needs_debayering()}, '
                          f'Bayer Pattern={self.bayer_pattern}, '
                          f'Width={self.width}, '
                          f'Height={self.height}, '
                          f'Data shape={self._data.shape}, '
                          f'Data type={self._data.dtype.name}, '
                          f'Origin={self.origin}, '
                          f'Destination={self.destination}, ')

        if self.is_color():
            representation += f"Mean R: {int(np.mean(self._data[0]))}, "
            representation += f"Mean G: {int(np.mean(self._data[1]))}, "
            representation += f"Mean B: {int(np.mean(self._data[2]))})"
        else:
            representation += f"Mean: {int(np.mean(self._data))})"

        return representation
