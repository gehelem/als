"""
Main module, basically in charge of application init / start
"""
import logging
import multiprocessing
import os
import platform
import sys

import psutil
from PyQt5.QtWidgets import QApplication

from als import config
from als.logic import Controller
from als.code_utilities import Timer, human_readable_byte_size, get_text_content_of_resource
from als.model.data import VERSION
from als.ui.windows import MainWindow

_LOGGER = logging.getLogger(__name__)


def log_sys_info():
    """
    Log detailed info about current running system
    """

    _LOGGER.debug("***************************************************************************")
    _LOGGER.debug('System info dump - START')
    _LOGGER.debug(f"Platform name         : {sys.platform}")
    _LOGGER.debug(f"Platform architecture : {platform.architecture()}")
    _LOGGER.debug(f"Machine name          : {platform.machine()}")
    _LOGGER.debug(f"CPU type              : {platform.processor()}")
    _LOGGER.debug(f"CPU count             : {os.cpu_count()}")
    _LOGGER.debug(f"OS name               : {platform.system()}")
    _LOGGER.debug(f"OS release            : {platform.release()}")
    _LOGGER.debug(f"Available memory      : {human_readable_byte_size(psutil.virtual_memory().available)}")
    _LOGGER.debug(f"Python version        : {sys.version}")
    _LOGGER.debug('System info dump - END')
    _LOGGER.debug("***************************************************************************")


def main():
    """
    Application launcher
    """

    with Timer() as startup:
        app = QApplication(sys.argv)
        config.setup()

        log_sys_info()

        # look for existing "Stacker" processes and kill them
        #
        # Those Stacker processes are leftovers from a previous ALS crash occurring while stacking
        # using multiprocessing
        for process in psutil.process_iter():
            if process.name() == "Stacker" and process.status() != psutil.STATUS_ZOMBIE:
                process.kill()

        app.setStyleSheet(get_text_content_of_resource(":/main/main.css"))

        _LOGGER.debug("Building and showing main window")
        controller = Controller()
        window = MainWindow(controller)

        window.reset_image_view()

    _LOGGER.info(f"Astro Live Stacker version {VERSION} started in {startup.elapsed_in_milli_as_str} ms.")

    app_return_code = app.exec()
    controller.shutdown()

    _LOGGER.info(f"Astro Live Stacker terminated with return code = {app_return_code}")

    sys.exit(app_return_code)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
