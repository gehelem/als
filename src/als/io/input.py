"""
Provides everything need to handle ALS main inputs : images.

We need to read file and in the future, get images from INDI
"""
import logging
import time
from abc import abstractmethod
from pathlib import Path

from astropy.io import fits
from PyQt5.QtCore import QFileInfo, pyqtSignal, QObject
from rawpy import imread
from rawpy._rawpy import LibRawNonFatalError, LibRawFatalError
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from als import config
from als.code_utilities import log
from als.IndiCamera import IndiCamera
from als.IndiClient import IndiClient
from als.model.base import Image

_LOGGER = logging.getLogger(__name__)

_IGNORED_FILENAME_START_PATTERNS = ['.', '~', 'tmp']
_DEFAULT_SCAN_FILE_SIZE_RETRY_PERIOD_IN_SEC = 0.1

SCANNER_TYPE_FILESYSTEM = "FS"
SCANNER_TYPE_INDI = "DI"


class InputError(Exception):
    """
    Base class for all Exception subclasses in this module
    """


class ScannerStartError(InputError):
    """
    Raised when folder scanner start is in error.
    """


class InputScanner:
    """
    Base abstract class for all code responsible of ALS "image acquisition".

    Subclasses are responsible for :

      - replying to start & stop commands
      - reading images from actual source
      - creating Image objects
      - broadcasting every new image
    """

    new_image_signal = pyqtSignal(Image)
    """Qt signal emitted when a new image is read by scanner"""

    @log
    def broadcast_image(self, image: Image):
        """
        Send a signal with newly read image to anyone who cares

        :param image: the new image
        :type image: Image
        """
        if image is not None:
            self.new_image_signal.emit(image)

    @abstractmethod
    def start(self):
        """
        Starts checking for new images

        :raises: ScannerStartError if startup fails
        """

    @abstractmethod
    def stop(self):
        """
        Stops checking for new images
        """

    @staticmethod
    def create_scanner(scanner_type: str = SCANNER_TYPE_FILESYSTEM):
        """
        Factory for image scanners.

        :param scanner_type: the type of scanner to create. Accepted values are :

          - "FS" for a filesystem scanner

        :type scanner_type: str.

        :return: the right scanner implementation
        :rtype: InputScanner subclass
        """

        #TODO TN fix that
        return IndiScanner()
        if scanner_type == SCANNER_TYPE_FILESYSTEM:
            return FolderScanner()
        elif scanner_type == SCANNER_TYPE_INDI:
            return IndiScanner()

        raise ValueError(f"Unsupported scanner type : {scanner_type}")


class FolderScanner(FileSystemEventHandler, InputScanner, QObject):
    """
    Watches file changes (creation, move) in a specific filesystem folder

    the watched directory is retrieved from user config on scanner startup
    """
    @log
    def __init__(self):
        FileSystemEventHandler.__init__(self)
        InputScanner.__init__(self)
        QObject.__init__(self)
        self._observer = None

    @log
    def start(self):
        """
        Starts scanning scan folder for new files
        """
        try:
            scan_folder_path = config.get_scan_folder_path()
            self._observer = PollingObserver()
            self._observer.schedule(self, scan_folder_path, recursive=False)
            self._observer.start()
        except OSError as os_error:
            raise ScannerStartError(os_error)

    @log
    def stop(self):
        """
        Stops scanning scan folder for new files
        """
        if self._observer is not None:
            self._observer.stop()
            self._observer = None

    @log
    def on_moved(self, event):
        if event.event_type == 'moved':
            image_path = event.dest_path
            _LOGGER.debug(f"File move detected : {image_path}")

            self.broadcast_image(read_disk_image(Path(image_path)))

    @log
    def on_created(self, event):
        if event.event_type == 'created':
            file_is_incomplete = True
            last_file_size = -1
            image_path = event.src_path
            _LOGGER.debug(f"File creation detected : {image_path}. Waiting until file is complete and readable ...")

            while file_is_incomplete:
                info = QFileInfo(image_path)
                size = info.size()
                _LOGGER.debug(f"File {image_path}'s size = {size}")
                if size == last_file_size:
                    file_is_incomplete = False
                    _LOGGER.debug(f"File {image_path} is ready to be read")
                last_file_size = size
                time.sleep(_DEFAULT_SCAN_FILE_SIZE_RETRY_PERIOD_IN_SEC)

            self.broadcast_image(read_disk_image(Path(image_path)))


@log
def read_disk_image(path: Path):
    """
    Reads an image from disk

    :param path: path to the file to load image from
    :type path:  pathlib.Path

    :return: the image read from disk or None if image is ignored or an error occurred
    :rtype: Image or None
    """

    ignore_image = False
    image = None

    for pattern in _IGNORED_FILENAME_START_PATTERNS:
        if path.name.startswith(pattern):
            ignore_image = True
            break

    if not ignore_image:
        if path.suffix.lower() in ['.fit', '.fits']:
            image = _read_fit_image(path)
        else:
            image = _read_raw_image(path)

        if image is not None:
            _LOGGER.info(f"Successful image read from {image.origin}")

    return image


@log
def _read_fit_image(path: Path):
    """
    read FIT image from filesystem

    :param path: path to image file to load from
    :type path: pathlib.Path

    :return: the loaded image, with data and headers parsed or None if a known error occurred
    :rtype: Image or None
    """
    try:
        with fits.open(str(path.resolve())) as fit:
            # pylint: disable=E1101
            data = fit[0].data
            header = fit[0].header

        image = Image(data)

        if 'BAYERPAT' in header:
            image.bayer_pattern = header['BAYERPAT']

        _set_image_file_origin(image, path)

    except OSError as error:
        _report_fs_error(path, error)
        return None

    return image


@log
def _read_raw_image(path: Path):
    """
    Reads a RAW DLSR image from file

    :param path: path to the file to read from
    :type path: pathlib.Path

    :return: the image or None if a known error occurred
    :rtype: Image or None
    """

    try:
        with imread(str(path.resolve())) as raw_image:

            # in here, we make sure we store the bayer pattern as it would be advertised if image was a FITS image.
            #
            # lets assume image comes from a DSLR sensor with the most common bayer pattern.
            #
            # The actual/physical bayer pattern would look like a repetition of :
            #
            # +---+---+
            # | R | G |
            # +---+---+
            # | G | B |
            # +---+---+
            #
            # RawPy will report the bayer pattern description as 2 discrete values :
            #
            # 1) raw_image.raw_pattern : a 2x2 numpy array representing the indices used to express the bayer patten
            #
            # in our example, its value is :
            #
            # +---+---+
            # | 0 | 1 |
            # +---+---+
            # | 3 | 2 |
            # +---+---+
            #
            # and its flatten version is :
            #
            # [0, 1, 3, 2]
            #
            # 2) raw_image.color_desc : a bytes literal formed of the color of each pixel of the bayer pattern, in
            #                           ascending index order from raw_image.raw_pattern
            #
            # in our example, its value is : b'RGBG'
            #
            # We need to express/store this pattern in a more common way, i.e. as it would be described in a FITS
            # header. Or put simply, we want to express the bayer pattern as it would be described if
            # raw_image.raw_pattern was :
            #
            # +---+---+
            # | 0 | 1 |
            # +---+---+
            # | 2 | 3 |
            # +---+---+
            bayer_pattern_indices = raw_image.raw_pattern.flatten()
            bayer_pattern_desc = raw_image.color_desc.decode()

            _LOGGER.debug(f"Bayer pattern indices = {bayer_pattern_indices}")
            _LOGGER.debug(f"Bayer pattern description = {bayer_pattern_desc}")

            assert len(bayer_pattern_indices) == len(bayer_pattern_desc)
            bayer_pattern = ""
            for i, index in enumerate(bayer_pattern_indices):
                assert bayer_pattern_indices[i] < len(bayer_pattern_indices)
                bayer_pattern += bayer_pattern_desc[index]

            _LOGGER.debug(f"Computed, FITS-compatible bayer pattern = {bayer_pattern}")

            new_image = Image(raw_image.raw_image_visible.copy())
            new_image.bayer_pattern = bayer_pattern
            _set_image_file_origin(new_image, path)
            return new_image

    except LibRawNonFatalError as non_fatal_error:
        _report_fs_error(path, non_fatal_error)
        return None
    except LibRawFatalError as fatal_error:
        _report_fs_error(path, fatal_error)
        return None


def _report_fs_error(path: Path, error: Exception):
    _LOGGER.error(f"Error reading from file {str(path.resolve())} : {str(error)}")


def _set_image_file_origin(image: Image, path: Path):
    image.origin = f"FILE : {str(path.resolve())}"


class IndiScanner(InputScanner, QObject):
    """
    Connects to an indi server and watch for a specific device blob

    the watched server/device is retrieved from user config on scanner startup
    """
    @log
    def __init__(self):
        InputScanner.__init__(self)
        QObject.__init__(self)
        self._observer = None

    @log
    def start(self):
        """
        Starts connect to server/device for new blobs
        """
        try:
            remote_host = config.get_remote_host()
            remote_port = config.get_remote_port()
            device_name = config.get_device_name()
            self._client = IndiClient(config=dict(indi_host=remote_host,
                                                  indi_port=remote_port),
                                      connect_on_create=True)
            self._device = IndiCamera(indi_client=self._client,
                                      config=dict(camera_name=device_name),
                                      connect_on_create=True)
        except Exception as e:
            raise ScannerStartError(e)

    @log
    def stop(self):
        """
        Stops listening to server for new blobs
        """
        if self._device is not None:
            self._device.disconnect()

    @log
    def on_received(self, event):
        if event.event_type == 'created':
            file_is_incomplete = True
            last_file_size = -1
            image_path = event.src_path
            _LOGGER.debug(f"File creation detected : {image_path}. Waiting until file is complete and readable ...")

            while file_is_incomplete:
                info = QFileInfo(image_path)
                size = info.size()
                _LOGGER.debug(f"File {image_path}'s size = {size}")
                if size == last_file_size:
                    file_is_incomplete = False
                    _LOGGER.debug(f"File {image_path} is ready to be read")
                last_file_size = size
                time.sleep(_DEFAULT_SCAN_FILE_SIZE_RETRY_PERIOD_IN_SEC)

            self.broadcast_image(read_disk_image(Path(image_path)))
