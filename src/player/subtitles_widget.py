from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor

from gui_controls.toggle_button import ToggleButton
from gui_controls.player_key_event_filter import KeyEventFilter
from app_constance.styles import SUBTITLES_LIST_STYLE


class SubtitlesWidget(QWidget):
    subtitlesToggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_event_filter = KeyEventFilter(self)
        self._all_subtitles_loaded = False  # Track if we've loaded all subtitles
        
        self.setup_ui()
        self.connect_signals()
        self._install_event_filter()
        
        self.subtitles_list.setVisible(False)
        self.toggle_btn.setText(_("Show subtitles"))
        self.toggle_btn.setActuated(True)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel(_("Subtitles"), self)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setAccessibleName(_("Subtitles section"))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.toggle_btn = ToggleButton(_("Hide Subtitles"), self)
        self.toggle_btn.setFixedSize(60, 25)
        header_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(header_layout)
        
        self.subtitles_list = QListWidget(self)
        self.subtitles_list.setAccessibleName(_("Subtitles display"))
        self.subtitles_list.setAccessibleDescription(_("Current video subtitles"))
        self.subtitles_list.setAlternatingRowColors(True)
        self.subtitles_list.setMaximumHeight(150)
        
        self.subtitles_list.setStyleSheet(SUBTITLES_LIST_STYLE)
        
        layout.addWidget(self.subtitles_list)
        
    def connect_signals(self):
        self.toggle_btn.actuated.connect(self.toggle_subtitles)
        
    @Slot(bool)
    def toggle_subtitles(self, hidden):
        self.subtitles_list.setVisible(not hidden)
        
        if hidden:
            self.toggle_btn.setText(_("Show subtitles"))
        else:
            self.toggle_btn.setText(_("Hide subtitles"))
            
        self.subtitlesToggled.emit(not hidden)
        
    def add_subtitle_line(self, text, timestamp=None):
        item = QListWidgetItem(text)
        if timestamp:
            item.setData(Qt.ItemDataRole.UserRole, timestamp)

        self.subtitles_list.addItem(item)
        
    def clear_subtitles(self):
        self.subtitles_list.clear()
        self._all_subtitles_loaded = False
    
    def load_all_subtitles(self, subtitle_manager):
        """Load all subtitles from subtitle manager"""
        self.subtitles_list.clear()
        for sub in subtitle_manager.subtitles:
            item = QListWidgetItem(sub.text)
            item.setData(Qt.ItemDataRole.UserRole, sub.start)  # Store start time
            self.subtitles_list.addItem(item)
        self._all_subtitles_loaded = True
        
    def highlight_subtitle_at_time(self, timestamp_usec):
        """Highlight the subtitle at given timestamp"""
        if not self._all_subtitles_loaded:
            return
        
        for i in range(self.subtitles_list.count()):
            item = self.subtitles_list.item(i)
            item_timestamp = item.data(Qt.ItemDataRole.UserRole)
            
            # Clear previous highlight
            item.setBackground(QColor(0, 0, 0, 0))  # Transparent
            
            # Check if this is the active subtitle
            if item_timestamp is not None and item_timestamp <= timestamp_usec:
                # Check if next subtitle exists and hasn't started yet
                if i + 1 < self.subtitles_list.count():
                    next_item = self.subtitles_list.item(i + 1)
                    next_timestamp = next_item.data(Qt.ItemDataRole.UserRole)
                    if next_timestamp and next_timestamp > timestamp_usec:
                        # This is the current subtitle
                        item.setBackground(QColor(255, 255, 0, 80))  # Yellow highlight
                        self.subtitles_list.scrollToItem(item)
                        break
                else:
                    # Last subtitle
                    item.setBackground(QColor(255, 255, 0, 80))
                    self.subtitles_list.scrollToItem(item)
                    break
                
    def _install_event_filter(self):
        widgets = [self.subtitles_list, self.toggle_btn]
        self._key_event_filter.install_on_widgets(widgets)
