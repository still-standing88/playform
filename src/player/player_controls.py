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
from gui_controls.flow_layout import FlowLayout, FlowContainer
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
    rotateChanged = Signal(int)
    flipHorizontalToggled = Signal(bool)
    flipVerticalToggled = Signal(bool)
    panChanged = Signal(float, float)
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

    timeUpdateRequested = Signal()
    jumpToBeginningRequested = Signal()
    jumpToEndRequested = Signal()
    stopRequested = Signal()
    screenshotRequested = Signal()
    reverseToggled = Signal(bool)

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
        self.is_reverse_available = False
        self.is_reverse_active = False
        self.is_video_available = False
        self.video_rotate = 0
        self.is_flip_horizontal = False
        self.is_flip_vertical = False
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.current_speed = 1.0
        # Keeps current_speed accurate no matter which caller emitted
        # speedChanged (menu click or an f/d hotkey step) so the "More
        # Options" menu's speed group can show the real checked entry
        # instead of always defaulting to 1.0x.
        self.speedChanged.connect(self._track_current_speed)

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
        self.toggle_controls_btn.setFixedHeight(30)
        self.toggle_controls_btn.setToolTip(_("Minimize/Maximize Controls"))

        # Create media control buttons with icons
        self.previous_btn = QToolButton(self)
        self.previous_btn.setIcon(load_icon("previous.svg"))

        self.backward_btn = QToolButton(self)
        self.backward_btn.setIcon(load_icon("rewind.svg"))

        self.play_pause_btn = QToolButton(self)
        self.play_pause_btn.setIcon(load_icon("play.svg"))

        self.forward_btn = QToolButton(self)
        self.forward_btn.setIcon(load_icon("forward.svg"))

        self.next_btn = QToolButton(self)
        self.next_btn.setIcon(load_icon("next.svg"))

        self.repeat_btn = QToolButton(self)
        self.repeat_btn.setIcon(load_icon("repeat.svg"))

        self.shuffle_btn = QToolButton(self)
        self.shuffle_btn.setIcon(load_icon("shuffle.svg"))

        self.bookmarks_btn = QToolButton(self)
        self.bookmarks_btn.setIcon(load_icon("bookmarks.svg"))

        self.goto_btn = QToolButton(self)
        self.goto_btn.setIcon(load_icon("seek.svg"))

        self.screenshot_btn = QToolButton(self)
        self.screenshot_btn.setIcon(load_icon("screenshot.svg"))

        # Icon-only at a predictable, uniform size, not the previous
        # per-button icon+text at 90-130px wide each - those ten buttons
        # alone summed to ~1110px, and the whole controls row to ~1660px,
        # far more than a typical window's width, forcing horizontal
        # clipping instead of ever wrapping. The state each button's text
        # used to show (Play/Pause, Repeat: Off/All/One, Shuffle: On/Off)
        # is already duplicated into its tooltip elsewhere in this file, so
        # nothing discoverable is lost by dropping the inline label.
        button_specs = [
            (self.previous_btn, _("Previous Track")),
            (self.backward_btn, _("Backward")),
            (self.play_pause_btn, _("Play/Pause")),
            (self.forward_btn, _("Forward")),
            (self.next_btn, _("Next Track")),
            (self.repeat_btn, _("Repeat mode")),
            (self.shuffle_btn, _("Shuffle")),
            (self.bookmarks_btn, _("Bookmarks list")),
            (self.goto_btn, _("Go to time")),
            (self.screenshot_btn, _("Take screenshot")),
        ]

        for btn, tooltip in button_specs:
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.setFixedSize(36, 36)
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
            (self.volume_slider, 0, 300, prefs.prefs["offset"]["volume"], prefs.prefs.get("player_volume", 120), 80),
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

        # The seek bar stays its own always-full-width row - unlike the
        # buttons below, it needs to stay wide to be usable, not wrap.
        self.seek_layout = QHBoxLayout()
        self.seek_layout.setSpacing(5)
        self.seek_layout.addWidget(self.seek_icon_label)
        self.seek_layout.addWidget(self.seek_slider, 1)

        # Everything else used to be one fixed QHBoxLayout row needing
        # ~1660px (ten 90-130px-wide buttons plus separators, volume, time
        # label) - now a FlowLayout wraps it across as many rows as the
        # actual window width needs, the same fix already applied to the
        # Panels toolbar.
        self.buttons_container = FlowContainer()
        self.buttons_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.buttons_flow = FlowLayout(self.buttons_container, margin=0, h_spacing=8, v_spacing=6)
        for widget in (self.toggle_controls_btn,
                       self.previous_btn, self.backward_btn, self.play_pause_btn,
                       self.forward_btn, self.next_btn, self.separator1,
                       self.repeat_btn, self.shuffle_btn, self.bookmarks_btn,
                       self.goto_btn, self.screenshot_btn, self.separator2,
                       self.mute_btn, self.volume_icon_label, self.volume_slider,
                       self.time_label, self.more_btn):
            self.buttons_flow.addWidget(widget)

        self.main_layout.addLayout(self.track_layout)
        self.main_layout.addLayout(self.seek_layout)
        self.main_layout.addWidget(self.buttons_container)

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

    def _resync_buttons_container_height(self):
        # Nested heightForWidth widgets inside a plain QVBoxLayout are a
        # known Qt limitation - the outer layout doesn't reliably re-query
        # a child's heightForWidth() when the available width changes or
        # when a managed widget's visibility changes, the way single-level
        # layouts do. Verified live: resizing this widget across several
        # widths, and toggling Minimize Controls (hiding most of its
        # children), left buttons_container's actual rendered height stuck
        # at an early wrong value throughout - updateGeometry() alone
        # (the normal way to ask a layout to re-check) never resolved it,
        # even after pumping the event loop. Computing and applying the
        # needed height directly sidesteps relying on that negotiation.
        width = self.buttons_container.width()
        if width > 0:
            self.buttons_container.setFixedHeight(self.buttons_flow.heightForWidth(width))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resync_buttons_container_height()

    @Slot(bool)
    def toggle_controls(self, minimized):
        self.is_minimized = minimized

        for widget in self.expandable_widgets:
            widget.setVisible(not minimized)
        self._resync_buttons_container_height()

        if minimized:
            self.toggle_controls_btn.setText(_("Maximize"))
            self.toggle_controls_btn.setToolTip(_("Maximize Controls"))
        else:
            self.toggle_controls_btn.setText(_("Minimize"))
            self.toggle_controls_btn.setToolTip(_("Minimize Controls"))

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

    def _on_reverse_action_toggled(self, checked: bool):
        self.is_reverse_active = checked
        self.reverseToggled.emit(checked)

    def set_reverse_available(self, available: bool):
        self.is_reverse_available = available
        if not available and self.is_reverse_active:
            self.is_reverse_active = False
            self.reverseToggled.emit(False)

    def sync_reverse_state(self, active: bool):
        """Reflects a reverse-playback change that happened without the
        user clicking the menu item (e.g. the monitor thread auto-stopping
        it after running off the start of the track), without re-emitting
        reverseToggled and looping back into the player."""
        self.is_reverse_active = active

    def set_video_available(self, available: bool):
        self.is_video_available = available
        # Only ever force-resets on the True->False edge (switching to an
        # audio-only track) -- this is called every poll tick while a video
        # track keeps playing, so resetting on the True branch too would
        # stomp the user's rotate/flip choice on the very next tick.
        if not available:
            if self.video_rotate != 0:
                self.video_rotate = 0
                self.rotateChanged.emit(0)
            if self.is_flip_horizontal:
                self.is_flip_horizontal = False
                self.flipHorizontalToggled.emit(False)
            if self.is_flip_vertical:
                self.is_flip_vertical = False
                self.flipVerticalToggled.emit(False)
            if self.pan_x != 0.0 or self.pan_y != 0.0:
                self.pan_x = 0.0
                self.pan_y = 0.0
                self.panChanged.emit(0.0, 0.0)

    def _on_rotate_action_triggered(self, degrees: int):
        self.video_rotate = degrees
        self.rotateChanged.emit(degrees)

    def _on_flip_horizontal_action_toggled(self, checked: bool):
        self.is_flip_horizontal = checked
        self.flipHorizontalToggled.emit(checked)

    def _on_flip_vertical_action_toggled(self, checked: bool):
        self.is_flip_vertical = checked
        self.flipVerticalToggled.emit(checked)

    PAN_STEP = 0.05

    def pan_by(self, dx: float, dy: float):
        self.pan_x = max(-1.0, min(1.0, self.pan_x + dx))
        self.pan_y = max(-1.0, min(1.0, self.pan_y + dy))
        self.panChanged.emit(self.pan_x, self.pan_y)

    def _track_current_speed(self, speed: float):
        self.current_speed = speed

    def step_speed(self, direction: int):
        try:
            idx = video_speeds.index(self.current_speed)
        except ValueError:
            idx = min(range(len(video_speeds)), key=lambda i: abs(video_speeds[i] - self.current_speed))
        new_idx = max(0, min(len(video_speeds) - 1, idx + direction))
        self.speedChanged.emit(video_speeds[new_idx])

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
        # QSlider.setRange() silently clamps an out-of-range current value
        # into the new range and fires valueChanged when it does -- e.g.
        # the slider still holding a previous, longer track's position/
        # duration when a new, shorter track's range is set narrows it down
        # to the new maximum. Unlike set_seek_position() below, this wasn't
        # guarded, so that clamp was treated as a real user seek and sent
        # straight to mpv, landing the new track right at its own ending
        # (confirmed via a captured call stack: set_seek_range ->
        # QSlider's own valueChanged -> _on_seek_value_changed ->
        # seekChanged -> _on_seek_changed -> instance.set_position()).
        # Self-perpetuating once triggered once, since it leaves the
        # slider back near *this* track's own duration for the next one.
        self.seek_slider.blockSignals(True)
        self.seek_slider.setRange(minimum, maximum)
        self.seek_slider.blockSignals(False)

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
                      self.mute_btn, self.seek_slider, self.volume_slider, self.goto_btn,
                      self.bookmarks_btn, self.screenshot_btn]:
            widget.setEnabled(enabled)

    @Slot(int)
    def _on_seek_value_changed(self, position):
        self.seekChanged.emit(position)



    def set_current_file(self, file_path: str):
        # load_file()/load_playlist() both call this once directly (with the
        # requested path) and again moments later via _update_current_file()
        # (with the now-loaded instance's file_path, normally the same
        # file) -- guarding on "was a file already open" instead of "is this
        # actually a different file" made the second call see its own
        # first call as a file switch and immediately save_last_position()
        # for the file that was just opened, using whatever the seek slider
        # still showed (0, since nothing had played yet) -- clobbering its
        # real saved resume position on disk before mpv had even loaded it.
        if self._current_file and self._current_file != file_path:
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
        self.last_position = int(last_pos) if last_pos is not None else None

    @Slot()
    def volume_up(self):
        current_volume = self.get_volume()
        volume_offset = prefs.prefs["offset"]["volume"]
        new_volume = min(300, current_volume + volume_offset)
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
