from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..engine import CaptureEngine
from ..registries import SessionRegistry, SourceRegistry


class CaptureTab(QWidget):
    """Transport: start/pause/resume/stop + live status. Only runs what the
    Sessions tab has already configured - no add/edit/delete here.

    engine.start()/pause()/resume()/stop() are asynchronous (they run on the
    engine's own worker thread - see engine.py's docstring for why), so this
    tab reacts to state_changed/source_* signals rather than a synchronous
    return value; buttons are optimistically disabled on click and
    corrected by the next state_changed."""

    def __init__(self, sessions: SessionRegistry, sources: SourceRegistry, engine: CaptureEngine, parent=None):
        super().__init__(parent)
        self.sessions = sessions
        self.sources = sources
        self.engine = engine

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel(_("Active session")))
        self.session_combo = QComboBox()
        top.addWidget(self.session_combo, 1)
        layout.addLayout(top)

        transport = QHBoxLayout()
        self.start_btn = QPushButton(_("Start"))
        self.pause_btn = QPushButton(_("Pause"))
        self.stop_btn = QPushButton(_("Stop"))
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_capture)
        self.pause_btn.clicked.connect(self.toggle_pause_resume)
        self.stop_btn.clicked.connect(self.stop_capture)
        for b in (self.start_btn, self.pause_btn, self.stop_btn):
            transport.addWidget(b)
        layout.addLayout(transport)

        self.status_label = QLabel(_("Idle"))
        layout.addWidget(self.status_label)

        layout.addWidget(QLabel(_("Sources in active session")))
        self.live_list = QListWidget()
        layout.addWidget(self.live_list)

        self.session_combo.currentIndexChanged.connect(self._refresh_live_list)

        self.engine.state_changed.connect(self._on_state_changed)
        self.engine.source_started.connect(self._on_source_started)
        self.engine.source_error.connect(self._on_source_error)
        self.engine.source_stopped.connect(self._on_source_stopped)
        self.engine.duration_changed.connect(self._on_duration_changed)

    def refresh_sessions(self) -> None:
        current_id = self.session_combo.currentData()
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        for s in self.sessions.all():
            self.session_combo.addItem(s.name, s.id)
        if current_id:
            idx = self.session_combo.findData(current_id)
            if idx >= 0:
                self.session_combo.setCurrentIndex(idx)
        self.session_combo.blockSignals(False)
        self._refresh_live_list()

    def _refresh_live_list(self) -> None:
        self.live_list.clear()
        sid = self.session_combo.currentData()
        session = self.sessions.get(sid) if sid else None
        if not session:
            return
        for src_id in session.source_ids:
            src = self.sources.get(src_id)
            if src:
                item = QListWidgetItem(f"{src.friendly_name}  -  {src.status_text()}")
                item.setData(1000, src_id)
                self.live_list.addItem(item)

    def _current_session(self):
        sid = self.session_combo.currentData()
        return self.sessions.get(sid) if sid else None

    # -- transport, also called directly by hotkeys --

    def start_capture(self) -> None:
        if self.engine.is_active():
            return
        session = self._current_session()
        if not session:
            QMessageBox.information(self, _("No session"), _("Select or create a session first."))
            return
        selected = [self.sources.get(sid) for sid in session.source_ids]
        selected = [s for s in selected if s is not None and s.enabled]
        if not selected:
            QMessageBox.information(self, _("No sources"), _("This session has no enabled sources."))
            return
        self.start_btn.setEnabled(False)
        self.status_label.setText(_("Starting..."))
        self.engine.start(session, selected)

    def toggle_pause_resume(self) -> None:
        if not self.engine.is_active():
            return
        self.pause_btn.setEnabled(False)
        if self.engine.is_paused():
            self.engine.resume()
        else:
            self.engine.pause()

    def stop_capture(self) -> None:
        if not self.engine.is_active():
            return
        self.stop_btn.setEnabled(False)
        self.status_label.setText(_("Stopping..."))
        self.engine.stop()

    # -- engine signal handlers --

    def _on_state_changed(self, state: str) -> None:
        if state == "recording":
            self.status_label.setText(_("Recording"))
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText(_("Pause"))
            self.stop_btn.setEnabled(True)
            self.session_combo.setEnabled(False)
        elif state == "paused":
            self.status_label.setText(_("Paused"))
            self.pause_btn.setText(_("Resume"))
            self.pause_btn.setEnabled(True)
        elif state in ("idle", "stopped"):
            self.status_label.setText(_("Idle"))
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText(_("Pause"))
            self.stop_btn.setEnabled(False)
            self.session_combo.setEnabled(True)

    def _on_source_started(self, source_id: str, output_path: str) -> None:
        self._set_source_status(source_id, _("recording -> {path}").format(path=output_path))

    def _on_source_error(self, source_id: str, message: str) -> None:
        if source_id:
            self._set_source_status(source_id, _("error: {message}").format(message=message))
        else:
            QMessageBox.warning(self, _("Capture error"), message)

    def _on_source_stopped(self, source_id: str, final_path: str) -> None:
        text = _("stopped -> {path}").format(path=final_path) if final_path else _("stopped")
        self._set_source_status(source_id, text)

    def _on_duration_changed(self, source_id: str, elapsed_seconds: float) -> None:
        minutes, seconds = divmod(int(elapsed_seconds), 60)
        self._set_source_status(source_id, _("recording - {m:02d}:{s:02d}").format(m=minutes, s=seconds))

    def _set_source_status(self, source_id: str, text: str) -> None:
        for i in range(self.live_list.count()):
            item = self.live_list.item(i)
            if item.data(1000) == source_id:
                src = self.sources.get(source_id)
                name = src.friendly_name if src else source_id
                item.setText(f"{name}  -  {text}")
                return
