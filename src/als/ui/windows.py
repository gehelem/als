"""
Holds all windows used in the app
"""
import logging

from PyQt5.QtCore import QEvent, pyqtSlot, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QGraphicsScene, QGraphicsPixmapItem, QApplication
from qimage2ndarray import array2qimage

from als import model, config
from als.logic import Controller, SessionManagementError
from als.code_utilities import log
from als.io.network import get_ip, StoppableServerThread
from als.io.output import ImageSaver
from als.model import STACKING_MODE_SUM, STACKING_MODE_MEAN, VERSION, DYNAMIC_DATA
from als.processing import PreProcessPipeline, PostProcessPipeline
from als.stack import Stacker
from als.ui.dialogs import PreferencesDialog, AboutDialog, error_box, warning_box
from generated.als_ui import Ui_stack_window

_LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    ALS main window.
    """

    _LOG_DOCK_INITIAL_HEIGHT = 80

    @log
    def __init__(self, controller: Controller, parent=None):

        super().__init__(parent)
        self._controller = controller

        self._ui = Ui_stack_window()
        self._ui.setupUi(self)
        self.setWindowTitle(_("Astro Live Stacker") + f" - v{VERSION}")
        self._ui.cb_stacking_mode.addItem(STACKING_MODE_SUM)
        self._ui.cb_stacking_mode.addItem(STACKING_MODE_MEAN)
        self._ui.cb_stacking_mode.setCurrentIndex(0)
        self._ui.postprocess_widget.setCurrentIndex(0)

        # store if docks must be shown or not
        self.shown_log_dock = True
        self.show_session_dock = True

        self.counter = 0

        # web stuff
        self.thread = None
        self.web_dir = None

        # prevent log dock to be too tall
        self.resizeDocks([self._ui.log_dock], [self._LOG_DOCK_INITIAL_HEIGHT], Qt.Vertical)

        model.DYNAMIC_DATA.add_observer(self)

        self._image_saver = ImageSaver(DYNAMIC_DATA.save_queue)
        self._image_saver.start()

        self._pre_process_pipeline = PreProcessPipeline(DYNAMIC_DATA.input_queue, DYNAMIC_DATA.stack_queue)
        self._pre_process_pipeline.start()

        self._stacker = Stacker(DYNAMIC_DATA.stack_queue, DYNAMIC_DATA.process_queue)
        self._stacker.start()
        self._stacker.stack_size_changed_signal[int].connect(self.on_stack_size_changed)

        self._post_process_pipeline = PostProcessPipeline(DYNAMIC_DATA.process_queue)
        self._post_process_pipeline.start()
        self._post_process_pipeline.new_processing_result_signal.connect(self.on_new_process_result)

        self.update_according_to_app_state()

        DYNAMIC_DATA.input_queue.item_pushed_signal[int].connect(self.on_input_queue_pushed)
        DYNAMIC_DATA.input_queue.item_popped_signal[int].connect(self.on_input_queue_popped)

        DYNAMIC_DATA.stack_queue.item_pushed_signal[int].connect(self.on_stack_queue_pushed)
        DYNAMIC_DATA.stack_queue.item_popped_signal[int].connect(self.on_stack_queue_popped)

        DYNAMIC_DATA.process_queue.item_pushed_signal[int].connect(self.on_process_queue_pushed)
        DYNAMIC_DATA.process_queue.item_popped_signal[int].connect(self.on_process_queue_popped)

        DYNAMIC_DATA.save_queue.item_pushed_signal[int].connect(self.on_save_queue_pushed)
        DYNAMIC_DATA.save_queue.item_popped_signal[int].connect(self.on_save_queue_popped)

        self._scene = QGraphicsScene(self)
        self._ui.image_view.setScene(self._scene)
        self._image_item = None

        self.reset_image_view()

    @log
    def reset_image_view(self):
        """
        Reset image viewer to its inital state
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

        if DYNAMIC_DATA.web_server_is_running:
            self._stop_www()

        self._pre_process_pipeline.stop()
        self._stacker.stop()
        self._post_process_pipeline.stop()

        _LOGGER.debug(f"Window size : {self.size()}")
        _LOGGER.debug(f"Window position : {self.pos()}")

        window_rect = self.geometry()
        config.set_window_geometry((window_rect.x(), window_rect.y(), window_rect.width(), window_rect.height()))
        config.save()

        self._image_saver.stop()

        if self._image_saver.isRunning():
            message = "Making sure all images are saved..."
            _LOGGER.info(message)
            self._ui.statusBar.showMessage(message)
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self._image_saver.wait()

        DYNAMIC_DATA.remove_observer(self)
        super().closeEvent(event)

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

    # ------------------------------------------------------------------------------
    # Callbacks

    @pyqtSlot(int, name="on_SCNR_Slider_valueChanged")
    @log
    def cb_scnr_slider_changed(self, value):
        """
        Qt slot for SCNR slider changes.

        :param value: SCNR slider new value
        :type value: int
        """
        self._ui.SCNR_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_R_slider_valueChanged")
    @log
    def cb_r_slider_changed(self, value):
        """
        Qt slot for R slider changes.

        :param value: R slider new value
        :type value: int
        """
        self._ui.R_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_G_slider_valueChanged")
    @log
    def cb_g_slider_changed(self, value):
        """
        Qt slot for G slider changes.

        :param value: G slider new value
        :type value: int
        """
        self._ui.G_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_B_slider_valueChanged")
    @log
    def cb_b_slider_changed(self, value):
        """
        Qt slot for B slider changes.

        :param value: B slider new value
        :type value: int
        """
        self._ui.B_value.setNum(value / 100.)

    @pyqtSlot(int, name="on_contrast_slider_valueChanged")
    @log
    def cb_contrast_changed(self, value):
        """
        Qt slot for contrast slider changes.

        :param value: contrast slider new value
        :type value: int
        """
        self._ui.contrast.setNum(value / 10)

    @pyqtSlot(bool, name="on_cbWww_clicked")
    @log
    def cb_www_check(self, checked):
        """
        Qt slot for mouse clicks on 'www' checkbox.

        :param checked: True if the checkbox is checked, False otherwise
        :type checked: bool
        """
        if checked:
            self._start_www()
        else:
            self._stop_www()

    @pyqtSlot(name="on_pbSave_clicked")
    @log
    def cb_save(self):
        """
        Qt slot for louse clicks on the 'save' button.

        This saves the processed image using user chosen format

        """
        image_to_save = DYNAMIC_DATA.process_result
        if image_to_save is not None:
            self._controller.save_image(image_to_save,
                                        config.get_image_save_format(),
                                        config.get_work_folder_path(),
                                        config.STACKED_IMAGE_FILE_NAME_BASE,
                                        True)

    @pyqtSlot(name="on_pb_apply_value_clicked")
    @log
    def cb_apply_value(self):
        """Qt slot for clicks on the 'apply' button"""
        if self.counter > 0:
            self.adjust_value()
            self.update_image()
        _LOGGER.info("Define new display value")

    @pyqtSlot(name="on_action_quit_triggered")
    @log
    def cb_quit(self):
        """ Qt slot for activation of the 'quit' action"""
        super().close()

    @pyqtSlot(name="on_action_prefs_triggered")
    @log
    def cb_prefs(self):
        """ Qt slot for activation of the 'preferences' action"""
        dialog = PreferencesDialog(self)
        dialog.exec()

    @pyqtSlot(name="on_action_about_als_triggered")
    @log
    def cb_about(self):
        """ Qt slot for activation of the 'about' action"""
        dialog = AboutDialog(self)
        dialog.exec()

    @log
    def on_input_queue_pushed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the input queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"New image added to the input queue. Input queue size : {new_size}")
        self._ui.lbl_input_queue_size.setText(str(new_size))

    @log
    def on_input_queue_popped(self, new_size):
        """
        Qt slot executed when an item has just been popped from the input queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"Image taken from input queue. Input queue size : {new_size}")
        self._ui.lbl_input_queue_size.setText(str(new_size))

    @log
    def on_stack_queue_pushed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the stack queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"New image added to the stack queue. Stack queue size : {new_size}")
        self._ui.lbl_stack_queue_size.setText(str(new_size))

    @log
    def on_stack_queue_popped(self, new_size):
        """
        Qt slot executed when an item has just been popped from the stack queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"Image taken from stack queue. Stack queue size : {new_size}")
        self._ui.lbl_stack_queue_size.setText(str(new_size))

    @log
    def on_process_queue_pushed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the process queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"New image added to the process queue. Process queue size : {new_size}")
        self._ui.lbl_process_queue_size.setText(str(new_size))

    @log
    def on_process_queue_popped(self, new_size):
        """
        Qt slot executed when an item has just been popped from the process queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"Image taken from process queue. Process queue size : {new_size}")
        self._ui.lbl_process_queue_size.setText(str(new_size))

    @log
    def on_save_queue_pushed(self, new_size):
        """
        Qt slot executed when an item has just been pushed to the save queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"New image added to the save queue. Save queue size : {new_size}")
        self._ui.lbl_save_queue_size.setText(str(new_size))

    @log
    def on_save_queue_popped(self, new_size):
        """
        Qt slot executed when an item has just been popped from the save queue

        :param new_size: new queue size
        :type new_size: int
        """
        _LOGGER.debug(f"Image taken from save queue. Save queue size : {new_size}")
        self._ui.lbl_save_queue_size.setText(str(new_size))

    @log
    def on_stack_size_changed(self, new_size: int):
        """
        Qt slot executed when stack size changed

        :param new_size: new stack size
        :type new_size: int
        """
        self._ui.cnt.setText(str(new_size))

    # pylint: disable=C0103
    @log
    def on_cb_stacking_mode_currentTextChanged(self, text: str):
        """
        Qt slot executed when stacking mode comb box changed

        :param text: new stacking mode
        :type text: str
        :return:
        """
        DYNAMIC_DATA.stacking_mode = text

    @log
    def on_chk_align_toggled(self, checked: bool):
        """
        Qt slot executed when 'align' check box is changed

        :param checked: is checkbox checked ?
        :type checked: bool
        """
        DYNAMIC_DATA.align_before_stacking = checked

    @log
    def on_new_process_result(self):
        """
        Qt slot executed when a new stacking result is available
        """
        self.update_image()
        self._controller.save_process_result()

    @log
    def adjust_value(self):
        """
        Adjusts stacked image according to GUU controls

        """
        # # test rgb or gray
        # if len(self.image_ref_save.image.shape) == 2:
        #     mode = "gray"
        # elif len(self.image_ref_save.image.shape) == 3:
        #     mode = "rgb"
        # else:
        #     raise ValueError(_("fit format not supported"))
        #
        # self.image_ref_save.stack_image = prepro.post_process_image(self.image_ref_save.image,
        #                                                             mode=mode,
        #                                                             scnr_on=self._ui.cbSCNR.isChecked(),
        #                                                             wavelets_on=self._ui.cbWavelets.isChecked(),
        #                                                             wavelets_type=str(self._ui.cBoxWaveType.currentText()),
        #                                                             wavelets_use_luminance=self._ui.cbLuminanceWavelet.isChecked(),
        #                                                             param=[self._ui.contrast_slider.value() / 10.,
        #                                                                    self._ui.brightness_slider.value(),
        #                                                                    self._ui.black_slider.value(),
        #                                                                    self._ui.white_slider.value(),
        #                                                                    self._ui.R_slider.value() / 100.,
        #                                                                    self._ui.G_slider.value() / 100.,
        #                                                                    self._ui.B_slider.value() / 100.,
        #                                                                    self._ui.cmSCNR.currentText(),
        #                                                                    self._ui.SCNR_Slider.value() / 100.,
        #                                                                    {1: int(self._ui.wavelet_1_label.text()) / 100.,
        #                                                                     2: int(self._ui.wavelet_2_label.text()) / 100.,
        #                                                                     3: int(self._ui.wavelet_3_label.text()) / 100.,
        #                                                                     4: int(self._ui.wavelet_4_label.text()) / 100.,
        #                                                                     5: int(self._ui.wavelet_5_label.text()) / 100.}])

    @log
    def update_image(self):
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

        self._ui.white_slider.setEnabled(False)
        self._ui.black_slider.setEnabled(False)
        self._ui.contrast_slider.setEnabled(False)
        self._ui.brightness_slider.setEnabled(False)
        self._ui.R_slider.setEnabled(False)
        self._ui.G_slider.setEnabled(False)
        self._ui.B_slider.setEnabled(False)
        self._ui.pb_apply_value.setEnabled(False)

        self.counter = 0
        self._ui.cnt.setText(str(self.counter))

        try:
            self._controller.start_session()
        except SessionManagementError as session_error:
            error_box(session_error.message, str(session_error.error) + "\n\nSession start aborted")

    def on_log_message(self, message):
        """
        print received log message to GUI log window

        :param message: the log message
        :type message: str
        """
        self._ui.log.addItem(message)
        self._ui.log.scrollToBottom()

    @log
    def update_according_to_app_state(self):
        """
        Updates all displays and controls depending on DataStore held data
        """

        web_server_is_running = DYNAMIC_DATA.web_server_is_running
        session_is_running = DYNAMIC_DATA.session.is_running()
        session_is_stopped = DYNAMIC_DATA.session.is_stopped()
        session_is_paused = DYNAMIC_DATA.session.is_paused()

        # build status bar messages display
        messages = list()

        # update statusBar according to status of folder scanner and web server
        scanner_status_message = f"Scanner on {config.get_scan_folder_path()} : "
        scanner_status_message += f"Running" if session_is_running else "Stopped"
        messages.append(scanner_status_message)

        if web_server_is_running:
            messages.append(f"Web server reachable at "
                            f"http://{get_ip()}:{config.get_www_server_port_number()}")
        else:
            messages.append("Web server : Stopped")

        self._ui.statusBar.showMessage('   -   '.join(messages))

        # update preferences accessibility according to scanner and web server status
        self._ui.action_prefs.setEnabled(not web_server_is_running and not session_is_running)

        # handle Start / Pause / Stop / Reset buttons
        self._ui.pbPlay.setEnabled(session_is_stopped or session_is_paused)
        self._ui.pbReset.setEnabled(session_is_stopped)
        self._ui.pbStop.setEnabled(session_is_running or session_is_paused)
        self._ui.pbPause.setEnabled(session_is_running)

        # handle align + stack mode buttons
        self._ui.chk_align.setEnabled(session_is_stopped)
        self._ui.cb_stacking_mode.setEnabled(session_is_stopped)

    @pyqtSlot(name="on_pbStop_clicked")
    @log
    def cb_stop(self):
        """Qt slot for mouse clicks on the 'Stop' button"""
        self._controller.stop_session()

    @pyqtSlot(name="on_pbPause_clicked")
    @log
    def cb_pause(self):
        """Qt slot for mouse clicks on the 'Pause' button"""
        self._controller.pause_session()

    @pyqtSlot(name="on_pbReset_clicked")
    @log
    def cb_reset(self):
        """Qt slot for mouse clicks on the 'Reset' button"""

        self._ui.contrast_slider.setValue(10)
        self._ui.brightness_slider.setValue(0)
        self._ui.black_slider.setValue(0)
        self._ui.white_slider.setValue(65535)
        self._ui.R_slider.setValue(100)
        self._ui.G_slider.setValue(100)
        self._ui.B_slider.setValue(100)
        self._ui.contrast.setText(str(1))
        self._ui.brightness.setText(str(0))
        self._ui.black.setText(str(0))
        self._ui.white.setText(str(65535))
        self.counter = 0
        self._ui.cnt.setText(str(self.counter))
        self._ui.white_slider.setEnabled(False)
        self._ui.black_slider.setEnabled(False)
        self._ui.contrast_slider.setEnabled(False)
        self._ui.brightness_slider.setEnabled(False)
        self._ui.R_slider.setEnabled(False)
        self._ui.G_slider.setEnabled(False)
        self._ui.B_slider.setEnabled(False)
        self._ui.pb_apply_value.setEnabled(False)
        self._ui.cbSCNR.setChecked(False)
        self._ui.cbWavelets.setChecked(False)
        self._ui.cbLuminanceWavelet.setChecked(False)

        self._stacker.reset()
        self.reset_image_view()

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
        self.web_dir = config.get_work_folder_path()
        ip_address = get_ip()
        port_number = config.get_www_server_port_number()
        try:
            self.thread = StoppableServerThread(self.web_dir)
            self.thread.start()

            # Server is now started and listens on specified port on *all* available interfaces.
            # We get the machine ip address and warn user if detected ip is loopback (127.0.0.1)
            # since in this case, the web server won't be reachable by any other machine
            if ip_address == "127.0.0.1":
                log_function = _LOGGER.warning
                title = "Web server access is limited"
                message = "Web server IP address is 127.0.0.1.\n\nServer won't be reachable by other " \
                          "machines. Please check your network connection"
                warning_box(title, message)
            else:
                log_function = _LOGGER.info

            url = f"http://{ip_address}:{port_number}"
            log_function(f"Web server started. Reachable at {url}")
            self._ui.action_prefs.setEnabled(False)
            QApplication.clipboard().setText(url)
            model.DYNAMIC_DATA.web_server_is_running = True
        except OSError:
            title = "Could not start web server"
            message = f"The web server needs to listen on port n°{port_number} but this port is already in use.\n\n"
            message += "Please change web server port number in your preferences "
            _LOGGER.error(title)
            error_box(title, message)
            self._stop_www()
            self._ui.cbWww.setChecked(False)

    @log
    def _stop_www(self):
        """Stops web server"""
        if self.thread:
            self.thread.stop()
            self.thread.join()
            self.thread = None
            _LOGGER.info("Web server stopped")
            model.DYNAMIC_DATA.web_server_is_running = False
