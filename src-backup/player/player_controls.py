import os
import json
from typing import Optional, Callable, Dict, List, Tuple
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                               QSlider, QLabel, QSizePolicy, QFrame, QDialog, QListWidget, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QFont
from gui_controls.toggle_button import ToggleButton
from gui_controls.key_event_filter import ShortcutManager
from app_config import key_config


class BookmarksDialog(QDialog):
    def __init__(self, bookmarks: List[float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bookmarks")
        self.setModal(True)
        self.resize(300, 400)
        
        layout = QVBoxLayout(self)
        
        self.bookmarks_list = QListWidget(self)
        for i, bookmark in enumerate(bookmarks):
            minutes = int(bookmark // 60)
            seconds = int(bookmark % 60)
            self.bookmarks_list.addItem(f"Mark {i+1}: {minutes:02d}:{seconds:02d}")
        
        layout.addWidget(self.bookmarks_list)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_selected_bookmark_index(self):
        current_row = self.bookmarks_list.currentRow()
        return current_row if current_row >= 0 else None


class PlayerControls(QWidget):
    playPauseClicked = Signal()
    muteUnmuteClicked = Signal()
    forwardClicked = Signal()
    backwardClicked = Signal()
    previousClicked = Signal()
    nextClicked = Signal()
    repeatClicked = Signal()
    
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.is_minimized = False
        self.is_playing = False
        self.is_muted = False
        self.is_repeat_on = False
        
        self._current_file: Optional[str] = None
        self._bookmarks: Dict[str, List[float]] = {}
        self._last_positions: Dict[str, float] = {}
        self._repeat_loops: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        self._data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(self._data_dir, exist_ok=True)
        
        self._shortcut_manager: ShortcutManager = ShortcutManager(self)
        
        self.setup_ui()
        self.layout_widgets()
        self.connect_signals()
        self.apply_styles()
        self.set_shortcuts()
        self.load_bookmarks()
        self.load_last_positions()
        self.load_repeat_loops()
        
        self.time_update_timer = QTimer(self)
        self.time_update_timer.timeout.connect(self.timeUpdateRequested.emit)
        self.time_update_timer.timeout.connect(self._check_current_position)
        self.time_update_timer.start(250)
        
    def setup_ui(self):
        self.toggle_controls_btn = ToggleButton("◀", self)
        self.toggle_controls_btn.setFixedSize(30, 30)
        self.toggle_controls_btn.setToolTip("Minimize/Maximize Controls")
        
        self.previous_btn = QPushButton("⏮", self)
        self.backward_btn = QPushButton("⏪", self)
        self.play_pause_btn = QPushButton("▶", self)
        self.forward_btn = QPushButton("⏩", self)
        self.next_btn = QPushButton("⏭", self)
        self.repeat_btn = QPushButton("🔁", self)
        
        for btn in [self.previous_btn, self.backward_btn, self.play_pause_btn, 
                   self.forward_btn, self.next_btn, self.repeat_btn]:
            btn.setFixedSize(40, 40)
            
        self.play_pause_btn.setFixedSize(50, 50)
        
        self.previous_btn.setToolTip("Previous")
        self.backward_btn.setToolTip("Backward 10s")
        self.play_pause_btn.setToolTip("Play/Pause")
        self.forward_btn.setToolTip("Forward 10s")
        self.next_btn.setToolTip("Next")
        self.repeat_btn.setToolTip("Repeat")
        
        self.seek_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(100)
        self.seek_slider.setValue(0)
        self.seek_slider.setAccessibleName("Seek")
        self.seek_slider.setAccessibleDescription("Video position slider")
        
        self.mute_btn = QPushButton("🔊", self)
        self.mute_btn.setFixedSize(35, 35)
        self.mute_btn.setToolTip("Mute/Unmute")
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setAccessibleName("Volume")
        self.volume_slider.setAccessibleDescription("Volume control slider")
        
        self.time_label = QLabel("00:00 / 00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setMinimumWidth(100)
        self.time_label.setAccessibleName("Time Display")
        self.time_label.setAccessibleDescription("Shows elapsed and total time")
        
        self.current_track_label = QLabel("No media loaded", self)
        self.current_track_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.current_track_label.setAccessibleName("Currently Playing")
        
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
        self.controls_layout.addWidget(self.toggle_controls_btn)
        
        self.main_layout.addLayout(self.track_layout)
        self.main_layout.addLayout(self.controls_layout)
        
        self.expandable_widgets = [
            self.previous_btn, self.backward_btn, self.forward_btn, 
            self.next_btn, self.repeat_btn, self.separator1, 
            self.seek_slider, self.separator2, self.mute_btn, 
            self.volume_slider, self.time_label, self.current_track_label
        ]
        
    def connect_signals(self):
        self.play_pause_btn.clicked.connect(self.playPauseClicked.emit)
        self.mute_btn.clicked.connect(self.muteUnmuteClicked.emit)
        self.forward_btn.clicked.connect(self.forwardClicked.emit)
        self.backward_btn.clicked.connect(self.backwardClicked.emit)
        self.previous_btn.clicked.connect(self.previousClicked.emit)
        self.next_btn.clicked.connect(self.nextClicked.emit)
        self.repeat_btn.clicked.connect(self.repeatClicked.emit)
        
        self.seek_slider.valueChanged.connect(self.seekChanged.emit)
        self.seek_slider.sliderPressed.connect(self.seekPressed.emit)
        self.seek_slider.sliderReleased.connect(self.seekReleased.emit)
        self.volume_slider.valueChanged.connect(self.volumeChanged.emit)
        
        self.volumeUpRequested.connect(self.volume_up)
        self.volumeDownRequested.connect(self.volume_down)
        
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
                   self.forward_btn, self.next_btn, self.repeat_btn, self.mute_btn]:
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
            self.toggle_controls_btn.setText("▶")
            self.toggle_controls_btn.setToolTip("Maximize Controls")
        else:
            self.toggle_controls_btn.setText("◀")
            self.toggle_controls_btn.setToolTip("Minimize Controls")
            
        self.controlsToggled.emit(not minimized)
        
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
                      self.forward_btn, self.next_btn, self.repeat_btn, 
                      self.mute_btn, self.seek_slider, self.volume_slider]:
            widget.setEnabled(enabled)
    
    def set_shortcuts(self):
        hotkeys = key_config.key_dict["Player"]
        
        shortcuts: Dict[str, Callable] = {
            hotkeys["Play/pause"]: self.playPauseClicked.emit,
            hotkeys["Backward"]: self.backwardClicked.emit,
            hotkeys["Forward"]: self.forwardClicked.emit,
            hotkeys["Stop"]: self.stopRequested.emit,
            hotkeys["Mute/Unmute"]: self.muteUnmuteClicked.emit,
            hotkeys["Previous"]: self.previousClicked.emit,
            hotkeys["Next"]: self.nextClicked.emit,
            hotkeys["Jump to beginning"]: self.jumpToBeginningRequested.emit,
            hotkeys["Jump to the end"]: self.jumpToEndRequested.emit,
            hotkeys["Toggle repeat"]: self.repeatClicked.emit,
            hotkeys["Volume up"]: self.volume_up,
            hotkeys["Volume down"]: self.volume_down,
            hotkeys["Bookmarks list"]: self.show_bookmarks_dialog,
            hotkeys["New mark at current position"]: self.add_bookmark_at_current_position,
            hotkeys["Repeat loop start"]: self.set_loop_start,
            hotkeys["Repeat loop end"]: self.set_loop_end,
            hotkeys["Clear repeat loop"]: self.clear_repeat_loop,
            hotkeys["Mark1 position"]: lambda: self.jump_to_mark(0),
            hotkeys["Mark2 position"]: lambda: self.jump_to_mark(1),
            hotkeys["Mark3 position"]: lambda: self.jump_to_mark(2),
            hotkeys["Mark4 position"]: lambda: self.jump_to_mark(3),
            hotkeys["Mark5 position"]: lambda: self.jump_to_mark(4),
            hotkeys["Mark6 position"]: lambda: self.jump_to_mark(5),
            hotkeys["Mark7 position"]: lambda: self.jump_to_mark(6),
            hotkeys["Mark8 position"]: lambda: self.jump_to_mark(7),
            hotkeys["Mark9 position"]: lambda: self.jump_to_mark(8),
            hotkeys["Mark10 position"]: lambda: self.jump_to_mark(9),
        }
        
        self._shortcut_manager.clear_shortcuts()
        for shortcut, callback in shortcuts.items():
            self._shortcut_manager.add_widget_shortcut(self, shortcut, callback)
    
    def reset_shortcuts(self):
        self.set_shortcuts()
    
    def set_current_file(self, file_path: str):
        if self._current_file:
            self.save_last_position()
        
        self._current_file = file_path
        self.load_last_position()
    
    def show_bookmarks_dialog(self):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        
        bookmarks = self._bookmarks[self._current_file]
        if not bookmarks:
            return
        
        dialog = BookmarksDialog(bookmarks, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_index = dialog.get_selected_bookmark_index()
            if selected_index is not None:
                self.jump_to_mark(selected_index)
    
    def add_bookmark_at_current_position(self):
        if not self._current_file:
            return
        
        current_pos = self.get_seek_position()
        
        if self._current_file not in self._bookmarks:
            self._bookmarks[self._current_file] = []
        
        self._bookmarks[self._current_file].append(current_pos)
        self._bookmarks[self._current_file].sort()
        self.save_bookmarks()
    
    def jump_to_mark(self, mark_index: int):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        
        bookmarks = self._bookmarks[self._current_file]
        if mark_index < len(bookmarks):
            position = bookmarks[mark_index]
            self.set_seek_position(int(position))
            self.seekChanged.emit(int(position))
    
    def set_loop_start(self):
        if not self._current_file:
            return
        
        current_pos = float(self.get_seek_position())
        
        if self._current_file not in self._repeat_loops:
            self._repeat_loops[self._current_file] = (None, None)
        
        loop_start, loop_end = self._repeat_loops[self._current_file]
        self._repeat_loops[self._current_file] = (current_pos, loop_end)
        self.save_repeat_loops()
    
    def set_loop_end(self):
        if not self._current_file:
            return
        
        current_pos = float(self.get_seek_position())
        
        if self._current_file not in self._repeat_loops:
            self._repeat_loops[self._current_file] = (None, None)
        
        loop_start, loop_end = self._repeat_loops[self._current_file]
        self._repeat_loops[self._current_file] = (loop_start, current_pos)
        self.save_repeat_loops()
    
    def clear_repeat_loop(self):
        if self._current_file and self._current_file in self._repeat_loops:
            self._repeat_loops[self._current_file] = (None, None)
            self.save_repeat_loops()
    
    def get_current_loop(self) -> Tuple[Optional[float], Optional[float]]:
        if not self._current_file or self._current_file not in self._repeat_loops:
            return (None, None)
        return self._repeat_loops[self._current_file]
    
    def should_loop_playback(self, current_position: float) -> Optional[float]:
        if not self._current_file or self._current_file not in self._repeat_loops:
            return None
        
        loop_start, loop_end = self._repeat_loops[self._current_file]
        if loop_start is not None and loop_end is not None:
            if current_position >= loop_end:
                return loop_start
        return None
    
    def get_bookmarks(self) -> List[float]:
        if not self._current_file or self._current_file not in self._bookmarks:
            return []
        return self._bookmarks[self._current_file].copy()
    
    def clear_bookmarks(self):
        if self._current_file and self._current_file in self._bookmarks:
            del self._bookmarks[self._current_file]
            self.save_bookmarks()
    
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
            last_pos = self._last_positions[self._current_file]
            self.set_seek_position(int(last_pos))
            self.seekChanged.emit(int(last_pos))
    
    def volume_up(self):
        current_volume = self.get_volume()
        new_volume = min(100, current_volume + 5)
        self.set_volume(new_volume)
        self.volumeChanged.emit(new_volume)
    
    def volume_down(self):
        current_volume = self.get_volume()
        new_volume = max(0, current_volume - 5)
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
    
    def install_shortcuts(self):
        self._shortcut_manager.install_on_application()
    
    def uninstall_shortcuts(self):
        self._shortcut_manager.uninstall_from_application()