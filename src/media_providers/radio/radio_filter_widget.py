from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QGroupBox
)
from PySide6.QtCore import Signal
from radios import Order
from radios.models import Country, Language, Tag
from app_constance.styles import (
    RADIO_GROUP_BOX_STYLE, RADIO_COMBO_STYLE, 
    RADIO_LINE_EDIT_STYLE, RADIO_BUTTON_STYLE
)


class RadioFilterWidget(QWidget):
    search_requested = Signal(str, dict)
    filter_requested = Signal(str, str, dict)
    favorites_requested = Signal()
    cache_clear_requested = Signal()
    filter_data_requested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.countries: List[Country] = []
        self.languages: List[Language] = []
        self.tags: List[Tag] = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        search_group = QGroupBox("Search and Filter")
        search_group.setStyleSheet(RADIO_GROUP_BOX_STYLE)
        search_layout = QGridLayout()
        search_layout.setSpacing(8)
        
        search_layout.addWidget(QLabel("Station Name:"), 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter station name...")
        self.search_input.setAccessibleName("Station name search")
        self.search_input.setAccessibleDescription("Type a station name and press Enter to search")
        self.search_input.setStyleSheet(RADIO_LINE_EDIT_STYLE)
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input, 0, 1, 1, 2)
        
        self.search_button = QPushButton("Search")
        self.search_button.setAccessibleName("Search button")
        self.search_button.setAccessibleDescription("Click to search by station name")
        self.search_button.setStyleSheet(RADIO_BUTTON_STYLE)
        self.search_button.clicked.connect(self._on_search)
        search_layout.addWidget(self.search_button, 0, 3)
        
        search_layout.addWidget(QLabel("Filter By:"), 1, 0)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["None", "Country", "Language", "Tag", "Codec"])
        self.filter_combo.setAccessibleName("Filter type")
        self.filter_combo.setAccessibleDescription("Select how to filter stations")
        self.filter_combo.setStyleSheet(RADIO_COMBO_STYLE)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.filter_combo, 1, 1)
        
        search_layout.addWidget(QLabel("Value:"), 1, 2)
        self.filter_value = QComboBox()
        self.filter_value.setEditable(True)
        self.filter_value.setEnabled(False)
        self.filter_value.setAccessibleName("Filter value")
        self.filter_value.setAccessibleDescription("Select or type a filter value")
        self.filter_value.setStyleSheet(RADIO_COMBO_STYLE)
        search_layout.addWidget(self.filter_value, 1, 3)
        
        search_layout.addWidget(QLabel("Sort By:"), 2, 0)
        self.order_combo = QComboBox()
        self.order_combo.addItems(["Name", "Votes", "Country", "Language", "Bitrate", "Click Count"])
        self.order_combo.setAccessibleName("Sort order")
        self.order_combo.setAccessibleDescription("Select how to sort results")
        self.order_combo.setStyleSheet(RADIO_COMBO_STYLE)
        search_layout.addWidget(self.order_combo, 2, 1)
        
        self.apply_filter_button = QPushButton("Apply Filters")
        self.apply_filter_button.setAccessibleName("Apply filters button")
        self.apply_filter_button.setAccessibleDescription("Click to apply selected filters")
        self.apply_filter_button.setStyleSheet(RADIO_BUTTON_STYLE)
        self.apply_filter_button.clicked.connect(self._on_apply_filter)
        self.apply_filter_button.setEnabled(False)
        search_layout.addWidget(self.apply_filter_button, 2, 2, 1, 2)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.favorites_button = QPushButton("Show Favorites")
        self.favorites_button.setAccessibleName("Show favorites button")
        self.favorites_button.setAccessibleDescription("Click to view favorite stations")
        self.favorites_button.setStyleSheet(RADIO_BUTTON_STYLE)
        self.favorites_button.clicked.connect(self._on_show_favorites)
        button_layout.addWidget(self.favorites_button)
        
        self.clear_cache_button = QPushButton("Clear Cache")
        self.clear_cache_button.setAccessibleName("Clear cache button")
        self.clear_cache_button.setAccessibleDescription("Click to clear cached data")
        self.clear_cache_button.setStyleSheet(RADIO_BUTTON_STYLE)
        self.clear_cache_button.clicked.connect(self._on_clear_cache)
        button_layout.addWidget(self.clear_cache_button)
        
        button_layout.addStretch()
        
        search_layout.addLayout(button_layout, 3, 0, 1, 4)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

    def _on_filter_changed(self, filter_type: str):
        self.filter_value.clear()
        
        if filter_type == "None":
            self.filter_value.setEnabled(False)
            self.apply_filter_button.setEnabled(False)
        else:
            self.filter_value.setEnabled(True)
            self.apply_filter_button.setEnabled(True)
            if filter_type not in ["Codec"]:
                self.filter_data_requested.emit(filter_type)

    def _on_search(self):
        search_name = self.search_input.text().strip()
        if not search_name:
            return
        
        params = self._get_common_params()
        params['name'] = search_name
        self.search_requested.emit(search_name, params)

    def _on_apply_filter(self):
        filter_type = self.filter_combo.currentText()
        filter_value = self.filter_value.currentText().strip()
        
        if filter_type == "None" or not filter_value:
            return
        
        params = self._get_common_params()
        self.filter_requested.emit(filter_type, filter_value, params)

    def _on_show_favorites(self):
        self.favorites_requested.emit()

    def _on_clear_cache(self):
        self.cache_clear_requested.emit()

    def _get_common_params(self) -> Dict:
        order_map = {
            "Name": Order.NAME, "Votes": Order.VOTES, "Country": Order.COUNTRY,
            "Language": Order.LANGUAGE, "Bitrate": Order.BITRATE, "Click Count": Order.CLICK_COUNT,
        }
        order = order_map.get(self.order_combo.currentText(), Order.NAME)
        
        return {
            'order': order,
            'reverse': order in [Order.VOTES, Order.CLICK_COUNT, Order.BITRATE],
            'hide_broken': True,
            'limit': 500
        }

    def set_countries(self, countries: List[Country]):
        self.countries = countries
        self._populate_filter_combo()

    def set_languages(self, languages: List[Language]):
        self.languages = languages
        self._populate_filter_combo()

    def set_tags(self, tags: List[Tag]):
        self.tags = tags[:250]
        self._populate_filter_combo()

    def _populate_filter_combo(self):
        filter_type = self.filter_combo.currentText()
        self.filter_value.clear()
        
        items = []
        if filter_type == "Country":
            items = sorted([c.name for c in self.countries if c.name])
        elif filter_type == "Language":
            items = sorted([l.name for l in self.languages if l.name])
        elif filter_type == "Tag":
            items = [t.name for t in self.tags if t.name]
        
        if items:
            self.filter_value.addItems(items)
        
        self.filter_value.setEnabled(filter_type != "None")
        self.apply_filter_button.setEnabled(filter_type != "None")

    def set_buttons_enabled(self, enabled: bool):
        self.search_button.setEnabled(enabled)
        self.apply_filter_button.setEnabled(enabled and self.filter_combo.currentText() != "None")
        self.favorites_button.setEnabled(enabled)
        self.clear_cache_button.setEnabled(enabled)
