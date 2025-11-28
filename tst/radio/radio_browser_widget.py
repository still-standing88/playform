import asyncio
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QMenu, QMessageBox,
    QHeaderView, QGroupBox, QStatusBar, QGridLayout, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction

from radios import FilterBy, Order
from radios.models import Station, Country, Language, Tag
from radio_browser_service import RadioBrowserService


class RadioWorkerThread(QThread):
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, service: RadioBrowserService, operation: str, params: dict):
        super().__init__()
        self.service = service
        self.operation = operation
        self.params = params
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if self.operation == 'countries':
                result = loop.run_until_complete(
                    self.service.get_countries(order=Order.NAME)
                )
            elif self.operation == 'languages':
                result = loop.run_until_complete(
                    self.service.get_languages(order=Order.NAME)
                )
            elif self.operation == 'tags':
                result = loop.run_until_complete(
                    self.service.get_tags(order=Order.STATION_COUNT, reverse=True)
                )
            elif self.operation == 'search':
                result = loop.run_until_complete(
                    self.service.search_stations(**self.params)
                )
            elif self.operation == 'filter':
                result = loop.run_until_complete(
                    self.service.get_stations_by_filter(**self.params)
                )
            elif self.operation == 'favorites':
                result = self.service.get_favorites()
            elif self.operation == 'click':
                loop.run_until_complete(
                    self.service.click_station(uuid=self.params['uuid'])
                )
                result = True
            else:
                result = None
            
            loop.close()
            self.finished.emit(result)
                
        except Exception as e:
            self.error.emit(str(e))


class RadioBrowserWidget(QWidget):
    
    def __init__(self, parent=None, user_agent: str = "RadioBrowserWidget/1.0"):
        super().__init__(parent)
        self.user_agent = user_agent
        self.service = RadioBrowserService(user_agent)
        self.current_stations: List[Station] = []
        
        self.countries: List[Country] = []
        self.languages: List[Language] = []
        self.tags: List[Tag] = []
        
        self.countries_loaded = False
        self.languages_loaded = False
        self.tags_loaded = False
        
        self.filter_load_thread: Optional[RadioWorkerThread] = None
        self.search_thread: Optional[RadioWorkerThread] = None
        self.click_thread: Optional[RadioWorkerThread] = None  # Add this line
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        search_group = QGroupBox("Search and Filter")
        search_layout = QGridLayout()
        search_layout.setSpacing(8)
        
        search_layout.addWidget(QLabel("Station Name:"), 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter station name...")
        self.search_input.setAccessibleName("Station name search")
        self.search_input.setAccessibleDescription("Type a station name and press Enter to search")
        self.search_input.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_input, 0, 1, 1, 2)
        
        self.search_button = QPushButton("Search")
        self.search_button.setAccessibleName("Search button")
        self.search_button.setAccessibleDescription("Click to search by station name")
        self.search_button.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_button, 0, 3)
        
        search_layout.addWidget(QLabel("Filter By:"), 1, 0)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["None", "Country", "Language", "Tag", "Codec"])
        self.filter_combo.setAccessibleName("Filter type")
        self.filter_combo.setAccessibleDescription("Select how to filter stations")
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        search_layout.addWidget(self.filter_combo, 1, 1)
        
        search_layout.addWidget(QLabel("Value:"), 1, 2)
        self.filter_value = QComboBox()
        self.filter_value.setEditable(True)
        self.filter_value.setEnabled(False)
        self.filter_value.setAccessibleName("Filter value")
        self.filter_value.setAccessibleDescription("Select or type a filter value")
        search_layout.addWidget(self.filter_value, 1, 3)
        
        search_layout.addWidget(QLabel("Sort By:"), 2, 0)
        self.order_combo = QComboBox()
        self.order_combo.addItems(["Name", "Votes", "Country", "Language", "Bitrate", "Click Count"])
        self.order_combo.setAccessibleName("Sort order")
        self.order_combo.setAccessibleDescription("Select how to sort results")
        search_layout.addWidget(self.order_combo, 2, 1)
        
        self.apply_filter_button = QPushButton("Apply Filters")
        self.apply_filter_button.setAccessibleName("Apply filters button")
        self.apply_filter_button.setAccessibleDescription("Click to apply selected filters")
        self.apply_filter_button.clicked.connect(self.apply_filters)
        self.apply_filter_button.setEnabled(False)
        search_layout.addWidget(self.apply_filter_button, 2, 2, 1, 2)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.favorites_button = QPushButton("Show Favorites")
        self.favorites_button.setAccessibleName("Show favorites button")
        self.favorites_button.setAccessibleDescription("Click to view favorite stations")
        self.favorites_button.clicked.connect(self.show_favorites)
        button_layout.addWidget(self.favorites_button)
        
        self.clear_cache_button = QPushButton("Clear Cache")
        self.clear_cache_button.setAccessibleName("Clear cache button")
        self.clear_cache_button.setAccessibleDescription("Click to clear cached data")
        self.clear_cache_button.clicked.connect(self.clear_cache)
        button_layout.addWidget(self.clear_cache_button)
        
        button_layout.addStretch()
        
        search_layout.addLayout(button_layout, 3, 0, 1, 4)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(5, 5, 5, 5)
        
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["Name", "Country", "Language(s)", "Codec", "Bitrate"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionsMovable(False)
        header.setSectionsClickable(False)
        
        self.tree.setAccessibleName("Radio stations list")
        self.tree.setAccessibleDescription("List of radio stations. Right-click or double-click for options.")
        
        results_layout.addWidget(self.tree)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Ready - Enter search term or select filters")
    
    def set_buttons_enabled(self, enabled: bool):
        self.search_button.setEnabled(enabled)
        self.apply_filter_button.setEnabled(enabled and self.filter_combo.currentText() != "None")
        self.favorites_button.setEnabled(enabled)
        self.clear_cache_button.setEnabled(enabled)
    
    def on_filter_changed(self, filter_type: str):
        self.filter_value.clear()
        
        if filter_type == "None":
            self.filter_value.setEnabled(False)
            self.apply_filter_button.setEnabled(False)
        else:
            self.filter_value.setEnabled(True)
            self.apply_filter_button.setEnabled(True)
            if filter_type not in ["Codec"]:
                self.load_filter_data(filter_type)
    
    def load_filter_data(self, filter_type: str):
        if self.filter_load_thread and self.filter_load_thread.isRunning():
            return
        
        op_map = {
            "Country": ('countries', self.countries_loaded, self.on_countries_loaded),
            "Language": ('languages', self.languages_loaded, self.on_languages_loaded),
            "Tag": ('tags', self.tags_loaded, self.on_tags_loaded)
        }
        
        if filter_type in op_map:
            op, loaded, callback = op_map[filter_type]
            if not loaded:
                self.status_bar.showMessage(f"Loading {op}...")
                self.set_buttons_enabled(False)
                self.filter_load_thread = RadioWorkerThread(self.service, op, {})
                self.filter_load_thread.finished.connect(callback)
                self.filter_load_thread.error.connect(self.handle_error)
                self.filter_load_thread.start()
            else:
                self.populate_filter_combo()
        else:
            self.populate_filter_combo()
    
    def on_countries_loaded(self, countries):
        self.countries = countries
        self.countries_loaded = True
        self.populate_filter_combo()
        self.status_bar.showMessage(f"Loaded {len(countries)} countries", 3000)
        self.set_buttons_enabled(True)
        self.filter_load_thread = None
    
    def on_languages_loaded(self, languages):
        self.languages = languages
        self.languages_loaded = True
        self.populate_filter_combo()
        self.status_bar.showMessage(f"Loaded {len(languages)} languages", 3000)
        self.set_buttons_enabled(True)
        self.filter_load_thread = None
    
    def on_tags_loaded(self, tags):
        self.tags = tags[:250]  # Limit tags for performance
        self.tags_loaded = True
        self.populate_filter_combo()
        self.status_bar.showMessage(f"Loaded top {len(self.tags)} tags", 3000)
        self.set_buttons_enabled(True)
        self.filter_load_thread = None
    
    def populate_filter_combo(self):
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
    
    def get_common_search_params(self) -> Dict:
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

    def perform_search(self):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        search_name = self.search_input.text().strip()
        if not search_name:
            self.status_bar.showMessage("Enter a station name to search", 3000)
            return
        
        self.status_bar.showMessage(f"Searching for '{search_name}'...")
        self.set_buttons_enabled(False)
        
        params = self.get_common_search_params()
        params['name'] = search_name
        
        self.search_thread = RadioWorkerThread(self.service, 'search', params)
        self.search_thread.finished.connect(self.display_results)
        self.search_thread.error.connect(self.handle_error)
        self.search_thread.start()
    
    def apply_filters(self):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        filter_type = self.filter_combo.currentText()
        filter_value = self.filter_value.currentText().strip()
        
        if filter_type == "None" or not filter_value:
            self.status_bar.showMessage("Select a filter type and value", 3000)
            return
        
        filter_map = {
            "Country": FilterBy.COUNTRY_EXACT, "Language": FilterBy.LANGUAGE_EXACT,
            "Tag": FilterBy.TAG_EXACT, "Codec": FilterBy.CODEC_EXACT,
        }
        
        self.status_bar.showMessage(f"Filtering by {filter_type}: {filter_value}...")
        self.set_buttons_enabled(False)
        
        params = self.get_common_search_params()
        params['filter_by'] = filter_map[filter_type]
        params['filter_term'] = filter_value
        
        self.search_thread = RadioWorkerThread(self.service, 'filter', params)
        self.search_thread.finished.connect(self.display_results)
        self.search_thread.error.connect(self.handle_error)
        self.search_thread.start()
    
    def show_favorites(self):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        self.status_bar.showMessage("Loading favorites...")
        self.set_buttons_enabled(False)
        
        self.search_thread = RadioWorkerThread(self.service, 'favorites', {})
        self.search_thread.finished.connect(self.display_favorites)
        self.search_thread.error.connect(self.handle_error)
        self.search_thread.start()
    
    def display_favorites(self, favorites: List[Dict]):
        self.tree.clear()
        self.current_stations = []
        
        for fav in favorites:
            item = QTreeWidgetItem(self.tree)
            
            lang_data = fav.get("language", [])
            lang_str = ", ".join(lang_data) if isinstance(lang_data, list) else str(lang_data)
            
            item.setText(0, fav.get("name", "Unknown"))
            item.setText(1, fav.get("country", ""))
            item.setText(2, lang_str)
            item.setText(3, fav.get("codec", ""))
            item.setText(4, str(fav.get("bitrate", "")))
            item.setData(0, Qt.ItemDataRole.UserRole, fav)
            
            desc = (f"Favorite Station: {fav.get('name', 'Unknown')}. "
                    f"Country: {fav.get('country', 'N/A')}. Language: {lang_str or 'N/A'}.")
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            self.tree.addTopLevelItem(item)
        
        self.status_bar.showMessage(f"Showing {len(favorites)} favorite stations")
        self.set_buttons_enabled(True)
        self.search_thread = None
    
    def display_results(self, stations: List[Station]):
        self.tree.clear()
        
        if not stations:
            self.status_bar.showMessage("No results found")
            self.set_buttons_enabled(True)
            self.search_thread = None
            return
        
        self.current_stations = stations
        
        for station in stations:
            item = QTreeWidgetItem(self.tree)
            lang_str = ", ".join(station.language) if station.language else ""
            
            item.setText(0, station.name)
            item.setText(1, station.country or "")
            item.setText(2, lang_str)
            item.setText(3, station.codec or "")
            item.setText(4, str(station.bitrate) if station.bitrate else "")
            item.setData(0, Qt.ItemDataRole.UserRole, station)
            
            tags_str = ", ".join(station.tags) if station.tags else "None"
            desc = (f"Station: {station.name}. "
                    f"Country: {station.country or 'N/A'}. "
                    f"Language: {lang_str or 'N/A'}. "
                    f"Codec: {station.codec or 'N/A'}. "
                    f"Bitrate: {station.bitrate or 'N/A'}. "
                    f"Votes: {station.votes}. "
                    f"Tags: {tags_str}.")
            if self.service.is_favorite(station.uuid):
                desc += " This station is in your favorites."
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            self.tree.addTopLevelItem(item)
        
        self.status_bar.showMessage(f"Found {len(stations)} stations")
        self.set_buttons_enabled(True)
        self.search_thread = None
    
    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item: return
        
        station_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not station_data: return

        uuid = station_data.uuid if isinstance(station_data, Station) else station_data.get("uuid")
        if not uuid: return
        
        menu = QMenu(self)
        is_fav = self.service.is_favorite(uuid)
        
        actions = [
            ("Play Station", lambda: self.play_station(station_data)),
            ("Register Click", lambda: self.click_station(uuid)),
            (None, None),
            ("Remove from Favorites" if is_fav else "Add to Favorites", 
             lambda: self.remove_favorite(station_data, item) if is_fav else self.add_favorite(station_data, item)),
            (None, None),
            ("Station Information", lambda: self.show_station_info(station_data)),
            ("Copy Stream URL", lambda: self.copy_url(station_data)),
        ]
        
        for name, callback in actions:
            if name is None:
                menu.addSeparator()
            else:
                action = QAction(name, self)
                action.triggered.connect(callback)
                menu.addAction(action)

        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def on_item_double_clicked(self, item, column):
        station_data = item.data(0, Qt.ItemDataRole.UserRole)
        if station_data:
            self.play_station(station_data)
    
    def play_station(self, station_data):
        name = station_data.name if isinstance(station_data, Station) else station_data.get("name", "Unknown")
        url = (station_data.url_resolved or station_data.url) if isinstance(station_data, Station) \
            else (station_data.get("url_resolved") or station_data.get("url", ""))
        
        QMessageBox.information(self, "Play Station",
            f"<b>Playing: {name}</b><br><br>Stream URL: {url}<br><br>"
            "<i>(This is a demo. Integrate with a media player like VLC to play the stream.)</i>")
        self.status_bar.showMessage(f"Playing: {name}")
    
    def click_station(self, uuid: str):
        # FIX: Check if a click thread is already running
        if self.click_thread and self.click_thread.isRunning():
            self.status_bar.showMessage("Click registration already in progress...", 2000)
            return
        
        # FIX: Store the thread in self.click_thread to prevent garbage collection
        self.click_thread = RadioWorkerThread(self.service, 'click', {'uuid': uuid})
        self.click_thread.finished.connect(lambda: self.status_bar.showMessage("Click registered successfully", 3000))
        self.click_thread.error.connect(lambda e: self.status_bar.showMessage(f"Click failed: {e}", 4000))
        
        # Clean up the reference once it's done
        self.click_thread.finished.connect(lambda: setattr(self, 'click_thread', None))
        self.click_thread.error.connect(lambda: setattr(self, 'click_thread', None))
        
        self.click_thread.start()
    
    def add_favorite(self, station_data, item):
        if not isinstance(station_data, Station): return
        self.service.add_favorite(station_data)
        desc = item.data(0, Qt.ItemDataRole.AccessibleDescriptionRole)
        if desc and "in your favorites" not in desc:
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc + " This station is in your favorites.")
        self.status_bar.showMessage(f"Added '{station_data.name}' to favorites")
    
    def remove_favorite(self, station_data, item):
        uuid = station_data.uuid if isinstance(station_data, Station) else station_data.get("uuid")
        name = station_data.name if isinstance(station_data, Station) else station_data.get("name", "Unknown")
        self.service.remove_favorite(uuid)
        desc = item.data(0, Qt.ItemDataRole.AccessibleDescriptionRole)
        if desc:
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc.replace(" This station is in your favorites.", ""))
        self.status_bar.showMessage(f"Removed '{name}' from favorites")
        if self.favorites_button.text() == "Show All Stations":
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

    
    def show_station_info(self, station_data):
        if isinstance(station_data, Station):
            info = [f"<b>{station_data.name}</b>",
                    f"<b>UUID:</b> {station_data.uuid}",
                    f"<b>Country:</b> {station_data.country}",
                    f"<b>Language(s):</b> {', '.join(station_data.language)}",
                    f"<b>Tags:</b> {', '.join(station_data.tags)}",
                    f"<b>Codec:</b> {station_data.codec} @ {station_data.bitrate} kbps",
                    f"<b>Votes:</b> {station_data.votes}",
                    f"<b>Homepage:</b> {station_data.homepage}",
                    f"<b>Stream URL:</b> {station_data.url_resolved or station_data.url}"]
        else:
            info = [f"<b>{station_data.get('name', 'N/A')}</b>",
                    f"<b>UUID:</b> {station_data.get('uuid', 'N/A')}",
                    f"<b>Country:</b> {station_data.get('country', 'N/A')}",
                    f"<b>Language(s):</b> {station_data.get('language', 'N/A')}",
                    f"<b>Stream URL:</b> {station_data.get('url_resolved') or station_data.get('url', '')}"]
        QMessageBox.information(self, "Station Information", "<br>".join(info))
    
    def copy_url(self, station_data):
        url = (station_data.url_resolved or station_data.url) if isinstance(station_data, Station) \
            else (station_data.get("url_resolved") or station_data.get("url", ""))
        if url:
            QApplication.clipboard().setText(url)
            self.status_bar.showMessage("Stream URL copied to clipboard", 3000)
        else:
            self.status_bar.showMessage("No stream URL available for this station", 3000)
    
    def clear_cache(self):
        reply = QMessageBox.question(self, "Clear Cache", "Clear all cached data?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.service.clear_cache()
            self.countries_loaded = self.languages_loaded = self.tags_loaded = False
            self.countries, self.languages, self.tags = [], [], []
            self.filter_value.clear()
            self.status_bar.showMessage("Cache cleared", 3000)
    
    def handle_error(self, error_msg: str):
        QMessageBox.warning(self, "Error", f"An error occurred:\n{error_msg}")
        self.status_bar.showMessage("Error occurred", 4000)
        self.set_buttons_enabled(True)
        self.filter_load_thread = self.search_thread = None
    
    def closeEvent(self, event):
        for thread in [self.filter_load_thread, self.search_thread, self.click_thread]:
            if thread and thread.isRunning():
                thread.quit()
                thread.wait()
        event.accept()