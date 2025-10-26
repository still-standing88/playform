from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from gui_controls.toggle_button import ToggleButton
from gui_controls.player_key_event_filter import KeyEventFilter


class SubtitlesWidget(QWidget):
    subtitlesToggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_event_filter = KeyEventFilter(self)
        
        self.setup_ui()
        self.connect_signals()
        self._install_event_filter()
        
        self.subtitles_list.setVisible(False)
        self.toggle_btn.setText("Show subtitles")
        self.toggle_btn.setActuated(True)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Subtitles", self)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setAccessibleName("Subtitles section")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.toggle_btn = ToggleButton("Hide Subtitles", self)
        self.toggle_btn.setFixedSize(60, 25)
        header_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(header_layout)
        
        self.subtitles_list = QListWidget(self)
        self.subtitles_list.setAccessibleName("Subtitles display")
        self.subtitles_list.setAccessibleDescription("Current video subtitles")
        self.subtitles_list.setAlternatingRowColors(True)
        self.subtitles_list.setMaximumHeight(150)
        
        self.subtitles_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
        """)
        
        layout.addWidget(self.subtitles_list)
        
    def connect_signals(self):
        self.toggle_btn.actuated.connect(self.toggle_subtitles)
        
    def toggle_subtitles(self, hidden):
        self.subtitles_list.setVisible(not hidden)
        
        if hidden:
            self.toggle_btn.setText("Show subtitles")
        else:
            self.toggle_btn.setText("Hide subtitles")
            
        self.subtitlesToggled.emit(not hidden)
        
    def add_subtitle_line(self, text, timestamp=None):
        item = QListWidgetItem(text)
        if timestamp:
            item.setData(Qt.ItemDataRole.UserRole, timestamp)

        self.subtitles_list.addItem(item)
        
    def clear_subtitles(self):
        self.subtitles_list.clear()
        
    def highlight_subtitle_at_time(self, timestamp):
        for i in range(self.subtitles_list.count()):
            item = self.subtitles_list.item(i)
            item_timestamp = item.data(Qt.ItemDataRole.UserRole)
            if item_timestamp and item_timestamp <= timestamp:
                self.subtitles_list.setCurrentItem(item)
            else:
                break
                
    def _install_event_filter(self):
        widgets = [self.subtitles_list, self.toggle_btn]
        self._key_event_filter.install_on_widgets(widgets)
