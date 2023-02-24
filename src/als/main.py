"""
Main module, basically in charge of application init / start
"""
import locale
import logging
import multiprocessing
import os
import platform
import sys

import argparse
import psutil
from PyQt5.QtCore import QTranslator, QT_TRANSLATE_NOOP, QThread, Qt
from PyQt5.QtWidgets import QApplication

from als import config
from als.code_utilities import Timer, human_readable_byte_size, available_memory
from als.logic import Controller
from als.messaging import MESSAGE_HUB
from als.model.data import I18n, VERSION
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
    _LOGGER.debug(f"Available memory      : {human_readable_byte_size(available_memory())}")
    _LOGGER.debug(f"Python version        : {sys.version}")
    _LOGGER.debug('System info dump - END')
    _LOGGER.debug("***************************************************************************")


# pylint: disable=R0914
def main():
    """
    Runs ALS
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start_session", help="Start session on application startup", action="store_true")
    parser.add_argument("-w", "--start_server", help="Start web server on application startup", action="store_true")
    args = parser.parse_args()

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    with Timer() as startup:
        app = QApplication(sys.argv)
        QThread.currentThread().setPriority(QThread.TimeCriticalPriority)
        config.setup()
        log_sys_info()

        # look for existing "Stacker" processes and kill them
        #
        # Those Stacker processes are leftovers from a previous ALS crash occurring while stacking
        # using multiprocessing
        for process in psutil.process_iter():
            if process.status() != psutil.STATUS_ZOMBIE and process.name() == "Stacker":
                process.kill()

        locale_prefix = config.get_lang()
        if locale_prefix == 'sys':

            try:
                system_locale = locale.getlocale()[0]
                _LOGGER.debug(f"Detected system locale = {system_locale}")
                if system_locale is None:
                    raise ValueError("detected system locale is None !!! Grrrrrrrr")
                locale_prefix = system_locale.split('_')[0]
                _LOGGER.debug(f"System locale prefix = {locale_prefix}")

            except (ValueError, IndexError):
                _LOGGER.warning("Failed to detect system locale. App will not be translated")
                locale_prefix = "en"

        if locale_prefix != "en":

            translators = list()
            for component in ["als", "qtbase"]:
                i18n_file_name = f'{component}_{locale_prefix}'
                translator = QTranslator()
                if translator.load(f":/i18n/{i18n_file_name}.qm"):
                    _LOGGER.debug(f"Translation successfully loaded for {i18n_file_name}")
                    translator.setObjectName(i18n_file_name)
                    translators.append(translator)

            for translator in translators:
                if app.installTranslator(translator):
                    _LOGGER.debug(f"Translator successfully installed for {translator.objectName()}")

        I18n().setup()

        _LOGGER.debug("Building and showing main window")
        controller = Controller()
        window = MainWindow(controller)

        window.reset_image_view()

        if args.start_session:
            controller.start_session()

        if args.start_server:
            controller.start_www()

    start_message = QT_TRANSLATE_NOOP("", "Astro Live Stacker version {} started in {} ms.")
    start_message_values = [VERSION, startup.elapsed_in_milli_as_str]
    MESSAGE_HUB.dispatch_info(__name__, start_message, start_message_values)

    app_return_code = app.exec()
    controller.shutdown()

    _LOGGER.info(f"Astro Live Stacker terminated with return code = {app_return_code}")

    sys.exit(app_return_code)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
