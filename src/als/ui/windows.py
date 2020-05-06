"""
Holds all windows used in the app
"""
import logging

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QPixmap, QBrush, QColor
from PyQt5.QtWidgets import QMainWindow, QGraphicsScene, QGraphicsPixmapItem, QDialog
from qimage2ndarray import array2qimage

import als.model.data
from als import config
from als.config import CouldNotSaveConfig
from als.logic import Controller, SessionError, CriticalFolderMissing, WebServerStartFailure
from als.messaging import MESSAGE_HUB
from als.code_utilities import log
from als.model.data import DYNAMIC_DATA, I18n
from als.ui.dialogs import PreferencesDialog, AboutDialog, error_box, warning_box, SaveWaitDialog, question, message_box
from als.ui.params_utils import update_controls_from_params, update_params_from_controls, reset_params, \
    set_sliders_defaults
from generated.als_ui import Ui_stack_window

_LOGGER = logging.getLogger(__name__)


# pylint: disable=R0904, R0902
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
        self.setWindowTitle("Astro Live Stacker")

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
            self._ui.cb_stretch_method,
            self._ui.sld_stretch_strength
        ]

        self._autostretch_parameters = self._controller.get_autostretch_parameters()

        set_sliders_defaults(
            [self._autostretch_parameters[2]],
            [self._ui.sld_stretch_strength]
        )

        for label in self._autostretch_parameters[1].choices:
            self._ui.cb_stretch_method.addItem(label)

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
        self.update_display()

        self.setGeometry(*config.get_window_geometry())

        # setup management of 'image only' mode
        self._restore_log_dock = False
        self._restore_session_dock = False
        self._restore_processing_dock = False
        self._ui.lbl_stack_size_mini.setVisible(self._ui.action_image_only.isChecked())

        # setup image display
        self._scene = QGraphicsScene(self)
        self._ui.image_view.setScene(self._scene)
        self._image_item = None
        self.reset_image_view()

        if config.get_full_screen_active():
            self._ui.action_full_screen.setChecked(True)
        else:
            self.show()

        MESSAGE_HUB.add_receiver(self)

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
        self._ui.cb_stretch_method.setEnabled(checked)
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
        self._image_item = QGraphicsPixmapItem(QPixmap(":/icons/dslr-camera.svg"))
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
    def on_chk_follow_logs_clicked(self, checked):
        """
        scroll session log to last message when checkbox is checked

        :param checked: is the checkbox checked ?
        :type checked: bool
        """
        if checked:
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
        self._start_www()

    @pyqtSlot()
    @log
    def on_btn_web_stop_clicked(self):
        """
        Qt slot executed when START web button is clicked
        """
        self._stop_www()

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

    @pyqtSlot()
    @log
    def on_action_image_only_triggered(self):
        """
        Qt slot executed when 'image only' action is triggered
        """

        self._ui.lbl_stack_size_mini.setVisible(self._ui.action_image_only.isChecked())

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

        if visible:
            self._cancel_image_only_mode()

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
        image_raw_data = DYNAMIC_DATA.post_processor_result.data.copy()

        image = array2qimage(image_raw_data, normalize=(2 ** 16 - 1))
        self._image_item.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(name="on_pbPlay_clicked")
    @log
    def cb_play(self):
        """Qt slot for mouse clicks on the 'play' button"""

        self._start_session()

    def on_message(self, message):
        """
        print received message to GUI log window

        :param message: the message
        :type message: str
        """
        self._ui.log.addItem(message)
        if self._ui.chk_follow_logs.isChecked():
            self._ui.log.scrollToBottom()

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
            self._ui.lbl_scanner_status.setText(scanner_status_message)

            # update web server status
            if web_server_is_running:
                url = f"http://{DYNAMIC_DATA.web_server_ip}:{config.get_www_server_port_number()}"
                webserver_status = f'{I18n.RUNNING_M}, ' \
                                   f'{I18n.ADDRESS} =  <a href="{url}" style="color: #CC0000">{url}</a>'
            else:
                webserver_status = I18n.STOPPED_M
            self._ui.lbl_web_server_status.setText(f"{I18n.WEB_SERVER} : {webserver_status}")

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

            # update preferences accessibility according to session and web server status
            preferences_enabled = not web_server_is_running and session_is_stopped
            self._ui.action_prefs.setEnabled(preferences_enabled)

            if preferences_enabled:
                self._ui.action_prefs.setToolTip("")
            else:
                self._ui.action_prefs.setToolTip(self.tr("Preferences are avaialble when session and webserver "
                                                         "are both stopped"))

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
            self._ui.lbl_stack_size_mini.setText(f"{I18n.STACK_SIZE} : {stack_size_str}")

            # update queues sizes
            self._ui.lbl_pre_process_queue_size.setText(str(DYNAMIC_DATA.pre_process_queue.qsize()))
            self._ui.lbl_stack_queue_size.setText(str(DYNAMIC_DATA.stacker_queue.qsize()))
            self._ui.lbl_process_queue_size.setText(str(DYNAMIC_DATA.process_queue.qsize()))
            self._ui.lbl_save_queue_size.setText(str(DYNAMIC_DATA.save_queue.qsize()))

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

    @log
    def _start_www(self):
        """Starts web server"""

        try:
            self._controller.start_www()
            if DYNAMIC_DATA.web_server_ip == "127.0.0.1":
                title = self.tr("Web server access is limited")
                message = self.tr("Web server IP address is 127.0.0.1.\n\nServer won't be reachable by other machines. "
                                  "Please check your network connection")
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

            if ask_confirmation and DYNAMIC_DATA.stack_size > 0:
                message = (
                    self.tr("Stopping the current session will reset the stack and all image enhancements.\n\n"
                            "Are you sure you want to stop the current session ?"))

                do_stop_session = question(self.tr("Really stop session ?"),
                                           message,
                                           default_yes=False)

            if do_stop_session:
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
            error_box(save_error.message, self.tr("Your settings could not be saved\n\nDetails : {}").format(save_error.details))
