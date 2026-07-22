import os
import json

import time
from typing import Optional, Callable, Dict, List, Tuple
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton,
                               QSlider, QLabel, QSizePolicy, QFrame, QSpinBox, QMenu)
from PySide6.QtWidgets import QDialog, QApplication
from PySide6.QtCore import Qt, Signal, QTimer, Slot
from PySide6.QtGui import QIcon, QFont

from gui_controls.toggle_button import ToggleButton
from app_config import prefs
from .dialogs.bookmarks_dialog import BookmarksDialog
from .dialogs.goto_dialog import GoToDialog
from app_constance.misc import video_resolutions, video_speeds, video_aspect_ratios, video_scales
from app_constance.styles import (PLAYER_CONTROLS_STYLE, BUTTON_STYLE, SLIDER_STYLE,
                                   TIME_LABEL_STYLE, TRACK_LABEL_STYLE, TOOLBUTTON_STYLE,
                                   get_repeat_button_active_style)
from utilities.functions import get_app_path
from .core.playback_state_manager import PlaybackStateManager
from utilities.functions import is_youtube_url, is_local_file, open_file_location
from utilities.icon_loader import load_icon, load_pixmap
from .util.url import is_url_supported
from .core.bookmarks_controller import BookmarksController
from .core.repeat_loop_controller import RepeatLoopController
from .core.path_context_menu import build_path_context_menu as _build_path_context_menu
from .core.playback_options_menu import build_more_options_menu


class PlayerControls(QWidget):
    fullscreenToggled = Signal(bool)
    speedChanged = Signal(float)
    aspectRatioChanged = Signal(str)
    scaleChanged = Signal(float)
    playPauseClicked = Signal()
    muteUnmuteClicked = Signal()
    forwardClicked = Signal()
    backwardClicked = Signal()
    previousClicked = Signal()
    nextClicked = Signal()
    repeatClicked = Signal()
    shuffleClicked = Signal()

    seekChanged = Signal(int)
    seekPressed = Signal()
    seekReleased = Signal()
    volumeChanged = Signal(int)
    volumeUpRequested = Signal()
    volumeDownRequested = Signal()

    controlsToggled = Signal(bool)
    timeUpdateRequested = Signal()
    jumpToBeginningRequested = Signal()
    jumpToEndRequested = Signal()
    stopRequested = Signal()
    screenshotRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Qt reparents this widget to whatever layout it's later added to
        # (e.g. PlayerWidget's left_layout reparents it to an anonymous
        # container widget), so self.parent() no longer reliably points at
        # the owning PlayerWidget by the time these delegate methods run -
        # keep our own reference to the constructor-time parent instead.
        self._player_widget = parent
        self.last_position:Optional[int] = None
        self.is_minimized = False
        self.is_playing = False
        self.is_muted = False
        self.is_repeat_on = False
        self.is_shuffle_on = False
        self.is_fullscreen = False

        self._current_file: Optional[str] = None
        self._source_url: Optional[str] = None
        self._bookmarks: Dict[str, List[float]] = {}
        self._last_positions: Dict[str, float] = {}
        self._repeat_loops: Dict[str, List[Tuple[Optional[float], Optional[float]]]] = {}
        self._current_bookmark_index: int = -1
        self._current_loop_index: int = -1
        self._last_loop_trigger_time: float = 0.0
        self._last_known_position: float = 0.0
        self._is_user_seeking: bool = False
        self._data_dir = os.path.join(get_app_path(), "data")
        os.makedirs(self._data_dir, exist_ok=True)

        self._state = PlaybackStateManager(self._data_dir)
        self._bookmarks_ctrl = BookmarksController(self)
        self._repeat_loop_ctrl = RepeatLoopController(self)

        self.setup_ui()
        self.layout_widgets()
        self.connect_signals()
        self.apply_styles()
        self.load_bookmarks()
        self.load_last_positions()
        self.load_repeat_loops()
        self._update_shuffle_text()

        self.time_update_timer = QTimer(self)
        self.time_update_timer.setInterval(700)
        self.time_update_timer.timeout.connect(self.timeUpdateRequested.emit)
        self.time_update_timer.timeout.connect(self._check_current_position)
        self.time_update_timer.start()

    def setup_ui(self):
        self.toggle_controls_btn = ToggleButton(_("Minimize"), self)
        self.toggle_controls_btn.setFixedSize(30, 30)
        self.toggle_controls_btn.setToolTip(_("Minimize/Maximize Controls"))

        # Create media control buttons with icons
        self.previous_btn = QToolButton(self)
        self.previous_btn.setIcon(load_icon("previous.svg"))
        self.previous_btn.setText(_("Previous"))
        self.previous_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.backward_btn = QToolButton(self)
        self.backward_btn.setIcon(load_icon("rewind.svg"))
        self.backward_btn.setText(_("Rewind"))
        self.backward_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.play_pause_btn = QToolButton(self)
        self.play_pause_btn.setIcon(load_icon("play.svg"))
        self.play_pause_btn.setText(_("Play"))
        self.play_pause_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.forward_btn = QToolButton(self)
        self.forward_btn.setIcon(load_icon("forward.svg"))
        self.forward_btn.setText(_("Forward"))
        self.forward_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.next_btn = QToolButton(self)
        self.next_btn.setIcon(load_icon("next.svg"))
        self.next_btn.setText(_("Next"))
        self.next_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.repeat_btn = QToolButton(self)
        self.repeat_btn.setIcon(load_icon("repeat.svg"))
        self.repeat_btn.setText(_("Off"))
        self.repeat_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.shuffle_btn = QToolButton(self)
        self.shuffle_btn.setIcon(load_icon("shuffle.svg"))
        self.shuffle_btn.setText(_("Shuffle"))
        self.shuffle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.bookmarks_btn = QToolButton(self)
        self.bookmarks_btn.setIcon(load_icon("bookmarks.svg"))
        self.bookmarks_btn.setText(_("Bookmarks"))
        self.bookmarks_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.goto_btn = QToolButton(self)
        self.goto_btn.setIcon(load_icon("seek.svg"))
        self.goto_btn.setText(_("Go to"))
        self.goto_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.screenshot_btn = QToolButton(self)
        self.screenshot_btn.setIcon(load_icon("screenshot.svg"))
        self.screenshot_btn.setText(_("Screenshot"))
        self.screenshot_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        button_specs = [
            (self.previous_btn, 120, 40, _("Previous Track")),
            (self.backward_btn, 110, 40, _("Backward")),
            (self.play_pause_btn, 100, 50, _("Play/Pause")),
            (self.forward_btn, 110, 40, _("Forward")),
            (self.next_btn, 100, 40, _("Next Track")),
            (self.repeat_btn, 90, 40, _("Repeat mode")),
            (self.shuffle_btn, 110, 40, _("Shuffle")),
            (self.bookmarks_btn, 130, 40, _("Bookmarks list")),
            (self.goto_btn, 110, 40, _("Go to time")),
            (self.screenshot_btn, 130, 40, _("Take screenshot")),
        ]

        for btn, w, h, tooltip in button_specs:
            btn.setFixedSize(w, h)
            btn.setToolTip(tooltip)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(100)
        self.seek_slider.setSingleStep(prefs.prefs["offset"]["seek"])
        self.seek_slider.setValue(0)
        self.seek_slider.setAccessibleName(_("Seek"))
        self.seek_icon_label = QLabel(self)
        self.seek_icon_label.setPixmap(load_pixmap("seek.svg"))
        self.seek_icon_label.setToolTip(_("Seek"))

        self.mute_btn = QToolButton(self)
        self.mute_btn.setIcon(load_icon("mute_off.svg"))
        self.mute_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.mute_btn.setFixedSize(35, 35)
        self.mute_btn.setToolTip(_("Mute/Unmute"))

        self.more_btn = QPushButton("⋯", self)
        self.more_btn.setFixedSize(35, 35)
        self.more_btn.setToolTip(_("More Options"))

        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setAccessibleName(_("Volume"))
        self.volume_icon_label = QLabel(self)
        self.volume_icon_label.setPixmap(load_pixmap("volume.svg"))
        self.volume_icon_label.setToolTip(_("Volume"))

        sliders = [
            (self.volume_slider, 0, 200, prefs.prefs["offset"]["volume"], 100, 80),
        ]
        for slider, minv, maxv, step, value, fixed_width in sliders:
            slider.setMinimum(minv)
            slider.setMaximum(maxv)
            slider.setSingleStep(step)
            slider.setValue(value)
            slider.setFixedWidth(fixed_width)


        self.time_label = QLabel("00:00 / 00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setMinimumWidth(100)
        self.time_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)

        self.current_track_label = QLabel(_("No media loaded"), self)
        self.current_track_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.current_track_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.current_track_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.current_track_label.customContextMenuRequested.connect(self.show_path_context_menu)

        self.separator1 = QFrame(self)
        self.separator1.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Sunken)

        self.separator2 = QFrame(self)
        self.separator2.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Sunken)

    def layout_widgets(self):

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.track_layout = QHBoxLayout()
        self.track_layout.addWidget(self.current_track_label)
        self.track_layout.addStretch()

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(15)

        self.transport_layout = QHBoxLayout()
        self.transport_layout.setSpacing(5)
        self.transport_layout.addWidget(self.previous_btn)
        self.transport_layout.addWidget(self.backward_btn)
        self.transport_layout.addWidget(self.play_pause_btn)
        self.transport_layout.addWidget(self.forward_btn)
        self.transport_layout.addWidget(self.next_btn)
        self.transport_layout.addWidget(self.repeat_btn)
        self.transport_layout.addWidget(self.shuffle_btn)
        self.transport_layout.addWidget(self.bookmarks_btn)
        self.transport_layout.addWidget(self.goto_btn)
        self.transport_layout.addWidget(self.screenshot_btn)

        self.volume_layout = QHBoxLayout()
        self.volume_layout.setSpacing(5)
        self.volume_layout.addWidget(self.mute_btn)
        self.volume_layout.addWidget(self.volume_icon_label)
        self.volume_layout.addWidget(self.volume_slider)

        self.controls_layout.addLayout(self.transport_layout)
        self.controls_layout.addWidget(self.separator1)
        self.controls_layout.addWidget(self.seek_icon_label)
        self.controls_layout.addWidget(self.seek_slider, 1)
        self.controls_layout.addWidget(self.separator2)
        self.controls_layout.addLayout(self.volume_layout)
        self.controls_layout.addWidget(self.time_label)
        self.controls_layout.addWidget(self.more_btn)
        self.controls_layout.addWidget(self.toggle_controls_btn)


        self.main_layout.addLayout(self.track_layout)
        self.main_layout.addLayout(self.controls_layout)

        self.expandable_widgets = [
            self.previous_btn, self.backward_btn, self.forward_btn,
            self.next_btn, self.repeat_btn, self.separator1,
            self.seek_icon_label, self.seek_slider, self.separator2, self.mute_btn,
            self.volume_icon_label,
            self.volume_slider, self.time_label, self.current_track_label, self.shuffle_btn, self.bookmarks_btn, self.goto_btn, self.screenshot_btn,
            self.more_btn
        ]

    def connect_signals(self):
        self.play_pause_btn.clicked.connect(self.playPauseClicked.emit)
        self.mute_btn.clicked.connect(self.muteUnmuteClicked.emit)
        self.forward_btn.clicked.connect(self.forwardClicked.emit)
        self.backward_btn.clicked.connect(self.backwardClicked.emit)
        self.previous_btn.clicked.connect(self.previousClicked.emit)
        self.next_btn.clicked.connect(self.nextClicked.emit)
        self.repeat_btn.clicked.connect(self.repeatClicked.emit)
        self.shuffle_btn.clicked.connect(self.shuffleClicked.emit)
        self.bookmarks_btn.clicked.connect(self.show_bookmarks_dialog)
        self.goto_btn.clicked.connect(self.show_goto_dialog)
        self.screenshot_btn.clicked.connect(self.screenshotRequested.emit)

        self.seek_slider.valueChanged.connect(self._on_seek_value_changed)
        self.seek_slider.sliderPressed.connect(self.seekPressed.emit)
        self.seek_slider.sliderReleased.connect(self.seekReleased.emit)
        self.volume_slider.valueChanged.connect(self.volumeChanged.emit)

        self.volumeUpRequested.connect(self.volume_up)
        self.volumeDownRequested.connect(self.volume_down)

        self.more_btn.clicked.connect(self.show_more_menu)

        self.toggle_controls_btn.actuated.connect(self.toggle_controls)

    def apply_styles(self):
        self.setStyleSheet(PLAYER_CONTROLS_STYLE)

        # Apply QToolButton style to media control buttons
        for btn in [self.play_pause_btn, self.previous_btn, self.backward_btn,
                   self.forward_btn, self.next_btn, self.repeat_btn, self.shuffle_btn,
                   self.bookmarks_btn, self.screenshot_btn, self.mute_btn]:
            btn.setStyleSheet(TOOLBUTTON_STYLE)

        # Apply QPushButton style to more button
        self.more_btn.setStyleSheet(BUTTON_STYLE)

        self.seek_slider.setStyleSheet(SLIDER_STYLE)
        self.volume_slider.setStyleSheet(SLIDER_STYLE)

        self.time_label.setStyleSheet(TIME_LABEL_STYLE)
        self.current_track_label.setStyleSheet(TRACK_LABEL_STYLE)

    @Slot(bool)
    def toggle_controls(self, minimized):
        self.is_minimized = minimized

        for widget in self.expandable_widgets:
            widget.setVisible(not minimized)

        if minimized:
            self.toggle_controls_btn.setText(_("Maximize"))
            self.toggle_controls_btn.setToolTip(_("Maximize Controls"))
        else:
            self.toggle_controls_btn.setText(_("Minimize"))
            self.toggle_controls_btn.setToolTip(_("Minimize Controls"))

        self.controlsToggled.emit(not minimized)

    @Slot()
    def show_more_menu(self):
        menu = build_more_options_menu(self)
        menu.exec(self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft()))

    @Slot()
    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.fullscreenToggled.emit(self.is_fullscreen)

    def set_fullscreen_state(self, is_fullscreen):
        self.is_fullscreen = is_fullscreen

    def set_play_pause_state(self, is_playing):
        if self.is_playing == is_playing: return
        self.is_playing = is_playing
        if is_playing:
            self.play_pause_btn.setIcon(load_icon("pause.svg"))
            self.play_pause_btn.setText(_("Pause"))
            self.play_pause_btn.setToolTip(_("Pause"))
        else:
            self.play_pause_btn.setIcon(load_icon("play.svg"))
            self.play_pause_btn.setText(_("Play"))
            self.play_pause_btn.setToolTip(_("Play"))

    def set_mute_state(self, is_muted):
        if self.is_muted == is_muted: return
        self.is_muted = is_muted
        if is_muted:
            self.mute_btn.setIcon(load_icon("mute_on.svg"))
            self.mute_btn.setToolTip(_("Unmute"))
        else:
            self.mute_btn.setIcon(load_icon("mute_off.svg"))
            self.mute_btn.setToolTip(_("Mute"))

    def set_repeat_state(self, is_repeat_on):
        if self.is_repeat_on == is_repeat_on: return
        self.is_repeat_on = is_repeat_on
        base_style = BUTTON_STYLE
        if is_repeat_on:
            self.repeat_btn.setStyleSheet(get_repeat_button_active_style(base_style))
        else:
            self.repeat_btn.setStyleSheet(base_style)

    def set_repeat_mode(self, mode: str):
        mode = mode.lower()
        if mode == "off":
            self.set_repeat_state(False)
            self.repeat_btn.setText(_("Repeat: Off"))
            self.repeat_btn.setToolTip(_("Repeat off"))
        elif mode == "all":
            self.set_repeat_state(True)
            self.repeat_btn.setText(_("Repeat: All"))
            self.repeat_btn.setToolTip(_("Repeat all"))
        elif mode == "one":
            self.set_repeat_state(True)
            self.repeat_btn.setText(_("Repeat: One"))
            self.repeat_btn.setToolTip(_("Repeat one"))

    def set_shuffle_state(self, is_shuffle_on):
        if self.is_shuffle_on == is_shuffle_on: return
        self.is_shuffle_on = is_shuffle_on
        base_style = BUTTON_STYLE
        if is_shuffle_on:
            self.shuffle_btn.setStyleSheet(get_repeat_button_active_style(base_style))
        else:
            self.shuffle_btn.setStyleSheet(base_style)
        self._update_shuffle_text()

    def _update_shuffle_text(self):
        if self.is_shuffle_on:
            self.shuffle_btn.setText(_("Shuffle: On"))
            self.shuffle_btn.setToolTip(_("Shuffle on"))
        else:
            self.shuffle_btn.setText(_("Shuffle: Off"))
            self.shuffle_btn.setToolTip(_("Shuffle off"))

    def set_seek_range(self, minimum, maximum):
        self.seek_slider.setRange(minimum, maximum)

    def set_seek_position(self, position):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(position)
        self.seek_slider.blockSignals(False)

    def set_volume(self, volume):
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)

    def set_time_text(self, time_text):
        self.time_label.setText(time_text)

    def set_current_track(self, track_name):
        self.current_track_label.setText(track_name)

    def get_seek_position(self):
        return self.seek_slider.value()

    def get_volume(self):
        return self.volume_slider.value()

    def set_controls_enabled(self, enabled):
        for widget in [self.play_pause_btn, self.previous_btn, self.backward_btn,
                      self.forward_btn, self.next_btn, self.repeat_btn, self.shuffle_btn,
                      self.mute_btn, self.seek_slider, self.volume_slider]:
            widget.setEnabled(enabled)

    @Slot(int)
    def _on_seek_value_changed(self, position):
        self.seekChanged.emit(position)



    def set_current_file(self, file_path: str):
        if self._current_file:
            self.save_last_position()

        self._current_file = file_path
        self._current_bookmark_index = -1
        self._current_loop_index = -1
        self._last_known_position = 0.0

        self._state.bookmarks = self._bookmarks
        self._state.repeat_loops = self._repeat_loops
        self._state.last_positions = self._last_positions

    @Slot()
    def show_bookmarks_dialog(self):
        self._bookmarks_ctrl.show_bookmarks_dialog()

    @Slot()
    def show_goto_dialog(self):
        if not self._current_file:
            return
        mw = getattr(self._player_widget, "_main_window", None) or self.window()
        if hasattr(mw, '_dialog_open') and mw._dialog_open:
            return
        if hasattr(mw, '_dialog_open'):
            mw._dialog_open = True
        dlg = GoToDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            seconds = dlg.get_seconds()
            if seconds is not None:
                self.jump_to_time(seconds)
        if hasattr(mw, '_dialog_open'):
            mw._dialog_open = False

    def jump_to_time(self, seconds: float):
        position = int(seconds)
        self.set_seek_position(position)
        self.seekChanged.emit(position)

    def add_bookmark_at_current_position(self):
        self._bookmarks_ctrl.add_bookmark_at_current_position()

    def jump_to_mark(self, mark_index: int):
        self._bookmarks_ctrl.jump_to_mark(mark_index)

    def jump_to_previous_bookmark(self):
        self._bookmarks_ctrl.jump_to_previous_bookmark()

    def jump_to_next_bookmark(self):
        self._bookmarks_ctrl.jump_to_next_bookmark()

    def jump_to_previous_loop(self):
        self._repeat_loop_ctrl.jump_to_previous_loop()

    def jump_to_next_loop(self):
        self._repeat_loop_ctrl.jump_to_next_loop()

    def delete_current_bookmark(self):
        self._bookmarks_ctrl.delete_current_bookmark()

    @Slot(int)
    def delete_bookmark_at(self, index:int):
        self._bookmarks_ctrl.delete_bookmark_at(index)

    def set_loop_start(self):
        self._repeat_loop_ctrl.set_loop_start()

    def set_loop_end(self):
        self._repeat_loop_ctrl.set_loop_end()

    def set_loop_start_precise(self, position: float):
        self._repeat_loop_ctrl.set_loop_start_precise(position)

    def set_loop_end_precise(self, position: float):
        self._repeat_loop_ctrl.set_loop_end_precise(position)

    def clear_repeat_loop(self):
        self._repeat_loop_ctrl.clear_repeat_loop()

    def clear_all_repeat_loops(self):
        self._repeat_loop_ctrl.clear_all_repeat_loops()

    def get_current_loops(self) -> List[Tuple[Optional[float], Optional[float]]]:
        return self._repeat_loop_ctrl.get_current_loops()

    def update_loop_by_index(self, index:int, start:float, end:float):
        return self._repeat_loop_ctrl.update_loop_by_index(index, start, end)

    def delete_loop_by_index(self, index:int):
        return self._repeat_loop_ctrl.delete_loop_by_index(index)

    def add_bookmark_at_position(self, position:float):
        return self._bookmarks_ctrl.add_bookmark_at_position(position)

    def update_bookmark_at_index(self, index:int, position:float):
        return self._bookmarks_ctrl.update_bookmark_at_index(index, position)

    def should_loop_playback(self, current_position: float) -> Optional[float]:
        return self._repeat_loop_ctrl.should_loop_playback(current_position)

    def _is_position_in_existing_loop(self, position: float) -> bool:
        return self._repeat_loop_ctrl.is_position_in_existing_loop(position)

    def _would_loop_intersect(self, new_start: float, new_end: float, exclude_index: int = -1) -> bool:
        return self._repeat_loop_ctrl.would_loop_intersect(new_start, new_end, exclude_index=exclude_index)

    def get_bookmarks(self) -> List[float]:
        return self._bookmarks_ctrl.get_bookmarks()

    @Slot()
    def clear_bookmarks(self):
        self._bookmarks_ctrl.clear_bookmarks()

    def save_bookmarks(self):
        self._bookmarks_ctrl.save_bookmarks()

    def load_bookmarks(self):
        self._bookmarks_ctrl.load_bookmarks()

    def save_repeat_loops(self):
        self._repeat_loop_ctrl.save_repeat_loops()

    def load_repeat_loops(self):
        self._repeat_loop_ctrl.load_repeat_loops()

    def save_last_position(self):
        if not self._current_file:
            return

        current_pos = self.get_seek_position()
        self._last_positions[self._current_file] = current_pos

        self._state.last_positions = self._last_positions
        self._state.save_last_positions()

    def load_last_positions(self):
        self._state.load_last_positions()
        self._last_positions = self._state.last_positions

    def load_last_position(self):
        self._state.last_positions = self._last_positions
        last_pos = self._state.get_last_position(self._current_file)
        self._last_positions = self._state.last_positions
        if last_pos is not None:
            self.last_position = int(last_pos)

    @Slot()
    def volume_up(self):
        current_volume = self.get_volume()
        volume_offset = prefs.prefs["offset"]["volume"]
        new_volume = min(200, current_volume + volume_offset)
        self.set_volume(new_volume)
        self.volumeChanged.emit(new_volume)

    @Slot()
    def volume_down(self):
        current_volume = self.get_volume()
        volume_offset = prefs.prefs["offset"]["volume"]
        new_volume = max(0, current_volume - volume_offset)
        self.set_volume(new_volume)
        self.volumeChanged.emit(new_volume)

    def check_loop_position(self, current_position: float):
        self._repeat_loop_ctrl.check_loop_position(current_position)

    @Slot()
    def _check_current_position(self):
        self._repeat_loop_ctrl.check_current_position()

    def show_path_context_menu(self, position):
        """Show dynamic context menu for current file/URL"""
        if not self._current_file:
            return
        menu = self.build_path_context_menu(self)
        menu.exec(self.current_track_label.mapToGlobal(position))

    def build_path_context_menu(self, parent_widget) -> QMenu:
        """Build the Copy Path / Open in Explorer / Show YouTube Info menu shared
        by PlayerControls' own track-label context menu and PlayerWidget's."""
        return _build_path_context_menu(self, parent_widget)
