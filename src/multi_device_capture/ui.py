"""Multi Device Capture panel - a dock panel like Podcasts/Radio, not a
modal Tools-menu dialog (see gui.managers.dock_manager.DockManager
._create_multi_device_capture_dock / gui.managers.menu_manager.MenuManager
.setup_view_menu's Panels submenu / gui.managers.toolbar_manager
.ToolbarManager.setup_panels_toolbar).

One consolidated view rather than three tabs: a QStackedWidget swaps
between views/configure_view.ConfigureView (sessions + session-scoped
sources, Add source / Settings / Start capture) and
views/capture_view.CaptureView (live per-source status + Pause/Resume/
Cancel), so the session/source configuration UI isn't sitting there
editable mid-recording - clicking Start capture hides it entirely rather
than just disabling it.

Lazily created on first show, same as Podcasts/Radio - closing the dock just
hides it (FloatableDockWidget re-docks-and-hides rather than destroying), it
doesn't tear this widget down. An in-progress capture surviving a hidden
panel is intentional (mirrors a podcast download continuing off-screen); the
engine only gets stopped on real app shutdown, via MainWindow.closeEvent /
has_active_tools() (same "still active, are you sure" gate the ToolDialog
tools use).
"""
from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
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


class MultiDeviceCaptureUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.sources = SourceRegistry()
        self.sessions = SessionRegistry()
        self.settings = multi_device_capture_settings
        ffmpeg_path, _ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        self.capabilities = CaptureCapabilities(ffmpeg_executable=ffmpeg_path)
        self.engine = CaptureEngine(capabilities=self.capabilities, settings=self.settings, parent=self)

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
    # generically), but only fire while this panel has focus - capture transport
    # is deliberately not wired into the global `keyboard`-hook hotkeys, since a
    # background Start/Stop hotkey for an armed recorder is an easy way to start
    # capturing devices without realizing it. (Toggling/focusing the panel itself
    # is a *global*-scope hotkey though - see "Toggle/Focus multi device capture"
    # in the "Main interface" key_config section, wired in
    # gui.managers.shortcuts_manager, same as Podcasts/Radio.)

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
