"""
Provides everything need to handle ALS main inputs : images.

We need to read file and in the future, get images from INDI
"""
import logging
import time
from pathlib import Path
from queue import Queue

import numpy as np
import rawpy
from PyQt5.QtCore import QFileInfo
from astropy.io import fits
from rawpy._rawpy import LibRawNonFatalError, LibRawFatalError
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from als import config
from als.code_utilities import log
from als.model import Image, STORE

_LOGGER = logging.getLogger(__name__)

# queue to which are posted all loaded images
_IMAGE_INPUT_QUEUE = Queue()

_IGNORED_FILENAME_START_PATTERNS = ['.', '~', 'tmp']
_DEFAULT_SCAN_FILE_SIZE_RETRY_PERIOD_IN_SEC = 0.1


class FileSystemListener(FileSystemEventHandler):
    """
    Watches file changes (creation, move) in a specific filesystem folder
    """

    @log
    def __init__(self):
        FileSystemEventHandler.__init__(self)
        self._observer = None

    @log
    def start(self):
        self._observer = PollingObserver()
        self._observer.schedule(self, config.get_scan_folder_path(), recursive=False)
        self._observer.start()
        _LOGGER.info("File Listener started")
        STORE.scan_in_progress = True

    @log
    def pause(self):
        self._stop_observer()

    @log
    def stop(self):
        self._stop_observer()
        _purge_queue()

    @log
    def on_moved(self, event):
        if event.event_type == 'moved':
            image_path = event.dest_path
            _LOGGER.debug(f"File move detected : {image_path}")

            _enqueue_image(read_image(Path(image_path)))

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

            _enqueue_image(read_image(Path(image_path)))

    @log
    def _stop_observer(self):
        if self._observer is not None:
            self._observer.stop()
        self._observer = None
        _LOGGER.info("File Listener stopped")
        STORE.scan_in_progress = False


@log
def _purge_queue():
    while not _IMAGE_INPUT_QUEUE.empty():
        _IMAGE_INPUT_QUEUE.get()


@log
def _enqueue_image(image: Image):
    if image is not None:
        _IMAGE_INPUT_QUEUE.put(image)
        _LOGGER.debug(f"Input queue size = {_IMAGE_INPUT_QUEUE.qsize()}")


@log
def read_image(path: Path):
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

    except OSError as error:
        _report_error(path, error)
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
        with open(str(path.resolve()), 'rb') as image_file:
            raw_image = rawpy.imread(image_file)

        processed_image = raw_image.postprocess(gamma=(1, 1),
                                                no_auto_bright=True,
                                                output_bps=16,
                                                user_flip=0)

        return Image(np.rollaxis(processed_image, 2, 0))

    except LibRawNonFatalError as non_fatal_error:
        _report_error(path, non_fatal_error)
        return None
    except LibRawFatalError as fatal_error:
        _report_error(path, fatal_error)
        return None


def _report_error(path: Path, error: Exception):
    _LOGGER.error(f"Error reading from file {str(path.resolve())} : {str(error)}")
