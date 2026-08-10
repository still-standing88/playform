"""Live transport view - replaces the old Capture tab. Shown in place of
ConfigureView (see ui.py's QStackedWidget) while a capture is running, so
the session/source configuration UI isn't sitting there editable mid-
recording; ConfigureView comes back once the engine reports "stopped"/
"idle".
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from ..models import CaptureSource, Session
from ..registries import SourceRegistry

_ROLE_ID = 1000


class CaptureView(QWidget):
    pause_requested = Signal()
    resume_requested = Signal()
    stop_requested = Signal()

    def __init__(self, sources: SourceRegistry, parent=None):
        super().__init__(parent)
        self.sources = sources
        self._paused = False

        layout = QVBoxLayout(self)

        self.session_label = QLabel()
        bold_font = self.session_label.font()
        bold_font.setBold(True)
        self.session_label.setFont(bold_font)
        layout.addWidget(self.session_label)

        self.status_label = QLabel(_("Idle"))
        layout.addWidget(self.status_label)

        self.live_list = QListWidget()
        layout.addWidget(self.live_list)

        transport = QHBoxLayout()
        self.pause_btn = QPushButton(_("Pause"))
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.stop_btn = QPushButton(_("Cancel"))
        self.stop_btn.setToolTip(_("Stop and finalize the recording (files already captured are kept)."))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        transport.addWidget(self.pause_btn)
        transport.addWidget(self.stop_btn)
        layout.addLayout(transport)

    def begin(self, session: Session, sources: list[CaptureSource]) -> None:
        self.session_label.setText(_("Session: {name}").format(name=session.name))
        self.status_label.setText(_("Starting..."))
        self._paused = False
        self.pause_btn.setText(_("Pause"))
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        self.live_list.clear()
        for source in sources:
            item = QListWidgetItem(f"{source.friendly_name}  -  {_('waiting...')}")
            item.setData(_ROLE_ID, source.id)
            self.live_list.addItem(item)

    def is_paused(self) -> bool:
        return self._paused

    def _on_pause_clicked(self) -> None:
        self.pause_btn.setEnabled(False)
        if self._paused:
            self.resume_requested.emit()
        else:
            self.pause_requested.emit()

    def _on_stop_clicked(self) -> None:
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.status_label.setText(_("Stopping..."))
        self.stop_requested.emit()

    # -- engine signal handlers (wired by ui.py) -----------------------

    def on_state_changed(self, state: str) -> None:
        if state == "recording":
            self._paused = False
            self.status_label.setText(_("Recording"))
            self.pause_btn.setText(_("Pause"))
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        elif state == "paused":
            self._paused = True
            self.status_label.setText(_("Paused"))
            self.pause_btn.setText(_("Resume"))
            self.pause_btn.setEnabled(True)
        elif state in ("idle", "stopped"):
            self._paused = False
            self.status_label.setText(_("Idle"))
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    def on_source_started(self, source_id: str, output_path: str) -> None:
        self._set_status(source_id, _("recording -> {path}").format(path=output_path))

    def on_source_error(self, source_id: str, message: str) -> None:
        if source_id:
            self._set_status(source_id, _("error: {message}").format(message=message))

    def on_source_stopped(self, source_id: str, final_path: str) -> None:
        text = _("stopped -> {path}").format(path=final_path) if final_path else _("stopped")
        self._set_status(source_id, text)

    def on_duration_changed(self, source_id: str, elapsed_seconds: float) -> None:
        minutes, seconds = divmod(int(elapsed_seconds), 60)
        self._set_status(source_id, _("recording - {m:02d}:{s:02d}").format(m=minutes, s=seconds))

    def _set_status(self, source_id: str, text: str) -> None:
        for i in range(self.live_list.count()):
            item = self.live_list.item(i)
            if item.data(_ROLE_ID) == source_id:
                source = self.sources.get(source_id)
                name = source.friendly_name if source else source_id
                item.setText(f"{name}  -  {text}")
                return
