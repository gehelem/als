"""
Main module, basically in charge of application init / start
"""
import logging
import sys

from PyQt5.QtWidgets import QApplication

from als import config
from als.logic import Controller
from als.code_utilities import Timer
from als.model import VERSION
from als.ui.windows import MainWindow

_LOGGER = logging.getLogger(__name__)


def main():
    """
    Application launcher
    """

    with Timer() as startup:
        app = QApplication(sys.argv)
        config.setup()

        _LOGGER.debug("Building and showing main window")
        controller = Controller()
        window = MainWindow(controller)
        config.register_log_receiver(window)
        window.setGeometry(*config.get_window_geometry())
        window.show()
        window.reset_image_view()

    _LOGGER.info(f"Astro Live Stacker version {VERSION} started in {startup.elapsed_in_milli} ms.")

    app_return_code = app.exec()
    _LOGGER.info(f"Astro Live Stacker terminated with return code = {app_return_code}")

    sys.exit(app_return_code)


if __name__ == "__main__":
    main()
