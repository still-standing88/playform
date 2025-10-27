import os
import json

import time
from typing import Optional, Callable, Dict, List, Tuple
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                               QSlider, QLabel, QSizePolicy, QFrame, QSpinBox, QMenu)
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QFont

from gui_controls.toggle_button import ToggleButton
from app_config import prefs
from .bookmarks_dialog import BookmarksDialog
from app_constance.misc import video_resolutions, video_speeds, video_aspect_ratios, video_scales
from utilities.functions import get_app_path


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
        self.last_position:Optional[int] = None
        self.is_minimized = False
        self.is_playing = False
        self.is_muted = False
        self.is_repeat_on = False
        self.is_shuffle_on = False
        self.is_fullscreen = False
        
        self._current_file: Optional[str] = None
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
        
        #self._shortcut_manager: ShortcutManager = ShortcutManager(self)
        
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
        self.toggle_controls_btn = ToggleButton("Minimize", self)
        self.toggle_controls_btn.setFixedSize(30, 30)
        self.toggle_controls_btn.setToolTip("Minimize/Maximize Controls")
        
        self.previous_btn = QPushButton("⏮Previous", self)
        self.backward_btn = QPushButton("⏪Rewind", self)
        self.play_pause_btn = QPushButton("▶", self)
        self.forward_btn = QPushButton("⏩Forward", self)
        self.next_btn = QPushButton("⏭Next", self)
        self.repeat_btn = QPushButton("🔁Off", self)
        self.shuffle_btn = QPushButton("🔀Shuffle", self)
        self.bookmarks_btn = QPushButton("🔖", self)
        self.bookmarks_btn.setToolTip("Bookmarks list")
        self.screenshot_btn = QPushButton("📷", self)
        self.screenshot_btn.setToolTip("Take screenshot")
        
        for btn in [self.previous_btn, self.backward_btn, self.play_pause_btn,
                   self.forward_btn, self.next_btn, self.repeat_btn, self.shuffle_btn, self.bookmarks_btn, self.screenshot_btn]:
            btn.setFixedSize(40, 40)
            
        self.play_pause_btn.setFixedSize(50, 50)
        
        self.previous_btn.setToolTip("Previous Track")
        self.backward_btn.setToolTip("Backward")
        self.play_pause_btn.setToolTip("Play/Pause")
        self.forward_btn.setToolTip("Forward")
        self.next_btn.setToolTip("Next Track")
        self.repeat_btn.setToolTip("Repeat mode")
        self.shuffle_btn.setToolTip("Shuffle")
        
        self.seek_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(100)
        self.seek_slider.setSingleStep(prefs.prefs["offset"]["seek"])
        self.seek_slider.setValue(0)
        self.seek_slider.setAccessibleName("Seek")

        
        self.mute_btn = QPushButton("🔊", self)
        self.mute_btn.setFixedSize(35, 35)
        self.mute_btn.setToolTip("Mute/Unmute")
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setSingleStep(prefs.prefs["offset"]["volume"])
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setAccessibleName("Volume")

        
        self.time_label = QLabel("00:00 / 00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setMinimumWidth(100)
        self.time_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        
        self.more_btn = QPushButton("⋯", self)
        self.more_btn.setFixedSize(35, 35)
        self.more_btn.setToolTip("More Options")


        
        self.current_track_label = QLabel("No media loaded", self)
        self.current_track_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.current_track_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        #self.current_track_label.setAccessibleName("Currently Playing")


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
        self.transport_layout.addWidget(self.screenshot_btn)
        
        self.volume_layout = QHBoxLayout()
        self.volume_layout.setSpacing(5)
        self.volume_layout.addWidget(self.mute_btn)
        self.volume_layout.addWidget(self.volume_slider)
        
        self.controls_layout.addLayout(self.transport_layout)
        self.controls_layout.addWidget(self.separator1)
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
            self.seek_slider, self.separator2, self.mute_btn,
            self.volume_slider, self.time_label, self.current_track_label, self.shuffle_btn, self.bookmarks_btn, self.screenshot_btn, 
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
        self.setStyleSheet("background-color: transparent;")
        button_style = """
            QPushButton {
                background-color: #3498db; border: none; border-radius: 20px;
                color: white; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #21618c; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """
        
        slider_style = """
            QSlider::groove:horizontal { border: 1px solid #bbb; background: white; height: 8px; border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #3498db; border: 1px solid #777; height: 8px; border-radius: 4px; }
            QSlider::add-page:horizontal { background: #fff; border: 1px solid #777; height: 8px; border-radius: 4px; }
            QSlider::handle:horizontal { background: #3498db; border: 2px solid #777; width: 18px; margin: -2px 0; border-radius: 9px; }
            QSlider::handle:horizontal:hover { background: #2980b9; }
        """
        
        for btn in [self.play_pause_btn, self.previous_btn, self.backward_btn,
                   self.forward_btn, self.next_btn, self.repeat_btn, self.mute_btn, self.more_btn, self.shuffle_btn, self.bookmarks_btn, self.screenshot_btn]:
            btn.setStyleSheet(button_style)
            
        self.seek_slider.setStyleSheet(slider_style)
        self.volume_slider.setStyleSheet(slider_style)
        
        self.time_label.setStyleSheet("QLabel { color: #2c3e50; font-weight: bold; }")
        self.current_track_label.setStyleSheet("QLabel { color: #34495e; font-size: 14px; }")
        
    def toggle_controls(self, minimized):
        self.is_minimized = minimized
        
        for widget in self.expandable_widgets:
            widget.setVisible(not minimized)
            
        if minimized:
            self.toggle_controls_btn.setText("Maximize")
            self.toggle_controls_btn.setToolTip("Maximize Controls")
        else:
            self.toggle_controls_btn.setText("Minimize")
            self.toggle_controls_btn.setToolTip("Minimize Controls")
            
        self.controlsToggled.emit(not minimized)
    
    def show_more_menu(self):
        menu = QMenu(self)
        
        speed_menu = menu.addMenu("⚡ Speed")
        from PySide6.QtGui import QActionGroup
        speed_group = QActionGroup(speed_menu)
        speed_group.setExclusive(True)
        for speed in video_speeds:
            speed_text = f"{speed}x"
            action = speed_menu.addAction(speed_text)
            action.setCheckable(True)
            if float(speed) == 1.0:
                action.setChecked(True)
            action.triggered.connect(self._create_speed_handler(speed))
            speed_group.addAction(action)

        aspect_menu = menu.addMenu("Aspect Ratio")
        for ratio in video_aspect_ratios:
            a = aspect_menu.addAction(ratio)
            a.triggered.connect(lambda r=ratio: self.aspectRatioChanged.emit(r))

        scale_menu = menu.addMenu("Scale")
        for s in video_scales:
            a = scale_menu.addAction(s)
            a.triggered.connect(lambda v=s: self.scaleChanged.emit(float(v)))
        
        fullscreen_action = menu.addAction("⛶ Fullscreen")
        fullscreen_action_state = lambda: fullscreen_action.setChecked(self.is_fullscreen)
        fullscreen_action.setCheckable(True)
        fullscreen_action.setChecked(self.is_fullscreen)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        self.fullscreenToggled.connect(fullscreen_action_state)
        
        
        menu.exec(self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft()))
    
    def _create_speed_handler(self, speed):
        return lambda: self.speedChanged.emit(speed)
    
    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.fullscreenToggled.emit(self.is_fullscreen)
    
    def set_fullscreen_state(self, is_fullscreen):
        self.is_fullscreen = is_fullscreen
        
    def set_play_pause_state(self, is_playing):
        if self.is_playing == is_playing: return
        self.is_playing = is_playing
        if is_playing:
            self.play_pause_btn.setText("⏸")
            self.play_pause_btn.setToolTip("Pause")
        else:
            self.play_pause_btn.setText("▶")
            self.play_pause_btn.setToolTip("Play")
            
    def set_mute_state(self, is_muted):
        if self.is_muted == is_muted: return
        self.is_muted = is_muted
        if is_muted:
            self.mute_btn.setText("🔇")
            self.mute_btn.setToolTip("Unmute")
        else:
            self.mute_btn.setText("🔊")
            self.mute_btn.setToolTip("Mute")
            
    def set_repeat_state(self, is_repeat_on):
        if self.is_repeat_on == is_repeat_on: return
        self.is_repeat_on = is_repeat_on
        base_style = self.play_pause_btn.styleSheet()
        if is_repeat_on:
            self.repeat_btn.setStyleSheet(base_style + "QPushButton { background-color: #e74c3c; }")
        else:
            self.repeat_btn.setStyleSheet(base_style)

    def set_repeat_mode(self, mode: str):
        mode = mode.lower()
        if mode == "off":
            self.set_repeat_state(False)
            self.repeat_btn.setText("🔁Off")
            self.repeat_btn.setToolTip("Repeat off")
        elif mode == "all":
            self.set_repeat_state(True)
            self.repeat_btn.setText("🔁All")
            self.repeat_btn.setToolTip("Repeat all")
        elif mode == "one":
            self.set_repeat_state(True)
            self.repeat_btn.setText("🔁One")
            self.repeat_btn.setToolTip("Repeat one")
            
    def set_shuffle_state(self, is_shuffle_on):
        if self.is_shuffle_on == is_shuffle_on: return
        self.is_shuffle_on = is_shuffle_on
        base_style = self.play_pause_btn.styleSheet()
        if is_shuffle_on:
            self.shuffle_btn.setStyleSheet(base_style + "QPushButton { background-color: #e74c3c; }")
        else:
            self.shuffle_btn.setStyleSheet(base_style)
        self._update_shuffle_text()

    def _update_shuffle_text(self):
        if self.is_shuffle_on:
            self.shuffle_btn.setText("🔀On")
            self.shuffle_btn.setToolTip("Shuffle on")
        else:
            self.shuffle_btn.setText("🔀Off")
            self.shuffle_btn.setToolTip("Shuffle off")
            
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
    
    def _on_seek_value_changed(self, position):
        self.seekChanged.emit(position)
    

    
    def set_current_file(self, file_path: str):
        if self._current_file:
            self.save_last_position()
        
        self._current_file = file_path
        self._current_bookmark_index = -1
        self._current_loop_index = -1
        self._last_known_position = 0.0
        
        if file_path not in self._bookmarks:
            self._current_bookmark_index = -1
    
    def show_bookmarks_dialog(self):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        bookmarks = self._bookmarks[self._current_file]
        if not bookmarks:
            return
        self._bookmarks_dialog = BookmarksDialog(bookmarks, self)
        dlg = self._bookmarks_dialog
        dlg.deleteRequested.connect(self.delete_bookmark_at)
        dlg.clearAllRequested.connect(self.clear_bookmarks)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_index = dlg.get_selected_bookmark_index()
            if selected_index is not None:
                self.jump_to_mark(selected_index)
        self._bookmarks_dialog = None
    
    def add_bookmark_at_current_position(self):
        if not self._current_file:
            return
        
        current_pos = self.get_seek_position()
        
        if self._current_file not in self._bookmarks:
            self._bookmarks[self._current_file] = []
        
        self._bookmarks[self._current_file].append(current_pos)
        self._bookmarks[self._current_file].sort()
        self.save_bookmarks()
        if hasattr(self, '_bookmarks_dialog') and isinstance(self._bookmarks_dialog, BookmarksDialog) and self._bookmarks_dialog is not None:
            self._refresh_bookmarks_dialog()
    
    def jump_to_mark(self, mark_index: int):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        
        bookmarks = self._bookmarks[self._current_file]
        if mark_index < len(bookmarks):
            position = bookmarks[mark_index]
            self._current_bookmark_index = mark_index
            self.set_seek_position(int(position))
            self.seekChanged.emit(int(position))
    
    def jump_to_previous_bookmark(self):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        
        bookmarks = self._bookmarks[self._current_file]
        if not bookmarks:
            return
        
        if self._current_bookmark_index <= 0:
            self._current_bookmark_index = len(bookmarks) - 1
        else:
            self._current_bookmark_index -= 1
        
        position = bookmarks[self._current_bookmark_index]
        self.set_seek_position(int(position))
        self.seekChanged.emit(int(position))
    
    def jump_to_next_bookmark(self):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        
        bookmarks = self._bookmarks[self._current_file]
        if not bookmarks:
            return
        
        if self._current_bookmark_index >= len(bookmarks) - 1 or self._current_bookmark_index < 0:
            self._current_bookmark_index = 0
        else:
            self._current_bookmark_index += 1
        
        position = bookmarks[self._current_bookmark_index]
        self.set_seek_position(int(position))
        self.seekChanged.emit(int(position))
    
    def jump_to_previous_loop(self):
        if not self._current_file or self._current_file not in self._repeat_loops:
            return
        
        loops = self._repeat_loops[self._current_file]
        complete_loops = [(i, start, end) for i, (start, end) in enumerate(loops) if start is not None and end is not None]
        
        if not complete_loops:
            return
        
        if self._current_loop_index == -1 or self._current_loop_index <= 0:
            self._current_loop_index = len(complete_loops) - 1
        else:
            self._current_loop_index -= 1
        
        _, loop_start, _ = complete_loops[self._current_loop_index]
        if loop_start is not None:
            self._is_user_seeking = True
            self.set_seek_position(int(loop_start))
            self.seekChanged.emit(int(loop_start))
            self._is_user_seeking = False
    
    def jump_to_next_loop(self):
        if not self._current_file or self._current_file not in self._repeat_loops:
            return
        
        loops = self._repeat_loops[self._current_file]
        complete_loops = [(i, start, end) for i, (start, end) in enumerate(loops) if start is not None and end is not None]
        
        if not complete_loops:
            return
        
        if self._current_loop_index == -1 or self._current_loop_index >= len(complete_loops) - 1:
            self._current_loop_index = 0
        else:
            self._current_loop_index += 1
        
        _, loop_start, _ = complete_loops[self._current_loop_index]
        if loop_start is not None:
            self._is_user_seeking = True
            self.set_seek_position(int(loop_start))
            self.seekChanged.emit(int(loop_start))
            self._is_user_seeking = False

    def delete_current_bookmark(self):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        if not hasattr(self, '_bookmarks_dialog') or self._bookmarks_dialog is None:
            return
        idx = self._bookmarks_dialog.get_selected_bookmark_index()
        if idx is None:
            return
        if 0 <= idx < len(self._bookmarks[self._current_file]):
            del self._bookmarks[self._current_file][idx]
            self.save_bookmarks()
            self._bookmarks_dialog.remove_bookmark_at(idx)

    def delete_bookmark_at(self, index:int):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        if 0 <= index < len(self._bookmarks[self._current_file]):
            del self._bookmarks[self._current_file][index]
            self._current_bookmark_index = -1
            self.save_bookmarks()
            self._refresh_bookmarks_dialog()
    
    def set_loop_start(self):
        if not self._current_file:
            return
        current_pos = float(self.get_seek_position())
        self.set_loop_start_precise(current_pos)
    
    def set_loop_end(self):
        if not self._current_file:
            return
        current_pos = float(self.get_seek_position())
        self.set_loop_end_precise(current_pos)

    def set_loop_start_precise(self, position: float):
        if not self._current_file:
            return

        if self._current_file not in self._repeat_loops:
            self._repeat_loops[self._current_file] = []

        if self._is_position_in_existing_loop(position):
            return

        self._repeat_loops[self._current_file].append((position, None))
        self.save_repeat_loops()

    def set_loop_end_precise(self, position: float):
        if not self._current_file:
            return

        if self._current_file not in self._repeat_loops:
            return

        loops = self._repeat_loops[self._current_file]
        if not loops:
            return

        for i in range(len(loops) - 1, -1, -1):
            if loops[i][1] is None:
                loop_start = loops[i][0]

                if loop_start is None or position <= loop_start:
                    return

                if self._would_loop_intersect(loop_start, position, exclude_index=i):
                    return

                loops[i] = (loop_start, position)
                self._current_loop_index = i
                self.save_repeat_loops()

                if loop_start is not None:
                    self._is_user_seeking = True
                    self.set_seek_position(int(loop_start))
                    self.seekChanged.emit(int(loop_start))
                    self._is_user_seeking = False

                return
    
    def clear_repeat_loop(self):
        if not self._current_file or self._current_file not in self._repeat_loops:
            return
        
        loops = self._repeat_loops[self._current_file]
        if not loops:
            return
        
        complete_loops = [(i, start, end) for i, (start, end) in enumerate(loops) if start is not None and end is not None]
        
        if not complete_loops:
            incomplete_loops = [i for i, (start, end) in enumerate(loops) if start is None or end is None]
            if incomplete_loops:
                del loops[incomplete_loops[-1]]
            self.save_repeat_loops()
            return
        
        if self._current_loop_index == -1 or self._current_loop_index >= len(complete_loops):
            self._current_loop_index = len(complete_loops) - 1
        
        if 0 <= self._current_loop_index < len(complete_loops):
            actual_index, _, _ = complete_loops[self._current_loop_index]
            del loops[actual_index]
            
            if self._current_loop_index >= len([l for l in loops if l[0] is not None and l[1] is not None]):
                self._current_loop_index = max(0, len([l for l in loops if l[0] is not None and l[1] is not None]) - 1)
            
            if not loops or all(start is None or end is None for start, end in loops):
                self._current_loop_index = -1
        
        self.save_repeat_loops()
    
    def clear_all_repeat_loops(self):
        if self._current_file and self._current_file in self._repeat_loops:
            self._repeat_loops[self._current_file] = []
            self._current_loop_index = -1
            self.save_repeat_loops()
    
    def get_current_loops(self) -> List[Tuple[Optional[float], Optional[float]]]:
        if not self._current_file or self._current_file not in self._repeat_loops:
            return []
        return self._repeat_loops[self._current_file]

    def update_loop_by_index(self, index:int, start:float, end:float):
        if not self._current_file or self._current_file not in self._repeat_loops:
            return False
        loops = self._repeat_loops[self._current_file]
        if index < 0 or index >= len(loops):
            return False
        if start is None or end is None or end <= start:
            return False
        # ensure no intersection with other loops
        if self._would_loop_intersect(start, end, exclude_index=index):
            return False
        loops[index] = (start, end)
        self._current_loop_index = index
        self.save_repeat_loops()
        return True

    def delete_loop_by_index(self, index:int):
        if not self._current_file or self._current_file not in self._repeat_loops:
            return False
        loops = self._repeat_loops[self._current_file]
        if index < 0 or index >= len(loops):
            return False
        del loops[index]
        # adjust current index
        complete_count = len([l for l in loops if l[0] is not None and l[1] is not None])
        if complete_count == 0:
            self._current_loop_index = -1
        else:
            self._current_loop_index = max(0, min(self._current_loop_index, complete_count - 1))
        self.save_repeat_loops()
        return True

    def add_bookmark_at_position(self, position:float):
        if not self._current_file:
            return False
        if self._current_file not in self._bookmarks:
            self._bookmarks[self._current_file] = []
        self._bookmarks[self._current_file].append(position)
        self._bookmarks[self._current_file].sort()
        self.save_bookmarks()
        if hasattr(self, '_bookmarks_dialog') and self._bookmarks_dialog is not None:
            self._refresh_bookmarks_dialog()
        return True

    def update_bookmark_at_index(self, index:int, position:float):
        if not self._current_file or self._current_file not in self._bookmarks:
            return False
        bookmarks = self._bookmarks[self._current_file]
        if index < 0 or index >= len(bookmarks):
            return False
        bookmarks[index] = position
        bookmarks.sort()
        self.save_bookmarks()
        if hasattr(self, '_bookmarks_dialog') and self._bookmarks_dialog is not None:
            self._refresh_bookmarks_dialog()
        return True
    
    def should_loop_playback(self, current_position: float) -> Optional[float]:
        if not self._current_file or self._current_file not in self._repeat_loops:
            return None
        
        if self._is_user_seeking:
            self._last_known_position = current_position
            return None
        
        current_time = time.time()
        if current_time - self._last_loop_trigger_time < 1.0:
            self._last_known_position = current_position
            return None
        
        position_delta = current_position - self._last_known_position
        
        if abs(position_delta) > 2.0:
            self._last_known_position = current_position
            return None
        
        loops = self._repeat_loops[self._current_file]
        for loop_start, loop_end in loops:
            if loop_start is not None and loop_end is not None:
                if self._last_known_position < loop_end and current_position >= loop_end:
                    if position_delta > 0 and position_delta < 2.0:
                        self._last_loop_trigger_time = current_time
                        self._last_known_position = loop_start
                        return loop_start
        
        self._last_known_position = current_position
        return None
    
    def _is_position_in_existing_loop(self, position: float) -> bool:
        if self._current_file not in self._repeat_loops:
            return False
        
        loops = self._repeat_loops[self._current_file]
        for loop_start, loop_end in loops:
            if loop_start is not None and loop_end is not None:
                if loop_start <= position <= loop_end:
                    return True
        return False
    
    def _would_loop_intersect(self, new_start: float, new_end: float, exclude_index: int = -1) -> bool:
        if self._current_file not in self._repeat_loops:
            return False
        
        loops = self._repeat_loops[self._current_file]
        for i, (loop_start, loop_end) in enumerate(loops):
            if i == exclude_index:
                continue
            
            if loop_start is not None and loop_end is not None:
                if (new_start <= loop_start <= new_end or 
                    new_start <= loop_end <= new_end or
                    loop_start <= new_start <= loop_end or
                    loop_start <= new_end <= loop_end):
                    return True
        return False
    
    def get_bookmarks(self) -> List[float]:
        if not self._current_file or self._current_file not in self._bookmarks:
            return []
        return self._bookmarks[self._current_file].copy()
    
    def clear_bookmarks(self):
        if self._current_file and self._current_file in self._bookmarks:
            del self._bookmarks[self._current_file]
            self._current_bookmark_index = -1
            self.save_bookmarks()
            if hasattr(self, '_bookmarks_dialog') and self._bookmarks_dialog is not None:
                self._bookmarks_dialog.clear_all()
    
    def save_bookmarks(self):
        bookmarks_file = os.path.join(self._data_dir, "bookmarks.json")
        try:
            with open(bookmarks_file, 'w') as f:
                json.dump(self._bookmarks, f, indent=2)
        except Exception:
            pass
    
    def load_bookmarks(self):
        bookmarks_file = os.path.join(self._data_dir, "bookmarks.json")
        try:
            if os.path.exists(bookmarks_file):
                with open(bookmarks_file, 'r') as f:
                    self._bookmarks = json.load(f)
        except Exception:
            self._bookmarks = {}
    
    def save_repeat_loops(self):
        loops_file = os.path.join(self._data_dir, "repeat_loops.json")
        try:
            with open(loops_file, 'w') as f:
                json.dump(self._repeat_loops, f, indent=2)
        except Exception:
            pass
    
    def load_repeat_loops(self):
        loops_file = os.path.join(self._data_dir, "repeat_loops.json")
        try:
            if os.path.exists(loops_file):
                with open(loops_file, 'r') as f:
                    self._repeat_loops = json.load(f)
        except Exception:
            self._repeat_loops = {}
    
    def save_last_position(self):
        if not self._current_file:
            return
        
        current_pos = self.get_seek_position()
        self._last_positions[self._current_file] = current_pos
        
        positions_file = os.path.join(self._data_dir, "last_positions.json")
        try:
            with open(positions_file, 'w') as f:
                json.dump(self._last_positions, f, indent=2)
        except Exception:
            pass
    
    def load_last_positions(self):
        positions_file = os.path.join(self._data_dir, "last_positions.json")
        try:
            if os.path.exists(positions_file):
                with open(positions_file, 'r') as f:
                    self._last_positions = json.load(f)
        except Exception:
            self._last_positions = {}
    
    def load_last_position(self):
        if not self._current_file:
            return
        
        if self._current_file in self._last_positions:
            try:
                last_pos = self._last_positions[self._current_file]
                if isinstance(last_pos, (int, float)) and last_pos >= 0:
                    #max_duration = self.seek_slider.maximum()
                    #if max_duration > 0 and last_pos <= max_duration:
                    self.last_position = int(last_pos)
                        #self.set_seek_position(int(last_pos))
                        #self.seekChanged.emit(int(last_pos))
            except Exception as e:
                pass

    def _refresh_bookmarks_dialog(self):
        if not hasattr(self, '_bookmarks_dialog') or self._bookmarks_dialog is None:
            return
        dlg = self._bookmarks_dialog
        dlg.clear_all()
        if self._current_file and self._current_file in self._bookmarks:
            for i, bookmark in enumerate(self._bookmarks[self._current_file]):
                minutes = int(bookmark // 60)
                seconds = int(bookmark % 60)
                dlg.bookmarks_list.addItem(f"Mark {i+1}: {minutes:02d}:{seconds:02d}")
    
    def volume_up(self):
        current_volume = self.get_volume()
        volume_offset = prefs.prefs["offset"]["volume"]
        new_volume = min(100, current_volume + volume_offset)
        self.set_volume(new_volume)
        self.volumeChanged.emit(new_volume)
    
    def volume_down(self):
        current_volume = self.get_volume()
        volume_offset = prefs.prefs["offset"]["volume"]
        new_volume = max(0, current_volume - volume_offset)
        self.set_volume(new_volume)
        self.volumeChanged.emit(new_volume)
    
    def check_loop_position(self, current_position: float):
        loop_position = self.should_loop_playback(current_position)
        if loop_position is not None:
            self.set_seek_position(int(loop_position))
            self.seekChanged.emit(int(loop_position))
    
    def _check_current_position(self):
        if self._current_file:
            current_pos = float(self.get_seek_position())
            self.check_loop_position(current_pos)
    
    #def install_shortcuts(self):
        #self._shortcut_manager.install_on_application()
    
    #def uninstall_shortcuts(self):
        #self._shortcut_manager.uninstall_from_application()

