"""
Main module, basically in charge of application init / start
"""
import logging
import sys

from pathlib import Path

from PyQt5.QtWidgets import QApplication

from als import config
from als.logic import Controller
from als.code_utilities import Timer
from als.model.data import VERSION
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

        with open(Path(__file__).parent / "main.css", "r") as styleFile:

            style = styleFile.read()
            app.setStyleSheet(style)

        window.show()
        window.reset_image_view()

    _LOGGER.info(f"Astro Live Stacker version {VERSION} started in {startup.elapsed_in_milli_as_str} ms.")

    app_return_code = app.exec()
    controller.shutdown()

    _LOGGER.info(f"Astro Live Stacker terminated with return code = {app_return_code}")

    sys.exit(app_return_code)


if __name__ == "__main__":
    main()
