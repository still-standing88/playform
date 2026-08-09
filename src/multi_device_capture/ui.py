"""Multi Device Capture panel - a dock panel like Podcasts/Radio, not a
modal Tools-menu dialog (see gui.managers.dock_manager.DockManager
._create_multi_device_capture_dock / gui.managers.menu_manager.MenuManager
.setup_view_menu's Panels submenu / gui.managers.toolbar_manager
.ToolbarManager.setup_panels_toolbar).

Three tabs, sessions/sources managed as separate pools (a session references
sources rather than owning them):
    Sessions   - session list + source pool, each with add/edit/delete
    Capture    - transport: start/pause/resume/stop + live status
    Settings   - global audio/video defaults, category list + stack

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
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app_config import key_config

from .engine import CaptureEngine
from .registries import SessionRegistry, SourceRegistry
from .settings import multi_device_capture_settings
from .tabs import CaptureTab, SessionsTab, SettingsTab

HOTKEY_SECTION = "Multi Device Capture"


class MultiDeviceCaptureUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.sources = SourceRegistry()
        self.sessions = SessionRegistry()
        self.settings = multi_device_capture_settings
        self.engine = CaptureEngine(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.sessions_tab = SessionsTab(self.sessions, self.sources)
        self.capture_tab = CaptureTab(self.sessions, self.sources, self.engine)
        self.settings_tab = SettingsTab(self.settings)

        self.tabs.addTab(self.sessions_tab, _("Sessions"))
        self.tabs.addTab(self.capture_tab, _("Capture"))
        self.tabs.addTab(self.settings_tab, _("Settings"))
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs)

        self.sessions_tab.sessions_changed.connect(self.capture_tab.refresh_sessions)
        self.sessions_tab.sources_changed.connect(self.capture_tab.refresh_sessions)

        self._shortcuts: list[QShortcut] = []
        self._setup_shortcuts()

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.tabText(index) == _("Capture"):
            self.capture_tab.refresh_sessions()

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

    def _setup_shortcuts(self) -> None:
        for shortcut in self._shortcuts:
            shortcut.setParent(None)
        self._shortcuts = []

        section = key_config.key_config[HOTKEY_SECTION] if HOTKEY_SECTION in key_config.key_config else {}
        mapping = {
            section.get("Start capture", "Ctrl+Alt+R"): self.capture_tab.start_capture,
            section.get("Pause/Resume capture", "Ctrl+Alt+P"): self.capture_tab.toggle_pause_resume,
            section.get("Stop capture", "Ctrl+Alt+S"): self.capture_tab.stop_capture,
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
