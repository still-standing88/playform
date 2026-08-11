"""Multi Device Capture tool - a modal Tools-menu dialog like Batch
Converter/Tag Editor/Speech Converter, opened via
gui.managers.tool_window_manager.ToolWindowManager.open_multi_device_capture
(wrapped in gui.dialogs.tool_dialog.ToolDialog, same as every other tool -
see that class for the Hide/Close chrome and the "still active, are you
sure" close gate).

One consolidated view rather than three tabs: a QStackedWidget swaps
between views/configure_view.ConfigureView (sessions + session-scoped
sources, Add source / Settings / Start capture) and
views/capture_view.CaptureView (live per-source status + Pause/Resume/
Cancel), so the session/source configuration UI isn't sitting there
editable mid-recording - clicking Start capture hides it entirely rather
than just disabling it.

Not a dock panel: it used to be one (Toggle/Focus multi device capture
global hotkeys, a Panels-toolbar entry, a FloatableDockWidget), which meant
the engine could keep recording invisibly behind a hidden dock - moved back
to a tool because that "hidden but still active" state didn't fit a
capture session that has a hard Start/Stop the way Podcasts/Radio's
background downloads don't. As a tool, the dialog's own active-tool gate
(ToolDialog.is_tool_active(), via the `thread` shim below) is what stands
between the user and losing an in-progress recording; there is no dock/
Panels-menu wiring to remove things from if this changes again.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from app_config import key_config
from media_core.av_capture.capabilities import CaptureCapabilities
from tools.ffmpeg_handler import FFmpegHandler

from .dialogs import SettingsDialog
from .engine import CaptureEngine
from .registries import SessionRegistry, SourceRegistry
from .settings import multi_device_capture_settings
from .views import CaptureView, ConfigureView

HOTKEY_SECTION = "Multi Device Capture"


class _EngineActivityThread(QThread):
    """Never actually started - purely a vessel ToolDialog.is_tool_active()
    can query via isRunning(), matching the `tool_widget.thread` convention
    every other tool follows (its own background work genuinely is a
    QThread, e.g. tools.ffmpeg.batch_converter.job.ConvertJob). This
    engine's real work runs on CaptureEngine's own ThreadPoolExecutor
    instead (see engine.py's docstring for why it isn't a QThread) - this
    shim exists only so the Tools-menu's generic close-gate can see it."""

    def __init__(self, engine: CaptureEngine, parent=None):
        super().__init__(parent)
        self._engine = engine

    def isRunning(self) -> bool:
        return self._engine.is_active()


class MultiDeviceCaptureUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.sources = SourceRegistry()
        self.sessions = SessionRegistry()
        self.settings = multi_device_capture_settings
        ffmpeg_path, _ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        self.capabilities = CaptureCapabilities(ffmpeg_executable=ffmpeg_path)
        self.engine = CaptureEngine(capabilities=self.capabilities, settings=self.settings, parent=self)
        self.thread = _EngineActivityThread(self.engine, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.configure_view = ConfigureView(self.sessions, self.sources, self.capabilities, self.settings)
        self.capture_view = CaptureView(self.sources)
        self.stack.addWidget(self.configure_view)
        self.stack.addWidget(self.capture_view)
        layout.addWidget(self.stack)

        self.configure_view.start_capture_requested.connect(self._start_capture)
        self.configure_view.settings_requested.connect(self._open_settings)
        self.capture_view.pause_requested.connect(self.engine.pause)
        self.capture_view.resume_requested.connect(self.engine.resume)
        self.capture_view.stop_requested.connect(self.engine.stop)

        self.engine.state_changed.connect(self._on_state_changed)
        self.engine.state_changed.connect(self.capture_view.on_state_changed)
        self.engine.source_started.connect(self.capture_view.on_source_started)
        self.engine.source_error.connect(self._on_source_error)
        self.engine.source_stopped.connect(self.capture_view.on_source_stopped)
        self.engine.duration_changed.connect(self.capture_view.on_duration_changed)

        self._shortcuts: list[QShortcut] = []
        self._setup_shortcuts()

    # -- start/stop handoff between the two views ------------------------

    def _start_capture(self, session, sources) -> None:
        self.capture_view.begin(session, sources)
        self.stack.setCurrentWidget(self.capture_view)
        self.engine.start(session, sources)

    def _on_state_changed(self, state: str) -> None:
        if state in ("idle", "stopped"):
            self.stack.setCurrentWidget(self.configure_view)

    def _on_source_error(self, source_id: str, message: str) -> None:
        self.capture_view.on_source_error(source_id, message)
        if not source_id:
            QMessageBox.warning(self, _("Capture error"), message)

    def _open_settings(self) -> None:
        SettingsDialog(self.settings, parent=self).exec()

    # -- hotkeys: Start / Pause-Resume / Stop capture --------------------
    #
    # Local (widget-scoped) shortcuts, same pattern as EXPLORER/explorer_widget's
    # set_shortcuts(): read from app_config.key_config so they're user-remappable
    # through the existing Hotkeys dialog (which enumerates key_config sections
    # generically), but only fire while this dialog has focus - capture transport
    # is deliberately not wired into the global `keyboard`-hook hotkeys, since a
    # background Start/Stop hotkey for an armed recorder is an easy way to start
    # capturing devices without realizing it. These are the only
    # multi-device-capture-specific hotkeys left; there is no global toggle/
    # focus hotkey for the tool itself (it opens from the Tools menu like any
    # other tool, not a dock).

    def start_capture(self) -> None:
        if self.engine.is_active():
            return
        self.configure_view._on_start_clicked()

    def toggle_pause_resume(self) -> None:
        if not self.engine.is_active():
            return
        if self.engine.is_paused():
            self.engine.resume()
        else:
            self.engine.pause()

    def stop_capture(self) -> None:
        if not self.engine.is_active():
            return
        self.engine.stop()

    def _setup_shortcuts(self) -> None:
        for shortcut in self._shortcuts:
            shortcut.setParent(None)
        self._shortcuts = []

        section = key_config.key_config[HOTKEY_SECTION] if HOTKEY_SECTION in key_config.key_config else {}
        mapping = {
            section.get("Start capture", "Ctrl+Alt+R"): self.start_capture,
            section.get("Pause/Resume capture", "Ctrl+Alt+P"): self.toggle_pause_resume,
            section.get("Stop capture", "Ctrl+Alt+S"): self.stop_capture,
        }
        for key_sequence, callback in mapping.items():
            if not key_sequence:
                continue
            shortcut = QShortcut(QKeySequence(key_sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def reset_shortcuts(self) -> None:
        self._setup_shortcuts()
