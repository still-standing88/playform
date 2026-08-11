import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFileDialog,
    QMessageBox
)
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt

from tools.speech_converter.engine import SpeechEngine, IS_WINDOWS
from tools.speech_converter.parameters_dialog import ParametersDialog
from tools.speech_converter.job import SaveSpeechJob
from gui_controls.job_progress_dialog import JobProgressDialog
from utilities import signal_manager

_SAVE_FILTER = "MP3 Audio (*.mp3);;WAV Audio (*.wav);;OGG Audio (*.ogg);;FLAC Audio (*.flac);;All Files (*.*)"


class SpeechTextEdit(QTextEdit):

    def __init__(self, open_callback, save_callback, parent=None):
        super().__init__(parent)
        self._open_callback = open_callback
        self._save_callback = save_callback
        self.setTabChangesFocus(True)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        menu.addAction(_("Open Text File..."), self._open_callback)
        menu.addAction(_("Save As..."), self._save_callback)
        menu.exec(event.globalPos())


class SpeechConverterUI(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = SpeechEngine(self)
        self.engine.state_changed.connect(self._on_state_changed)
        self.engine.error_occurred.connect(self._on_error)

        self.save_job = None
        self.progress_dialog = None

        self.parameters = {
            "volume": 1.0, "rate": 0.0, "pitch": 0.0,
            "use_pitch_xml": self.engine.supports_pitch_xml(), "pitch_xml_middle": 0,
        }

        self._build_ui()
        self._apply_parameters()
        self._update_buttons("ready")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.text_edit = SpeechTextEdit(self._open_text_file, self._save_as, self)
        self.text_edit.setPlaceholderText(_("Type or paste text to speak..."))
        self.text_edit.setAccessibleName(_("Text to speak"))
        self.text_edit.setAccessibleDescription(
            _("Right-click for Open Text File and Save As. Shortcuts: F7 speak/pause, "
              "F8 stop, Ctrl+O open, Ctrl+S save, Ctrl+F parameters.")
        )
        layout.addWidget(self.text_edit, stretch=1)

        button_row = QHBoxLayout()
        self.speak_button = QPushButton(_("Speak"), self)
        self.pause_button = QPushButton(_("Pause"), self)
        self.stop_button = QPushButton(_("Stop"), self)
        self.save_button = QPushButton(_("Save..."), self)
        self.parameters_button = QPushButton(_("Parameters..."), self)

        self.speak_button.clicked.connect(self._on_speak)
        self.pause_button.clicked.connect(self._on_pause_resume)
        self.stop_button.clicked.connect(self._on_stop)
        self.save_button.clicked.connect(self._save_as)
        self.parameters_button.clicked.connect(self._open_parameters)

        for button in (self.speak_button, self.pause_button, self.stop_button,
                       self.save_button, self.parameters_button):
            button_row.addWidget(button)
        layout.addLayout(button_row)

        self._install_shortcuts()

    def _install_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_F7), self, activated=self._on_speak_pause_shortcut)
        QShortcut(QKeySequence(Qt.Key.Key_F8), self, activated=self._on_stop)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_as)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._open_text_file)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._open_parameters)

    def _apply_parameters(self):
        self.engine.set_volume(self.parameters["volume"])
        self.engine.set_rate(self.parameters["rate"])
        self.engine.set_pitch(self.parameters["pitch"])

    def _open_parameters(self):
        dialog = ParametersDialog(self.engine, self.parameters, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.parameters = dialog.values()
            self._apply_parameters()

    def _on_speak_pause_shortcut(self):
        state = self.engine.state()
        from PySide6.QtTextToSpeech import QTextToSpeech
        if state == QTextToSpeech.State.Speaking:
            self._on_pause_resume()
        else:
            self._on_speak()

    def _on_speak(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            return
        self.engine.speak(text, self.parameters["use_pitch_xml"], self.parameters["pitch_xml_middle"])

    def _on_pause_resume(self):
        from PySide6.QtTextToSpeech import QTextToSpeech
        state = self.engine.state()
        if state == QTextToSpeech.State.Speaking:
            self.engine.pause()
        elif state == QTextToSpeech.State.Paused:
            self.engine.resume()

    def _on_stop(self):
        self.engine.stop()

    def _open_text_file(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Open Text File"), "", "Text Files (*.txt);;All Files (*.*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                self.text_edit.setPlainText(handle.read())
        except OSError as error:
            QMessageBox.critical(self, _("Error"), str(error))

    def _save_as(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, _("Warning"), _("There is no text to speak."))
            return

        if not self.engine.can_save_to_file():
            QMessageBox.warning(
                self, _("Not Supported"),
                _("Saving speech to an audio file requires the Windows SAPI5 engine.")
            )
            return

        path, _filter = QFileDialog.getSaveFileName(self, _("Save Speech As"), "", _SAVE_FILTER)
        if not path:
            return

        self.save_job = SaveSpeechJob(
            self.engine, text, path, self.parameters["use_pitch_xml"], self.parameters["pitch_xml_middle"]
        )
        self.save_job.finished_job.connect(lambda ok, error: self._on_save_finished(ok, error, path))

        self.progress_dialog = JobProgressDialog(0, self, title=_("Saving Speech..."), supports_pause=False)
        self.progress_dialog.cancel_requested.connect(self.progress_dialog.accept)
        self.progress_dialog.current_file_label.setText(_("Rendering speech to {path}...").format(path=path))

        self.save_button.setEnabled(False)
        self.save_job.start()
        self.progress_dialog.show()

    def _on_save_finished(self, success: bool, error: str, path: str):
        self.save_button.setEnabled(self.engine.can_save_to_file())
        if self.progress_dialog:
            self.progress_dialog.append_file_result(
                _("Saved to {path}").format(path=path) if success
                else _("FAILED: {error}").format(error=error or _("Unknown error"))
            )
            self.progress_dialog.mark_finished(success)
            self.progress_dialog = None

        if success:
            signal_manager.statusbar_message.emit(_("Speech saved to {path}").format(path=path))
        else:
            QMessageBox.critical(self, _("Error"), error or _("Unknown error"))
        self.save_job = None

    def _on_state_changed(self, state: str):
        self._update_buttons(state)

    def _on_error(self, message: str):
        signal_manager.statusbar_message.emit(_("Speech error: {message}").format(message=message))

    def _update_buttons(self, state: str):
        speaking = state == "speaking"
        paused = state == "paused"
        self.pause_button.setText(_("Resume") if paused else _("Pause"))
        self.pause_button.setEnabled((speaking or paused) and self.engine.supports_pause_resume())
        self.stop_button.setEnabled(speaking or paused)
        self.save_button.setEnabled(self.engine.can_save_to_file())
