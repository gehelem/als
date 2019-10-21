"""
Holds all windows used in the app
"""
import logging

from PyQt5.QtCore import QEvent, pyqtSlot, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QGraphicsScene, QGraphicsPixmapItem, QDialog, QWidget
from qimage2ndarray import array2qimage

import als.model.data
from als import config
from als.config import CouldNotSaveConfig
from als.logic import Controller, SessionError, CriticalFolderMissing, WebServerStartFailure
from als.code_utilities import log
from als.model.data import VERSION, STACKING_MODE_SUM, STACKING_MODE_MEAN, DYNAMIC_DATA
from als.ui.dialogs import PreferencesDialog, AboutDialog, error_box, warning_box, SaveWaitDialog, question, message_box
from als.ui.params_utils import update_controls_from_params, update_params_from_controls, reset_params
from generated.als_ui import Ui_stack_window

_LOGGER = logging.getLogger(__name__)


# pylint: disable=R0904
class MainWindow(QMainWindow):
    """
    ALS main window.
    """

    _LOG_DOCK_INITIAL_HEIGHT = 150

    @log
    def __init__(self, controller: Controller, parent=None):

        super().__init__(parent)

        self._controller = controller
        self._ui = Ui_stack_window()
        self._ui.setupUi(self)
        self.setWindowTitle(_("Astro Live Stacker") + f" - v{VERSION}")

        # populate stacking mode combo box
        self._ui.cb_stacking_mode.blockSignals(True)
        stacking_modes = [STACKING_MODE_SUM, STACKING_MODE_MEAN]
        for stacking_mode in stacking_modes:
            self._ui.cb_stacking_mode.addItem(stacking_mode)
        self._ui.cb_stacking_mode.setCurrentIndex(stacking_modes.index(DYNAMIC_DATA.stacking_mode))
        self._ui.cb_stacking_mode.blockSignals(False)

        # store if docks must be shown or not
        self.shown_log_dock = True
        self.show_session_dock = True

        # prevent log dock to be too tall
        self.resizeDocks([self._ui.log_dock], [self._LOG_DOCK_INITIAL_HEIGHT], Qt.Vertical)

        # setup levels controls
        self._levels_controls = [self._ui.sld_black, self._ui.sld_white, self._ui.chk_autostretch]
        self._reset_levels()
        self._ui.btn_levels_apply.clicked.connect(self._apply_levels)
        self._ui.btn_levels_reset.clicked.connect(self._reset_levels)
        self._ui.btn_levels_reload.clicked.connect(self._reload_levels)

        DYNAMIC_DATA.add_observer(self)
        self.update_display()

        # setup image display
        self._scene = QGraphicsScene(self)
        self._ui.image_view.setScene(self._scene)
        self._image_item = None
        self.reset_image_view()

    def _apply_levels(self):
        """
        Apply levels processing
        """
        update_params_from_controls(DYNAMIC_DATA.levels_parameters, self._levels_controls)

        self._controller.apply_processing()

    def _reset_levels(self):
        """
        Resets levels processing controls to their defaults
        """
        reset_params(DYNAMIC_DATA.levels_parameters, self._levels_controls)

    def _reload_levels(self):
        """
        Sets levels processing controls to their previously recorded values (last apply)
        """
        update_controls_from_params(DYNAMIC_DATA.levels_parameters, self._levels_controls)

    @log
    def reset_image_view(self):
        """
        Reset image viewer to its initial state
        """
        for item in self._scene.items():
            self._scene.removeItem(item)
        self._image_item = QGraphicsPixmapItem(QPixmap(":/icons/dslr-camera.svg"))
        self._scene.addItem(self._image_item)
        self._ui.image_view.fitInView(self._image_item, Qt.KeepAspectRatio)

    @log
    def closeEvent(self, event):
        """Handles window close events."""
        # pylint: disable=C0103

        window_rect = self.geometry()
        config.set_window_geometry((window_rect.x(), window_rect.y(), window_rect.width(), window_rect.height()))
        MainWindow._save_config()

        self._stop_session()

        if DYNAMIC_DATA.session.is_stopped:

            if DYNAMIC_DATA.saver_queue_size > 0:
                SaveWaitDialog(self).exec()

            event.accept()
        else:
            event.ignore()

    @log
    def changeEvent(self, event):
        """Handles window change events."""
        # pylint: disable=C0103

        event.accept()

        # if window is going out of minimized state, we restore docks if needed
        if event.type() == QEvent.WindowStateChange:
            if not self.windowState() & Qt.WindowMinimized:
                _LOGGER.debug("Restoring docks visibility")
                if self.shown_log_dock:
                    self._ui.log_dock.show()
                if self.show_session_dock:
                    self._ui.session_dock.show()

    @pyqtSlot(name="on_pbSave_clicked")
    @log
    def cb_save(self):
        """
        Qt slot for mouse clicks on the 'save' button.

        This saves the processed image using user chosen format

        """
        image_to_save = DYNAMIC_DATA.process_result
        if image_to_save is not None:
            self._controller.save_image(image_to_save,
                                        config.get_image_save_format(),
                                        config.get_work_folder_path(),
                                        als.model.data.STACKED_IMAGE_FILE_NAME_BASE,
                                        add_timestamp=True)

    @pyqtSlot(name="on_action_quit_triggered")
    @log
    def cb_quit(self):
        """ Qt slot for activation of the 'quit' action"""
        super().close()

    @pyqtSlot(name="on_action_prefs_triggered")
    @log
    def cb_prefs(self):
        """ Qt slot for activation of the 'preferences' action"""
        self._open_preferences()

    @pyqtSlot(name="on_action_about_als_triggered")
    @log
    def cb_about(self):
        """ Qt slot for activation of the 'about' action"""
        dialog = AboutDialog(self)
        dialog.exec()

    # pylint: disable=C0103
    @staticmethod
    @log
    def on_cb_stacking_mode_currentTextChanged(text: str):
        """
        Qt slot executed when stacking mode comb box changed

        :param text: new stacking mode
        :type text: str
        :return:
        """
        DYNAMIC_DATA.stacking_mode = text

    @staticmethod
    @log
    def on_chk_align_toggled(checked: bool):
        """
        Qt slot executed when 'align' check box is changed

        :param checked: is checkbox checked ?
        :type checked: bool
        """
        DYNAMIC_DATA.align_before_stacking = checked

    @staticmethod
    @log
    def on_chk_save_every_image_toggled(checked: bool):
        """
        Qt slot executed when 'save ever image' check box is changed

        :param checked: is checkbox checked ?
        :type checked: bool
        """
        DYNAMIC_DATA.save_every_image = checked

    @pyqtSlot()
    @log
    def on_btn_web_start_clicked(self):
        """
        Qt slot executed when START web button is clicked
        """
        self._start_www()

    @pyqtSlot()
    @log
    def on_btn_web_stop_clicked(self):
        """
        Qt slot executed when START web button is clicked
        """
        self._stop_www()

    @log
    def adjust_value(self):
        """
        Adjusts stacked image according to GUU controls

        """
        # TODO :)

    @log
    def _update_image(self):
        """
        Update central image display.
        """
        image_raw_data = DYNAMIC_DATA.process_result.data.copy()

        image = array2qimage(image_raw_data, normalize=(2 ** 16 - 1))
        self._image_item.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(name="on_pbPlay_clicked")
    @log
    def cb_play(self):
        """Qt slot for mouse clicks on the 'play' button"""

        self._start_session()

    def on_log_message(self, message):
        """
        print received log message to GUI log window

        :param message: the log message
        :type message: str
        """
        self._ui.log.addItem(message)
        self._ui.log.scrollToBottom()

    @log
    def update_display(self, image_only: bool = False):
        """
        Updates all displays and controls depending on DataStore held data
        """

        if image_only:
            self._update_image()

        else:
            web_server_is_running = DYNAMIC_DATA.web_server_is_running
            session = DYNAMIC_DATA.session
            session_is_running = session.is_running
            session_is_stopped = session.is_stopped
            session_is_paused = session.is_paused

            # update running statuses
            scanner_status_message = f"Scanner on {config.get_scan_folder_path()}: "
            scanner_status_message += f"Running" if session_is_running else "Stopped"
            self._ui.lbl_scanner_status.setText(scanner_status_message)

            if web_server_is_running:
                url = f"http://{DYNAMIC_DATA.web_server_ip}:{config.get_www_server_port_number()}"
                self._ui.lbl_web_server_status.setText(f'Web server: Started, reachable at <a href="{url}">{url}</a>')
            else:
                self._ui.lbl_web_server_status.setText("Web server: Stopped")

            if session_is_stopped:
                session_status_string = "Stopped"
            elif session_is_paused:
                session_status_string = "Paused"
            elif session_is_running:
                session_status_string = "Running"
            else:
                # this should never happen, that's why we check ;)
                session_status_string = "### BUG !"
            self._ui.lbl_session_status.setText(f"Session: {session_status_string}")

            # update preferences accessibility according to session and web server status
            self._ui.action_prefs.setEnabled(not web_server_is_running and session_is_stopped)

            # handle Start / Pause / Stop  buttons
            self._ui.pbPlay.setEnabled(session_is_stopped or session_is_paused)
            self._ui.pbStop.setEnabled(session_is_running or session_is_paused)
            self._ui.pbPause.setEnabled(session_is_running)

            # handle align + stack mode buttons
            self._ui.chk_align.setEnabled(session_is_stopped)
            self._ui.cb_stacking_mode.setEnabled(session_is_stopped)

            # handle web stop start buttons
            self._ui.btn_web_start.setEnabled(not web_server_is_running)
            self._ui.btn_web_stop.setEnabled(web_server_is_running)

            # update stack size
            self._ui.lbl_stack_size.setText(str(DYNAMIC_DATA.stack_size))

            # update queues sizes
            self._ui.lbl_pre_process_queue_size.setText(str(DYNAMIC_DATA.pre_processor_queue_size))
            self._ui.lbl_stack_queue_size.setText(str(DYNAMIC_DATA.stacker_queue_size))
            self._ui.lbl_process_queue_size.setText(str(DYNAMIC_DATA.post_processor_queue_size))
            self._ui.lbl_save_queue_size.setText(str(DYNAMIC_DATA.saver_queue_size))

            # handle component statuses
            self._ui.lbl_pre_processor_status.setText(DYNAMIC_DATA.pre_processor_status)
            self._ui.lbl_stacker_status.setText(DYNAMIC_DATA.stacker_status)
            self._ui.lbl_post_processor_status.setText(DYNAMIC_DATA.post_processor_status)
            self._ui.lbl_saver_status.setText(DYNAMIC_DATA.saver_status)

    @pyqtSlot(name="on_pbStop_clicked")
    @log
    def cb_stop(self):
        """Qt slot for mouse clicks on the 'Stop' button"""
        self._stop_session()

    @pyqtSlot(name="on_pbPause_clicked")
    @log
    def cb_pause(self):
        """Qt slot for mouse clicks on the 'Pause' button"""
        self._controller.pause_session()

    @pyqtSlot(bool, name="on_log_dock_visibilityChanged")
    @log
    def cb_log_dock_changed_visibility(self, visible):
        """
        Qt slot for changes of log dock visibility.

        :param visible: True if log dock is visible
        :type visible: bool
        """

        if not self.windowState() & Qt.WindowMinimized:
            self.shown_log_dock = visible

    @pyqtSlot(bool, name="on_session_dock_visibilityChanged")
    @log
    def cb_session_dock_changed_visibility(self, visible):
        """
        Qt slot for changes of session dock visibility.

        :param visible: True if session dock is visible
        :type visible: bool
        """

        if not self.windowState() & Qt.WindowMinimized:
            self.show_session_dock = visible

    @log
    def _start_www(self):
        """Starts web server"""

        try:
            self._controller.start_www()
            if DYNAMIC_DATA.web_server_ip == "127.0.0.1":
                title = "Web server access is limited"
                message = "Web server IP address is 127.0.0.1.\n\nServer won't be reachable by other " \
                          "machines. Please check your network connection"
                warning_box(title, message)
        except WebServerStartFailure as start_failure:
            error_box(start_failure.message, start_failure.details)

    @log
    def _stop_www(self):
        """Stops web server"""
        self._controller.stop_www()

    @log
    def _start_session(self, is_retry: bool = False):
        """
        Stars session

        :param is_retry: is this a retry ?
        :type is_retry: bool
        """

        try:
            self._controller.start_session()
            if is_retry:
                message_box("Session started", "Session successfully started after retry")

        except CriticalFolderMissing as folder_missing:

            text = folder_missing.details
            text += "\n\n Would you like to open the preferences box ?"

            if question(folder_missing.message, text) and self._open_preferences():
                self._start_session(is_retry=True)

        except SessionError as session_error:
            error_box(session_error.message, str(session_error.details) + "\n\nSession start aborted")

    @log
    def _stop_session(self, ask_confirmation: bool = True):
        """
        Stops sessions

        :param ask_confirmation: do we ask user for confirmation ?
        :type ask_confirmation: bool
        """

        if not DYNAMIC_DATA.session.is_stopped:

            do_stop_session = True

            if ask_confirmation and DYNAMIC_DATA.stack_size > 0:
                message = """Stopping the current session will reset the stack and all image enhancements.
    
                Are you sure you want to stop the current session ?
                """
                do_stop_session = question("Really stop session ?",
                                           message,
                                           default_yes=False)

            if do_stop_session:
                self._controller.stop_session()

    @log
    def _open_preferences(self):
        """
        Opens preferences dialog box and return True if dilaog was closed using "OK"

        :return: Was the dilaog closed with "OK" ?
        :rtype: bool
        """

        accepted = PreferencesDialog(self).exec() == QDialog.Accepted

        if accepted:
            self.update_display()

        return accepted

    @staticmethod
    @log
    def _save_config():

        try:
            config.save()
        except CouldNotSaveConfig as save_error:
            error_box(save_error.message, f"Your settings could not be saved\n\nDetails : {save_error.details}")
