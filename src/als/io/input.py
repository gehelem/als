"""
Provides everything need to handle ALS main inputs : images.

We need to read file and in the future, get images from INDI
"""
import logging
import time
from abc import abstractmethod
from pathlib import Path
from queue import Queue

import numpy as np
import rawpy
from PyQt5.QtCore import QObject, QFileInfo
from astropy.io import fits
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from als import config
from als.code_utilities import log
from als.model import Image

_LOGGER = logging.getLogger(__name__)

# queue to which are posted all loaded images
_IMAGE_INPUT_QUEUE = Queue()

_IGNORED_FILENAME_START_PATTERNS = ['.', '~', 'tmp']
_DEFAULT_SCAN_FILE_SIZE_RETRY_PERIOD_IN_SEC = 0.1


class InputListener(QObject):
    """
    In charge of input management, **abstract class**
    """

    @staticmethod
    def create_listener(listener_type: str):
        """
        Creates specialized input listeners.

        :param listener_type: what type of listener to create
        :type listener_type: str : allowed values :

          - 'FS' to create a filesystem listener

        :return: an input listener
        :rtype: FileSystemListener
        """
        if listener_type == "FS":
            return FileSystemListener()

    @abstractmethod
    def start(self):
        """
        Start listening for new images.
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Stop listening for new images.
        """
        pass


class FileSystemListener(InputListener, FileSystemEventHandler):
    """
    Watches file changes (creation, move) in a specific filesystem folder
    """

    @log
    def __init__(self):
        InputListener.__init__(self)
        FileSystemEventHandler.__init__(self)
        self._observer = None

    @log
    def start(self):
        self._observer = PollingObserver()
        self._observer.schedule(self, config.get_scan_folder_path(), recursive=False)
        self._observer.start()
        _LOGGER.info("File Listener started")

    @log
    def stop(self):
        if self._observer is not None:
            self._observer.stop()
        self._observer = None
        _LOGGER.info("File Listener stopped")

    @log
    def on_moved(self, event):
        if event.event_type == 'moved':
            image_path = event.dest_path
            _LOGGER.debug(f"File move detected : {image_path}")

            image = read_image(Path(image_path))

            if image is not None:
                _IMAGE_INPUT_QUEUE.put(image)

    @log
    def on_created(self, event):
        if event.event_type == 'created':
            file_is_incomplete = True
            last_file_size = -1
            image_path = event.src_path
            _LOGGER.debug(f"File creation detected : {image_path}. Waiting until file is fully written to disk...")

            while file_is_incomplete:
                info = QFileInfo(image_path)
                size = info.size()
                _LOGGER.debug(f"File {image_path}'s size = {size}")
                if size == last_file_size:
                    file_is_incomplete = False
                    _LOGGER.debug(f"File {image_path} has been fully written to disk")
                last_file_size = size
                time.sleep(_DEFAULT_SCAN_FILE_SIZE_RETRY_PERIOD_IN_SEC)

            image = read_image(Path(image_path))

            if image is not None:
                _IMAGE_INPUT_QUEUE.put(image)


@log
def read_image(path: Path):
    """
    Reads an image from disk

    :param path: path to the file to load image from
    :type path:  pathlib.Path

    :return: the image read from disk or None if image is ignored
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

        file_path_str = str(path.resolve())
        image.origin = f"FILE : {file_path_str}"
        _LOGGER.info(f"Successful image read from file '{file_path_str}'")

    return image


@log
def _read_fit_image(path: Path):
    """
    read FIT image from filesystem

    :param path: path to image file to load from
    :type path: pathlib.Path

    :return: the loaded image, with data and headers parsed
    :rtype: Image
    """
    with fits.open(str(path.resolve())) as fit:
        data = fit[0].data
        header = fit[0].header

    image = Image(data)

    if 'BAYERPAT' in header:
        image.bayer_pattern = header['BAYERPAT']

    return image


@log
def _read_raw_image(path: Path):
    """
    Reads a RAW DLSR image from file

    :param path: path to the file to read from
    :type path: pathlib.Path

    :return: the image
    :rtype: Image
    """
    raw_image = rawpy.imread(str(path.resolve())).postprocess(gamma=(1, 1),
                                                              no_auto_bright=True,
                                                              output_bps=16,
                                                              user_flip=0)
    return Image(np.rollaxis(raw_image, 2, 0))
