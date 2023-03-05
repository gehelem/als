"""
Holds all windows used in the app
"""
import logging
from os import linesep

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QPixmap, QBrush, QColor, QIcon
from PyQt5.QtWidgets import QMainWindow, QGraphicsScene, QGraphicsPixmapItem, QDialog, QApplication, \
    QListWidgetItem, qApp, QLabel, QFrame

import als.model.data
from als import config
from als.code_utilities import log, get_text_content_of_resource
from als.config import CouldNotSaveConfig
from als.logic import Controller, SessionError, CriticalFolderMissing, WebServerFailedToStart, WebServerOnLoopback
from als.messaging import MESSAGE_HUB
from als.model.data import DYNAMIC_DATA, I18n
from als.ui.dialogs import PreferencesDialog, AboutDialog, error_box, warning_box, SaveWaitDialog, question, \
    message_box, SessionStopDialog, QRDisplay
from als.ui.params_utils import update_controls_from_params, update_params_from_controls, reset_params, \
    set_sliders_defaults
from generated.als_ui import Ui_stack_window

_LOGGER = logging.getLogger(__name__)
_INFO_LOG_TAG = 'INFO'


# pylint: disable=R0904, R0902
class MainWindow(QMainWindow):
    """
    ALS main window.
    """

    _LOG_DOCK_INITIAL_HEIGHT = 150

    # pylint: disable=too-many-statements
    @log
    def __init__(self, controller: Controller, parent=None):

        super().__init__(parent)

        self._warning_sign_off = QIcon()
        self._warning_sign_on = QIcon(QPixmap(":/icons/warning_sign.svg"))

        self.setWindowIcon(QIcon(":/icons/als_logo.png"))

        self._controller = controller
        self._ui = Ui_stack_window()
        self._ui.setupUi(self)
        self.setWindowTitle("Astro Live Stacker")

        self._qrDisplay = QRDisplay(self)
        self._qrDisplay.hide()
        self._qrDisplay.visibility_changed_signal[bool].connect(self.on_qr_display_visibility_changed)

        # populate stacking mode combo box=
        self._ui.cb_stacking_mode.blockSignals(True)
        stacking_modes = [I18n.STACKING_MODE_SUM, I18n.STACKING_MODE_MEAN]
        for stacking_mode in stacking_modes:
            self._ui.cb_stacking_mode.addItem(stacking_mode)
        self._ui.cb_stacking_mode.setCurrentIndex(stacking_modes.index(self._controller.get_stacking_mode()))
        self._ui.cb_stacking_mode.blockSignals(False)

        # update align checkbox
        self._ui.chk_align.setChecked(self._controller.get_align_before_stack())

        # update save every frame checkbox
        self._ui.chk_save_every_image.setChecked(self._controller.get_save_every_image())

        # prevent log dock to be too tall
        self.resizeDocks([self._ui.log_dock], [MainWindow._LOG_DOCK_INITIAL_HEIGHT], Qt.Vertical)

        # setup rgb controls and params
        self._rgb_controls = [
            self._ui.chk_rgb_active,
            self._ui.sld_rgb_r,
            self._ui.sld_rgb_g,
            self._ui.sld_rgb_b,
        ]

        self._rgb_parameters = self._controller.get_rgb_parameters()

        set_sliders_defaults(
            [self._rgb_parameters[1], self._rgb_parameters[2], self._rgb_parameters[3]],
            [self._ui.sld_rgb_r, self._ui.sld_rgb_g, self._ui.sld_rgb_b]
        )

        self._reset_rgb()

        # setup autostretch controls and params
        self._autostretch_controls = [

            self._ui.chk_stretch_active,
            self._ui.sld_stretch_strength
        ]

        self._autostretch_parameters = self._controller.get_autostretch_parameters()

        set_sliders_defaults(
            [self._autostretch_parameters[1]],
            [self._ui.sld_stretch_strength]
        )

        self._reset_autostretch()

        # setup levels controls and parameters
        self._levels_controls = [
            self._ui.chk_levels_active,
            self._ui.sld_black,
            self._ui.sld_midtones,
            self._ui.sld_white,
        ]

        self._levels_parameters = self._controller.get_levels_parameters()

        set_sliders_defaults(
            [self._levels_parameters[1], self._levels_parameters[2], self._levels_parameters[3]],
            [self._ui.sld_black, self._ui.sld_midtones, self._ui.sld_white]
        )

        self._reset_levels()

        # setup exchanges with dynamic data
        self._controller.add_model_observer(self)

        self.setGeometry(*config.get_window_geometry())

        # setup management of 'image only' mode
        self._restore_log_dock = False
        self._restore_session_dock = False
        self._restore_processing_dock = False

        # setup image display
        self._scene = QGraphicsScene(self)
        self._ui.image_view.setScene(self._scene)
        self._image_item = None
        self.reset_image_view()

        # setup statusbar
        self._lbl_statusbar_session_status = QLabel(self._ui.statusBar)
        self._lbl_statusbar_session_status.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self._lbl_statusbar_scanner_status = QLabel(self._ui.statusBar)
        self._lbl_statusbar_scanner_status.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self._lbl_statusbar_stack_size = QLabel(self._ui.statusBar)
        self._lbl_statusbar_stack_size.setMinimumWidth(150)
        self._lbl_statusbar_stack_size.setAlignment(Qt.AlignHCenter)
        self._lbl_statusbar_stack_size.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self._lbl_statusbar_web_server_status = QLabel(self._ui.statusBar)
        self._lbl_statusbar_web_server_status.setOpenExternalLinks(True)
        self._lbl_statusbar_web_server_status.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self._ui.statusBar.addPermanentWidget(self._lbl_statusbar_session_status)
        self._ui.statusBar.addPermanentWidget(self._lbl_statusbar_scanner_status)
        self._ui.statusBar.addPermanentWidget(self._lbl_statusbar_stack_size)
        self._ui.statusBar.addPermanentWidget(self._lbl_statusbar_web_server_status)

        self._ui.action_night_mode.setChecked(config.get_night_mode_active())

        # handle first run
        if DYNAMIC_DATA.is_first_run:
            _LOGGER.info("First run detected")

            message_box(
                self.tr("Welcome to ALS"),
                self.tr('It appears this is your first use of ALS. Welcome !') + linesep*2 +
                self.tr('Clicking OK will bring up the settings page.') + linesep*2 +
                self.tr("Make sure the scan & work folders are set correctly : They must be created by you..."))

            if self._open_preferences():
                self.update_display()

        self.update_display()
        MESSAGE_HUB.add_receiver(self)

        if config.get_full_screen_active():
            self._ui.action_full_screen.setChecked(True)
        else:
            self.show()

    @log
    @pyqtSlot(bool)
    def on_chk_stretch_active_clicked(self, checked: bool):
        """
        Qt slot executed when autostretch 'active' checkbox is clicked

        :param checked: is the box now checked ?
        :type: bool
        """

        self._ui.btn_stretch_reload.setEnabled(checked)
        self._ui.btn_stretch_reset.setEnabled(checked)
        self._ui.btn_stretch_apply.setEnabled(checked)
        self._ui.sld_stretch_strength.setEnabled(checked)

        self._apply_autostretch()

    @log
    @pyqtSlot(bool)
    def on_chk_levels_active_clicked(self, checked: bool):
        """
        Qt slot executed when levels 'active' checkbox is clicked

        :param checked: is the box now checked ?
        :type: bool
        """

        self._ui.btn_levels_reload.setEnabled(checked)
        self._ui.btn_levels_reset.setEnabled(checked)
        self._ui.btn_levels_apply.setEnabled(checked)
        self._ui.sld_black.setEnabled(checked)
        self._ui.sld_midtones.setEnabled(checked)
        self._ui.sld_white.setEnabled(checked)

        self._apply_levels()

    @log
    @pyqtSlot(bool)
    def on_chk_rgb_active_clicked(self, checked: bool):
        """
        Qt slot executed when RGB 'active' checkbox is clicked

        :param checked: is the box now checked ?
        :type: bool
        """

        self._ui.btn_rgb_reload.setEnabled(checked)
        self._ui.btn_rgb_reset.setEnabled(checked)
        self._ui.btn_rgb_apply.setEnabled(checked)
        self._ui.sld_rgb_r.setEnabled(checked)
        self._ui.sld_rgb_g.setEnabled(checked)
        self._ui.sld_rgb_b.setEnabled(checked)

        self._apply_rgb()

    @log
    @pyqtSlot(name="on_btn_stretch_apply_clicked")
    def _apply_autostretch(self):
        """
        Apply autostretch processing
        """
        update_params_from_controls(self._autostretch_parameters, self._autostretch_controls)

        self._controller.apply_processing()

    @log
    @pyqtSlot(name="on_btn_rgb_apply_clicked")
    def _apply_rgb(self):
        """
        Apply rgb processing
        """
        update_params_from_controls(self._rgb_parameters, self._rgb_controls)

        self._controller.apply_processing()

    @log
    @pyqtSlot(name="on_btn_levels_apply_clicked")
    def _apply_levels(self):
        """
        Apply levels processing
        """
        update_params_from_controls(self._levels_parameters, self._levels_controls)

        self._controller.apply_processing()

    @log
    @pyqtSlot(name="on_btn_stretch_reset_clicked")
    def _reset_autostretch(self):
        """
        Resets autostretch controls to their defaults
        """
        reset_params(self._autostretch_parameters, self._autostretch_controls)

    @log
    @pyqtSlot(name="on_btn_rgb_reset_clicked")
    def _reset_rgb(self):
        """
        Resets rgb controls to their defaults
        """
        reset_params(self._rgb_parameters, self._rgb_controls)

    @log
    @pyqtSlot(name="on_btn_levels_reset_clicked")
    def _reset_levels(self):
        """
        Resets levels processing controls to their defaults
        """
        reset_params(self._levels_parameters, self._levels_controls)

    @log
    @pyqtSlot(name="on_btn_rgb_reload_clicked")
    def _reload_rgb(self):
        """
        Sets rgb controls to their previously recorded values (last apply)
        """
        update_controls_from_params(self._rgb_parameters, self._rgb_controls)

    @log
    @pyqtSlot(name="on_btn_stretch_reload_clicked")
    def _reload_autostretch(self):
        """
        Sets autostretch controls to their previously recorded values (last apply)
        """
        update_controls_from_params(self._autostretch_parameters, self._autostretch_controls)

    @log
    @pyqtSlot(name="on_btn_levels_reload_clicked")
    def _reload_levels(self):
        """
        Sets levels processing controls to their previously recorded values (last apply)
        """
        update_controls_from_params(self._levels_parameters, self._levels_controls)

    @log
    def reset_image_view(self):
        """
        Reset image viewer to its initial state
        """
        for item in self._scene.items():
            self._scene.removeItem(item)
        self._image_item = QGraphicsPixmapItem(QPixmap(":/icons/window_background.png"))
        self._ui.image_view.setBackgroundBrush(QBrush(QColor("#222222"), Qt.SolidPattern))
        self._scene.addItem(self._image_item)

    @log
    def closeEvent(self, event):
        """Handles window close events."""
        # pylint: disable=C0103

        if not self.isFullScreen():
            window_rect = self.geometry()
            config.set_window_geometry((window_rect.x(), window_rect.y(), window_rect.width(), window_rect.height()))

        config.set_full_screen_active(self.isFullScreen())
        config.set_night_mode_active(self._ui.action_night_mode.isChecked())
        self._save_config()

        self._stop_session()

        if DYNAMIC_DATA.session.is_stopped:

            image_waiter = SaveWaitDialog(self._controller, self)

            if image_waiter.count_remaining_images() > 0:
                image_waiter.exec()

            event.accept()
        else:
            event.ignore()

    @log
    @pyqtSlot(bool)
    def on_btn_follow_logs_clicked(self, checked):
        """
        scroll session log to last message when checkbox is checked

        :param checked: is the checkbox checked ?
        :type checked: bool
        """

        if checked:
            self._ui.log.scrollToBottom()

    @log
    @pyqtSlot(bool)
    def on_btn_issues_only_clicked(self, toggled):
        """
        Filters out INFO messages from session log button is toggled

        :param toggled: is button toggled ?
        :type toggled: bool
        """

        if toggled:
            for item in self._ui.log.findItems(_INFO_LOG_TAG, Qt.MatchContains):
                item.setHidden(True)
        else:
            for i in range(self._ui.log.count()):
                self._ui.log.item(i).setHidden(False)

        if self._ui.btn_follow_logs.isChecked():
            self._ui.log.scrollToBottom()

    @pyqtSlot(name="on_pbSave_clicked")
    @log
    def cb_save(self):
        """
        Qt slot for mouse clicks on the 'save' button.

        This saves the processed image using user chosen format

        """
        image_to_save = DYNAMIC_DATA.post_processor_result
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
    @log
    def on_cb_stacking_mode_currentTextChanged(self, stacking_mode: str):
        """
        Qt slot executed when stacking mode comb box changed

        :param stacking_mode: new stacking mode
        :type stacking_mode: str
        """
        self._controller.set_stacking_mode(stacking_mode)

    @log
    def on_chk_align_toggled(self, checked: bool):
        """
        Qt slot executed when 'align' check box is changed

        :param checked: is checkbox checked ?
        :type checked: bool
        """
        self._controller.set_align_before_stack(checked)

    @log
    def on_chk_save_every_image_toggled(self, checked: bool):
        """
        Qt slot executed when 'save ever image' check box is changed

        :param checked: is checkbox checked ?
        :type checked: bool
        """
        self._controller.set_save_every_image(checked)

    @pyqtSlot()
    @log
    def on_btn_web_start_clicked(self):
        """
        Qt slot executed when START web button is clicked
        """
        try:
            self._controller.start_www()
            self._qrDisplay.update_code()

        except WebServerFailedToStart as start_failure:
            error_box(start_failure.message, start_failure.details)

        except WebServerOnLoopback:
            title = self.tr("Web server access is limited")
            message = self.tr("Web server IP address is 127.0.0.1.\n\nServer won't be reachable by other machines. "
                              "Please check your network connection")
            warning_box(title, message)

    @pyqtSlot()
    @log
    def on_btn_web_stop_clicked(self):
        """
        Qt slot executed when START web button is clicked
        """
        self._controller.stop_www()
        self._qrDisplay.setVisible(False)

    @log
    def on_action_full_screen_toggled(self, checked):
        """
        Qt slot executed when action 'Full screen' is toggled

        :param checked: is the action active ?
        :type checked: bool
        """

        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    # pylint: disable=no-self-use
    @log
    @pyqtSlot(bool)
    def on_action_night_mode_toggled(self, checked):
        """
        Sets night mode according to menu item state

        :param checked: is 'night mode' menu item checked ?
        :type checked: bool
        """

        if checked:
            qApp.setStyleSheet(get_text_content_of_resource(":/main/main.css"))
        else:
            qApp.setStyleSheet("")

    @log
    @pyqtSlot(bool)
    def on_action_qrcode_toggled(self, checked):
        """
        QR action has changed : we deal with QR Code display

        :param checked: is action now checked ?
        :type checked: bool
        """
        self._qrDisplay.setVisible(checked)

    @log
    def on_qr_display_visibility_changed(self, visible):
        """
        QR Code display's visibility just changed.

        :param visible: is QR code visible now ?
        :type visible: bool
        """
        self._ui.action_qrcode.setChecked(visible)

    @pyqtSlot()
    @log
    def on_action_image_only_triggered(self):
        """
        Qt slot executed when 'image only' action is triggered
        """

        actions_restore_mapping = {

            self._ui.action_show_processing_panel: self._restore_processing_dock,
            self._ui.action_show_session_controls: self._restore_session_dock,
            self._ui.action_show_session_log: self._restore_log_dock,
        }

        checked = self._ui.action_image_only.isChecked()

        if checked:

            self._restore_session_dock = self._ui.session_dock.isVisible()
            self._restore_log_dock = self._ui.log_dock.isVisible()
            self._restore_processing_dock = self._ui.processing_dock.isVisible()

            for action in actions_restore_mapping:

                if action.isChecked():
                    action.trigger()

        else:
            for action, restore in actions_restore_mapping.items():

                if restore:
                    action.trigger()

    @log
    def on_processing_dock_visibilityChanged(self, visible):
        """
        Qt slot executed when prcessing dock visibility changed

        :param visible: is it now visible ?
        :type visible: bool
        """

        if visible:
            self._cancel_image_only_mode()

    @log
    def on_log_dock_visibilityChanged(self, visible):
        """
        Qt slot executed when log dock visibility changed

        :param visible: is it now visible ?
        :type visible: bool
        """
        self._update_issues_button_visibility()

        if visible:
            self._cancel_image_only_mode()
            self._ui.log.scrollToBottom()

    @log
    @pyqtSlot(bool)
    def on_btn_issues_clicked(self, _):
        """ Main control panel issues button clicked """

        if not self._ui.log_dock.isVisible():
            self._ui.log_dock.setVisible(True)

    @log
    @pyqtSlot(bool)
    def on_btn_issues_ack_clicked(self, _):
        """ issues ack button clicked """

        self._ui.action_ack_issues.trigger()

    @log
    @pyqtSlot()
    def on_action_ack_issues_triggered(self):
        """ user acknowledged issues """

        DYNAMIC_DATA.has_new_warnings = False
        self.update_display(False)

    # pylint: disable=no-self-use
    @log
    def on_log_itemClicked(self, item):
        """
        Copy clicked log line content to clipboard

        :param item: the clicked log item
        :type item: PyQt5.QtWidgets.QListWidgetItem
        """
        QApplication.clipboard().setText(item.text())

    @log
    def on_session_dock_visibilityChanged(self, visible):
        """
        Qt slot executed when session dock visibility changed

        :param visible: is it now visible ?
        :type visible: bool
        """

        if visible:
            self._cancel_image_only_mode()

    @log
    def _cancel_image_only_mode(self):
        """
        Untick 'image only' menu entry
        """

        self._ui.action_image_only.setChecked(False)

    @log
    def _update_image(self):
        """
        Update central image display.
        """
        self._image_item.setPixmap(DYNAMIC_DATA.post_processor_result_qimage)

    @pyqtSlot(name="on_pbPlay_clicked")
    @log
    def cb_play(self):
        """Qt slot for mouse clicks on the 'play' button"""

        self._start_session()

    @log
    def on_message(self, message):
        """
        print received message to GUI log window

        :param message: the message
        :type message: str
        """
        new_item = QListWidgetItem(message)
        if any([log_type in message for log_type in ['WARNING', 'ERROR']]):
            DYNAMIC_DATA.has_new_warnings = True

        self._ui.log.addItem(new_item)
        if _INFO_LOG_TAG in message and self._ui.btn_issues_only.isChecked():
            new_item.setHidden(True)

        if self._ui.btn_follow_logs.isChecked() and self._ui.log.isVisible():
            self._ui.log.scrollToBottom()

    # pylint: disable=too-many-statements
    @log
    def update_display(self, image_only: bool = False):
        """
        Updates all displays and controls depending on DataStore held data
        """

        if image_only:
            self._update_image()
            self._ui.histogram_view.update()

        else:
            web_server_is_running = DYNAMIC_DATA.web_server_is_running
            session = DYNAMIC_DATA.session
            session_is_running = session.is_running
            session_is_stopped = session.is_stopped
            session_is_paused = session.is_paused

            # update scanner statuses
            scanner_status_message = f"{I18n.SCANNER} {I18n.OF} {config.get_scan_folder_path()} : "
            scanner_status_message += f"{I18n.RUNNING_M}" if session_is_running else f"{I18n.STOPPED_M}"
            self._lbl_statusbar_scanner_status.setText(scanner_status_message)

            # update web server status
            if web_server_is_running:
                url = f"http://{DYNAMIC_DATA.web_server_ip}:{config.get_www_server_port_number()}"
                webserver_status = f'{I18n.RUNNING_M} : <a href="{url}" style="color: #CC0000">{url}</a>'
                self._ui.action_qrcode.setEnabled(True)
            else:
                webserver_status = I18n.STOPPED_M
                self._ui.action_qrcode.setDisabled(True)

            self._lbl_statusbar_web_server_status.setText(f"{I18n.WEB_SERVER} : {webserver_status}")
            self._ui.lbl_web_server_status_main.setText(f"{webserver_status}")

            if session_is_stopped:
                session_status = I18n.STOPPED_F
            elif session_is_paused:
                session_status = I18n.PAUSED
            elif session_is_running:
                session_status = I18n.RUNNING_F
            else:
                # this should never happen, that's why we check ;)
                session_status = "### BUG !"
            self._ui.lbl_session_status.setText(f"{session_status}")
            self._lbl_statusbar_session_status.setText(f"{I18n.SESSION} {session_status}")

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
            stack_size_str = str(DYNAMIC_DATA.stack_size)
            self._ui.lbl_stack_size.setText(stack_size_str)
            self._lbl_statusbar_stack_size.setText(f"{I18n.STACK_SIZE} : {stack_size_str}")

            # update queues sizes
            self._ui.lbl_pre_process_queue_size.setText(str(DYNAMIC_DATA.pre_process_queue.qsize()))
            self._ui.lbl_stack_queue_size.setText(str(DYNAMIC_DATA.stacker_queue.qsize()))
            self._ui.lbl_process_queue_size.setText(str(DYNAMIC_DATA.process_queue.qsize()))
            self._ui.lbl_save_queue_size.setText(str(DYNAMIC_DATA.save_queue.qsize()))

            # handle component statuses
            self._ui.lbl_pre_processor_status.setText(I18n.WORKER_STATUS_BUSY if DYNAMIC_DATA.pre_processor_busy else "-")
            self._ui.lbl_stacker_status.setText(I18n.WORKER_STATUS_BUSY if DYNAMIC_DATA.stacker_busy else "-")
            self._ui.lbl_post_processor_status.setText(I18n.WORKER_STATUS_BUSY if DYNAMIC_DATA.post_processor_busy else "-")
            self._ui.lbl_saver_status.setText(I18n.WORKER_STATUS_BUSY if DYNAMIC_DATA.saver_busy else "-")

            # manage warnings
            new_warnings = DYNAMIC_DATA.has_new_warnings
            self._ui.action_ack_issues.setEnabled(new_warnings)

            self._ui.btn_issues_ack.setEnabled(new_warnings)
            self._ui.btn_issues.setEnabled(new_warnings)

            self._ui.btn_issues_ack.setIcon(self._warning_sign_on if new_warnings else self._warning_sign_off)
            self._ui.btn_issues.setIcon(self._warning_sign_on if new_warnings else self._warning_sign_off)

            self._update_issues_button_visibility()

            # disable color balance controls on B&W image
            if DYNAMIC_DATA.post_processor_result:
                self._ui.rgbProcessBox.setEnabled(DYNAMIC_DATA.post_processor_result.is_color())

            self._ui.lbl_last_timing.setText(self.tr("Last image total time: {} s").format(DYNAMIC_DATA.last_timing))

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

    @log
    def _start_session(self, is_retry: bool = False):
        """
        Stars session

        :param is_retry: is this a retry ?
        :type is_retry: bool
        """

        try:
            if DYNAMIC_DATA.session.is_stopped:
                self._ui.log.clear()
            self._controller.start_session()
            if is_retry:
                message_box(self.tr("Session started"), self.tr("Session successfully started after retry"))

        except CriticalFolderMissing as folder_missing:

            text = folder_missing.details + "\n\n"
            text += self.tr("Would you like to open the preferences box ?")

            if question(folder_missing.message, text) and self._open_preferences():
                self._start_session(is_retry=True)

        except SessionError as session_error:
            error_box(session_error.message, str(session_error.details) + "\n\n" + self.tr("Session start aborted"))

    @log
    def _stop_session(self, ask_confirmation: bool = True):
        """
        Stops sessions

        :param ask_confirmation: do we ask user for confirmation ?
        :type ask_confirmation: bool
        """

        if not DYNAMIC_DATA.session.is_stopped:

            do_stop_session = True
            stop_dialog = SessionStopDialog()

            if ask_confirmation and DYNAMIC_DATA.stack_size > 0:

                do_stop_session = stop_dialog.exec()

            if do_stop_session:
                if stop_dialog.save_on_stop and DYNAMIC_DATA.post_processor_result is not None:
                    self._controller.save_post_process_result(final=True)
                self._controller.stop_session()

    @log
    def _open_preferences(self):
        """
        Opens preferences dialog box and return True if dialog was closed using "OK"

        :return: Was the dilaog closed with "OK" ?
        :rtype: bool
        """

        accepted = PreferencesDialog(self).exec() == QDialog.Accepted

        if accepted:
            self.update_display()

        return accepted

    @log
    def _save_config(self):

        try:
            config.save()
        except CouldNotSaveConfig as save_error:
            error_box(
                save_error.message,
                self.tr("Your settings could not be saved\n\nDetails : {}").format(save_error.details))

    @log
    def _update_issues_button_visibility(self):
        """ update issues button according to warnings & log visibility """

        self._ui.btn_issues.setVisible(

            self._ui.action_ack_issues.isEnabled() and not self._ui.log_dock.isVisible()
        )
