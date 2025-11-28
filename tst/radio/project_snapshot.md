# Project Snapshot: radio

Generated on: The current date is: Tue 11/11/2025 
Enter the new date: (mm-dd-yy)

## Table of Contents

- [Directory: cache](#directory-cache)
- [Directory: data](#directory-data)

## Files


<a name="directory-root"></a>
### Directory: `Root`


#### File: `project_snapshot.md`

```markdown

```

#### File: `radio_browser_service.py`

```python
import asyncio
import json
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from radios import FilterBy, Order, RadioBrowser
from radios.models import Country, Language, Station, Stats, Tag


class RadioBrowserService:
    
    def __init__(self, user_agent: str = "RadioBrowserWidget/1.0"):
        self.user_agent = user_agent
        self.cache_dir = Path("./cache")
        self.data_dir = Path("./data")
        self.cache_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        self.favorites_file = self.data_dir / "radio_stations.json"
        self.favorites: Dict[str, Dict[str, Any]] = self._load_favorites()
        
        self.cache_expiry = {
            "stats": 24,
            "countries": 168,
            "languages": 168,
            "tags": 24,
            "search": 1,
        }

    def _load_favorites(self) -> Dict[str, Dict[str, Any]]:
        if self.favorites_file.exists():
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading favorites: {e}")
                return {}
        return {}

    def _save_favorites(self) -> None:
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving favorites: {e}")

    def _get_cache_path(self, cache_type: str, key: str = "") -> Path:
        if key:
            return self.cache_dir / f"{cache_type}_{key}.pkl"
        return self.cache_dir / f"{cache_type}.pkl"

    def _is_cache_valid(self, cache_path: Path, cache_type: str) -> bool:
        if not cache_path.exists():
            return False
        
        mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_hours = self.cache_expiry.get(cache_type, 1)
        expiry_time = timedelta(hours=expiry_hours)
        
        return datetime.now() - mod_time < expiry_time

    def _load_cache(self, cache_path: Path) -> Optional[Any]:
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None

    def _save_cache(self, cache_path: Path, data: Any) -> None:
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    async def get_stats(self, use_cache: bool = True) -> Stats:
        cache_path = self._get_cache_path("stats")
        
        if use_cache and self._is_cache_valid(cache_path, "stats"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stats = await rb.stats()
        
        self._save_cache(cache_path, stats)
        return stats

    async def get_countries(self, use_cache: bool = True, **kwargs) -> List[Country]:
        cache_path = self._get_cache_path("countries")
        
        if use_cache and self._is_cache_valid(cache_path, "countries"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            countries = await rb.countries(
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self._save_cache(cache_path, countries)
        return countries

    async def get_languages(self, use_cache: bool = True, **kwargs) -> List[Language]:
        cache_path = self._get_cache_path("languages")
        
        if use_cache and self._is_cache_valid(cache_path, "languages"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            languages = await rb.languages(
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self._save_cache(cache_path, languages)
        return languages

    async def get_tags(self, use_cache: bool = True, **kwargs) -> List[Tag]:
        cache_path = self._get_cache_path("tags")
        
        if use_cache and self._is_cache_valid(cache_path, "tags"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            tags = await rb.tags(
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self._save_cache(cache_path, tags)
        return tags

    async def search_stations(self, use_cache: bool = True, **kwargs) -> List[Station]:
        name = kwargs.get('name', '')
        country = kwargs.get('country', '')
        
        cache_key = f"{name}_{country}_{kwargs.get('order', Order.NAME)}"
        cache_key = cache_key.replace(' ', '_').replace('/', '_')
        cache_path = self._get_cache_path("search", cache_key)
        
        if use_cache and self._is_cache_valid(cache_path, "search"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stations = await rb.search(
                name=kwargs.get('name'),
                country=kwargs.get('country'),
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
                hide_broken=kwargs.get('hide_broken', False),
            )
        
        self._save_cache(cache_path, stations)
        return stations

    async def get_stations_by_filter(self, filter_by: FilterBy, filter_term: str, 
                                    use_cache: bool = True, **kwargs) -> List[Station]:
        cache_key = f"{filter_by.value}_{filter_term}_{kwargs.get('order', Order.NAME)}"
        cache_key = cache_key.replace(' ', '_').replace('/', '_')
        cache_path = self._get_cache_path("filter", cache_key)
        
        if use_cache and self._is_cache_valid(cache_path, "search"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stations = await rb.stations(
                filter_by=filter_by,
                filter_term=filter_term,
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
                hide_broken=kwargs.get('hide_broken', False),
            )
        
        self._save_cache(cache_path, stations)
        return stations

    async def get_station_by_uuid(self, uuid: str) -> Optional[Station]:
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            return await rb.station(uuid=uuid)

    async def click_station(self, uuid: str) -> None:
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            await rb.station_click(uuid=uuid)

    def add_favorite(self, station: Station) -> None:
        self.favorites[station.uuid] = {
            "uuid": station.uuid,
            "name": station.name,
            "url": station.url,
            "url_resolved": station.url_resolved,
            "country": station.country,
            "language": station.language,
            "tags": station.tags,
            "votes": station.votes,
            "codec": station.codec,
            "bitrate": station.bitrate,
            "homepage": station.homepage,
            "favicon": station.favicon,
            "added_date": datetime.now().isoformat(),
        }
        self._save_favorites()

    def remove_favorite(self, uuid: str) -> None:
        if uuid in self.favorites:
            del self.favorites[uuid]
            self._save_favorites()

    def is_favorite(self, uuid: str) -> bool:
        return uuid in self.favorites

    def get_favorites(self) -> List[Dict[str, Any]]:
        return list(self.favorites.values())

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        if cache_type:
            for cache_file in self.cache_dir.glob(f"{cache_type}*.pkl"):
                cache_file.unlink()
        else:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
```

#### File: `radio_browser_widget.py`

```python
import asyncio
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QMenu, QMessageBox,
    QHeaderView, QGroupBox, QStatusBar, QGridLayout
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
        self.filter_value.setAccessibleDescription("Select a filter value")
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
        self.tree.setHeaderLabels(["Name", "Country", "Language", "Codec", "Bitrate"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionsMovable(False)
        header.setSectionsClickable(False)
        
        self.tree.setAccessibleName("Radio stations list")
        self.tree.setAccessibleDescription("List of radio stations. Right-click for options.")
        
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
            self.filter_value.setEnabled(False)
            self.apply_filter_button.setEnabled(False)
            self.load_filter_data(filter_type)
    
    def load_filter_data(self, filter_type: str):
        if self.filter_load_thread and self.filter_load_thread.isRunning():
            return
        
        if filter_type == "Country" and not self.countries_loaded:
            self.status_bar.showMessage("Loading countries...")
            self.set_buttons_enabled(False)
            self.filter_load_thread = RadioWorkerThread(self.service, 'countries', {})
            self.filter_load_thread.finished.connect(self.on_countries_loaded)
            self.filter_load_thread.error.connect(self.handle_error)
            self.filter_load_thread.start()
            
        elif filter_type == "Language" and not self.languages_loaded:
            self.status_bar.showMessage("Loading languages...")
            self.set_buttons_enabled(False)
            self.filter_load_thread = RadioWorkerThread(self.service, 'languages', {})
            self.filter_load_thread.finished.connect(self.on_languages_loaded)
            self.filter_load_thread.error.connect(self.handle_error)
            self.filter_load_thread.start()
            
        elif filter_type == "Tag" and not self.tags_loaded:
            self.status_bar.showMessage("Loading tags...")
            self.set_buttons_enabled(False)
            self.filter_load_thread = RadioWorkerThread(self.service, 'tags', {})
            self.filter_load_thread.finished.connect(self.on_tags_loaded)
            self.filter_load_thread.error.connect(self.handle_error)
            self.filter_load_thread.start()
            
        else:
            self.populate_filter_combo()
    
    def on_countries_loaded(self, countries):
        self.countries = countries
        self.countries_loaded = True
        self.populate_filter_combo()
        self.status_bar.showMessage(f"Loaded {len(countries)} countries", 2000)
        self.set_buttons_enabled(True)
        self.filter_load_thread = None
    
    def on_languages_loaded(self, languages):
        self.languages = languages
        self.languages_loaded = True
        self.populate_filter_combo()
        self.status_bar.showMessage(f"Loaded {len(languages)} languages", 2000)
        self.set_buttons_enabled(True)
        self.filter_load_thread = None
    
    def on_tags_loaded(self, tags):
        self.tags = tags[:200]
        self.tags_loaded = True
        self.populate_filter_combo()
        self.status_bar.showMessage(f"Loaded {len(self.tags)} tags", 2000)
        self.set_buttons_enabled(True)
        self.filter_load_thread = None
    
    def populate_filter_combo(self):
        filter_type = self.filter_combo.currentText()
        self.filter_value.clear()
        
        if filter_type == "Country":
            items = [c.name for c in self.countries if c.name]
            self.filter_value.addItems(sorted(items))
        elif filter_type == "Language":
            items = [l.name for l in self.languages if l.name]
            self.filter_value.addItems(sorted(items))
        elif filter_type == "Tag":
            items = [t.name for t in self.tags if t.name]
            self.filter_value.addItems(items)
        
        self.filter_value.setEnabled(True)
        self.apply_filter_button.setEnabled(True)
    
    def perform_search(self):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        search_name = self.search_input.text().strip()
        
        if not search_name:
            self.status_bar.showMessage("Enter a station name to search")
            return
        
        order_text = self.order_combo.currentText()
        order_map = {
            "Name": Order.NAME,
            "Votes": Order.VOTES,
            "Country": Order.COUNTRY,
            "Language": Order.LANGUAGE,
            "Bitrate": Order.BITRATE,
            "Click Count": Order.CLICK_COUNT,
        }
        order = order_map.get(order_text, Order.NAME)
        
        self.status_bar.showMessage("Searching...")
        self.set_buttons_enabled(False)
        
        params = {
            'name': search_name,
            'order': order,
            'reverse': True if order in [Order.VOTES, Order.CLICK_COUNT] else False,
            'hide_broken': True,
            'limit': 500
        }
        
        self.search_thread = RadioWorkerThread(self.service, 'search', params)
        self.search_thread.finished.connect(self.display_results)
        self.search_thread.error.connect(self.handle_error)
        self.search_thread.start()
    
    def apply_filters(self):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        filter_type = self.filter_combo.currentText()
        filter_value = self.filter_value.currentText().strip()
        
        if filter_type == "None":
            self.status_bar.showMessage("Select a filter type")
            return
        
        if not filter_value:
            self.status_bar.showMessage("Select or enter a filter value")
            return
        
        order_text = self.order_combo.currentText()
        order_map = {
            "Name": Order.NAME,
            "Votes": Order.VOTES,
            "Country": Order.COUNTRY,
            "Language": Order.LANGUAGE,
            "Bitrate": Order.BITRATE,
            "Click Count": Order.CLICK_COUNT,
        }
        order = order_map.get(order_text, Order.NAME)
        
        filter_map = {
            "Country": FilterBy.COUNTRY_EXACT,
            "Language": FilterBy.LANGUAGE_EXACT,
            "Tag": FilterBy.TAG_EXACT,
            "Codec": FilterBy.CODEC_EXACT,
        }
        
        self.status_bar.showMessage(f"Filtering by {filter_type}: {filter_value}...")
        self.set_buttons_enabled(False)
        
        params = {
            'filter_by': filter_map[filter_type],
            'filter_term': filter_value,
            'order': order,
            'reverse': True if order in [Order.VOTES, Order.CLICK_COUNT] else False,
            'hide_broken': True,
            'limit': 500
        }
        
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
    
    def display_favorites(self, favorites: List):
        self.tree.clear()
        self.current_stations = []
        
        for fav in favorites:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, fav.get("name", "Unknown"))
            item.setText(1, fav.get("country", ""))
            item.setText(2, fav.get("language", ""))
            item.setText(3, fav.get("codec", ""))
            item.setText(4, str(fav.get("bitrate", "")))
            
            item.setData(0, Qt.ItemDataRole.UserRole, fav)
            
            desc = f"Favorite station: {fav.get('name', 'Unknown')}, "
            desc += f"Country: {fav.get('country', 'Unknown')}, "
            desc += f"Language: {fav.get('language', 'Unknown')}"
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            
            self.tree.addTopLevelItem(item)
        
        self.status_bar.showMessage(f"Showing {len(favorites)} favorite stations")
        self.set_buttons_enabled(True)
        self.search_thread = None
    
    def display_results(self, stations):
        self.tree.clear()
        
        if stations is None or len(stations) == 0:
            self.status_bar.showMessage("No results found")
            self.set_buttons_enabled(True)
            self.search_thread = None
            return
        
        self.current_stations = stations
        
        for station in stations:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, station.name)
            item.setText(1, station.country)
            item.setText(2, station.language)
            item.setText(3, station.codec)
            item.setText(4, str(station.bitrate) if station.bitrate else "")
            
            item.setData(0, Qt.ItemDataRole.UserRole, station)
            
            desc = f"Station: {station.name}, Country: {station.country}, "
            desc += f"Language: {station.language}, "
            desc += f"Codec: {station.codec}, Bitrate: {station.bitrate or 'Unknown'}, "
            desc += f"Votes: {station.votes}"
            if self.service.is_favorite(station.uuid):
                desc += ", Favorited"
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            
            self.tree.addTopLevelItem(item)
        
        self.status_bar.showMessage(f"Found {len(stations)} stations")
        self.set_buttons_enabled(True)
        self.search_thread = None
    
    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        
        station_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not station_data:
            return
        
        menu = QMenu(self)
        
        uuid = station_data.uuid if isinstance(station_data, Station) else station_data.get("uuid")
        is_fav = self.service.is_favorite(uuid)
        
        play_action = QAction("Play Station", self)
        play_action.triggered.connect(lambda: self.play_station(station_data))
        menu.addAction(play_action)
        
        click_action = QAction("Register Click", self)
        click_action.triggered.connect(lambda: self.click_station(uuid))
        menu.addAction(click_action)
        
        menu.addSeparator()
        
        if is_fav:
            fav_action = QAction("Remove from Favorites", self)
            fav_action.triggered.connect(lambda: self.remove_favorite(station_data, item))
        else:
            fav_action = QAction("Add to Favorites", self)
            fav_action.triggered.connect(lambda: self.add_favorite(station_data, item))
        menu.addAction(fav_action)
        
        menu.addSeparator()
        
        info_action = QAction("Station Information", self)
        info_action.triggered.connect(lambda: self.show_station_info(station_data))
        menu.addAction(info_action)
        
        copy_action = QAction("Copy Stream URL", self)
        copy_action.triggered.connect(lambda: self.copy_url(station_data))
        menu.addAction(copy_action)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def on_item_double_clicked(self, item, column):
        station_data = item.data(0, Qt.ItemDataRole.UserRole)
        if station_data:
            self.play_station(station_data)
    
    def play_station(self, station_data):
        if isinstance(station_data, Station):
            name = station_data.name
            url = station_data.url_resolved or station_data.url
        else:
            name = station_data.get("name", "Unknown")
            url = station_data.get("url_resolved") or station_data.get("url", "")
        
        QMessageBox.information(
            self,
            "Play Station",
            f"Playing: {name}\n\nStream URL: {url}\n\n"
            "Integrate this with your preferred media player."
        )
        self.status_bar.showMessage(f"Playing: {name}")
    
    def click_station(self, uuid: str):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        thread = RadioWorkerThread(self.service, 'click', {'uuid': uuid})
        thread.finished.connect(lambda x: self.status_bar.showMessage("Click registered", 2000))
        thread.error.connect(lambda e: self.status_bar.showMessage(f"Click failed: {e}", 3000))
        thread.finished.connect(thread.deleteLater)
        thread.error.connect(thread.deleteLater)
        thread.start()
    
    def add_favorite(self, station_data, item):
        if isinstance(station_data, Station):
            self.service.add_favorite(station_data)
            name = station_data.name
        else:
            return
        
        desc = item.data(0, Qt.ItemDataRole.AccessibleDescriptionRole)
        if desc and ", Favorited" not in desc:
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc + ", Favorited")
        
        self.status_bar.showMessage(f"Added '{name}' to favorites")
    
    def remove_favorite(self, station_data, item):
        uuid = station_data.uuid if isinstance(station_data, Station) else station_data.get("uuid")
        name = station_data.name if isinstance(station_data, Station) else station_data.get("name", "Unknown")
        
        self.service.remove_favorite(uuid)
        
        desc = item.data(0, Qt.ItemDataRole.AccessibleDescriptionRole)
        if desc:
            desc = desc.replace(", Favorited", "")
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
        
        self.status_bar.showMessage(f"Removed '{name}' from favorites")
    
    def show_station_info(self, station_data):
        if isinstance(station_data, Station):
            info = f"Station: {station_data.name}\n"
            info += f"UUID: {station_data.uuid}\n"
            info += f"Country: {station_data.country}\n"
            info += f"Language: {station_data.language}\n"
            info += f"Tags: {station_data.tags}\n"
            info += f"Codec: {station_data.codec}\n"
            info += f"Bitrate: {station_data.bitrate}\n"
            info += f"Votes: {station_data.votes}\n"
            info += f"Homepage: {station_data.homepage}\n"
            info += f"Stream URL: {station_data.url_resolved or station_data.url}\n"
        else:
            info = f"Station: {station_data.get('name', 'Unknown')}\n"
            info += f"UUID: {station_data.get('uuid', 'Unknown')}\n"
            info += f"Country: {station_data.get('country', '')}\n"
            info += f"Language: {station_data.get('language', '')}\n"
            info += f"Tags: {station_data.get('tags', '')}\n"
            info += f"Codec: {station_data.get('codec', '')}\n"
            info += f"Bitrate: {station_data.get('bitrate', '')}\n"
            info += f"Homepage: {station_data.get('homepage', '')}\n"
            info += f"Stream URL: {station_data.get('url_resolved') or station_data.get('url', '')}\n"
        
        QMessageBox.information(self, "Station Information", info)
    
    def copy_url(self, station_data):
        from PySide6.QtWidgets import QApplication
        
        if isinstance(station_data, Station):
            url = station_data.url_resolved or station_data.url
        else:
            url = station_data.get("url_resolved") or station_data.get("url", "")
        
        clipboard = QApplication.clipboard()
        clipboard.setText(url)
        self.status_bar.showMessage("Stream URL copied to clipboard")
    
    def clear_cache(self):
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "Clear all cached data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.service.clear_cache()
            self.countries_loaded = False
            self.languages_loaded = False
            self.tags_loaded = False
            self.countries = []
            self.languages = []
            self.tags = []
            self.filter_value.clear()
            self.status_bar.showMessage("Cache cleared")
    
    def handle_error(self, error_msg: str):
        QMessageBox.warning(self, "Error", f"An error occurred: {error_msg}")
        self.status_bar.showMessage("Error occurred")
        self.set_buttons_enabled(True)
        
        if self.filter_load_thread:
            self.filter_load_thread = None
        if self.search_thread:
            self.search_thread = None
    
    def closeEvent(self, event):
        if self.filter_load_thread and self.filter_load_thread.isRunning():
            self.filter_load_thread.quit()
            self.filter_load_thread.wait()
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.quit()
            self.search_thread.wait()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.service.close())
        finally:
            loop.close()
        
        event.accept()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = RadioBrowserWidget()
    widget.setWindowTitle("Radio Browser")
    widget.resize(1000, 600)
    widget.show()
    
    sys.exit(app.exec())
```

#### File: `radio_demo.py`

```python
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QKeySequence

from radio_browser_widget import RadioBrowserWidget


class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radio Browser - Browse Internet Radio Stations")
        self.resize(1100, 650)
        
        self.radio_widget = RadioBrowserWidget(self, user_agent="RadioBrowserDemo/1.0")
        self.setCentralWidget(self.radio_widget)
        
        self.create_menu_bar()
        
        QTimer.singleShot(500, self.show_welcome)
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        refresh_action = QAction("&Refresh Search", self)
        refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        refresh_action.setStatusTip("Refresh current search results")
        refresh_action.triggered.connect(self.radio_widget.perform_search)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.setStatusTip("Exit application")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        search_menu = menubar.addMenu("&Search")
        
        focus_search_action = QAction("Focus &Search Box", self)
        focus_search_action.setShortcut(QKeySequence("Ctrl+F"))
        focus_search_action.setStatusTip("Focus the search input field")
        focus_search_action.triggered.connect(self.focus_search)
        search_menu.addAction(focus_search_action)
        
        perform_search_action = QAction("&Perform Search", self)
        perform_search_action.setShortcut(QKeySequence("Return"))
        perform_search_action.setStatusTip("Execute the current search")
        perform_search_action.triggered.connect(self.radio_widget.perform_search)
        search_menu.addAction(perform_search_action)
        
        search_menu.addSeparator()
        
        clear_cache_action = QAction("Clear &Cache", self)
        clear_cache_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        clear_cache_action.setStatusTip("Clear all cached data")
        clear_cache_action.triggered.connect(self.radio_widget.clear_cache)
        search_menu.addAction(clear_cache_action)
        
        favorites_menu = menubar.addMenu("&Favorites")
        
        show_favorites_action = QAction("Show &Favorites", self)
        show_favorites_action.setShortcut(QKeySequence("Ctrl+D"))
        show_favorites_action.setStatusTip("Display favorite stations")
        show_favorites_action.triggered.connect(self.radio_widget.show_favorites)
        favorites_menu.addAction(show_favorites_action)
        
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        instructions_action = QAction("&Instructions", self)
        instructions_action.setShortcut(QKeySequence("F1"))
        instructions_action.setStatusTip("Show usage instructions")
        instructions_action.triggered.connect(self.show_instructions)
        help_menu.addAction(instructions_action)
    
    def show_welcome(self):
        self.radio_widget.status_bar.showMessage(
            "Welcome! Select a filter or search to browse stations",
            6000
        )
    
    def focus_search(self):
        self.radio_widget.search_input.setFocus()
        self.radio_widget.search_input.selectAll()
    
    def show_about(self):
        QMessageBox.about(
            self,
            "About Radio Browser",
            "<h2>Radio Browser Demo</h2>"
            "<p>Browse and search thousands of internet radio stations.</p>"
            "<p><b>Built with PySide6 and the Radio Browser API.</b></p>"
        )
    
    def show_instructions(self):
        instructions = """
        <h3>How to Use Radio Browser</h3>
        
        <h4>Searching for Stations:</h4>
        <ul>
            <li><b>By Name:</b> Type a station name</li>
            <li><b>By Filter:</b> Select Country/Language/Tag and choose a value</li>
            <li><b>Auto-search:</b> Results update automatically when you make selections</li>
        </ul>
        
        <h4>Station Actions (Right-Click Menu):</h4>
        <ul>
            <li><b>Play Station:</b> Shows stream URL</li>
            <li><b>Register Click:</b> Marks station as played</li>
            <li><b>Add/Remove Favorites:</b> Save stations</li>
            <li><b>Station Information:</b> View details</li>
            <li><b>Copy Stream URL:</b> Copy to clipboard</li>
        </ul>
        
        <h4>Keyboard Shortcuts:</h4>
        <ul>
            <li><b>Ctrl+F:</b> Focus search box</li>
            <li><b>Ctrl+R:</b> Refresh search</li>
            <li><b>Ctrl+D:</b> Show favorites</li>
            <li><b>Ctrl+Shift+C:</b> Clear cache</li>
        </ul>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Instructions")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(instructions)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Radio Browser Demo")
    app.setOrganizationName("RadioBrowser")
    
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```
