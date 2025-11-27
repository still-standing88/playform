from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt
from radios import FilterBy
from radios.models import Station
from media_providers.radio.radio_service import RadioService
from media_providers.radio.radio_worker import RadioWorker
from media_providers.radio.radio_filter_widget import RadioFilterWidget
from media_providers.radio.radio_tree_widget import RadioTreeWidget
from app_constance.styles import RADIO_GROUP_BOX_STYLE


class RadioBrowserWidget(QWidget):
    def __init__(self, parent=None, user_agent: str = "PlayForm/1.0"):
        super().__init__(parent)
        self.user_agent = user_agent
        self.service = RadioService(user_agent)
        
        self.countries_loaded = False
        self.languages_loaded = False
        self.tags_loaded = False
        
        self.filter_load_thread: Optional[RadioWorker] = None
        self.search_thread: Optional[RadioWorker] = None
        self.click_thread: Optional[RadioWorker] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        self.filter_widget = RadioFilterWidget(self)
        layout.addWidget(self.filter_widget)
        
        results_group = QGroupBox("Results")
        results_group.setStyleSheet(RADIO_GROUP_BOX_STYLE)
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(5, 5, 5, 5)
        
        self.tree_widget = RadioTreeWidget(self)
        results_layout.addWidget(self.tree_widget)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Ready - Enter search term or select filters")

    def _connect_signals(self):
        self.filter_widget.search_requested.connect(self._perform_search)
        self.filter_widget.filter_requested.connect(self._apply_filter)
        self.filter_widget.favorites_requested.connect(self._show_favorites)
        self.filter_widget.cache_clear_requested.connect(self._clear_cache)
        self.filter_widget.filter_data_requested.connect(self._load_filter_data)
        
        self.tree_widget.play_requested.connect(self._play_station)
        self.tree_widget.click_requested.connect(self._click_station)
        self.tree_widget.favorite_added.connect(self._add_favorite)
        self.tree_widget.favorite_removed.connect(self._remove_favorite)
        self.tree_widget.info_requested.connect(self._show_station_info)

    def _perform_search(self, search_name: str, params: Dict):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        self.status_bar.showMessage(f"Searching for '{search_name}'...")
        self._set_buttons_enabled(False)
        
        self.search_thread = RadioWorker(self.service, 'search', params)
        self.search_thread.finished.connect(self._display_results)
        self.search_thread.error.connect(self._handle_error)
        self.search_thread.start()

    def _apply_filter(self, filter_type: str, filter_value: str, params: Dict):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        filter_map = {
            "Country": FilterBy.COUNTRY_EXACT, 
            "Language": FilterBy.LANGUAGE_EXACT,
            "Tag": FilterBy.TAG_EXACT, 
            "Codec": FilterBy.CODEC_EXACT,
        }
        
        self.status_bar.showMessage(f"Filtering by {filter_type}: {filter_value}...")
        self._set_buttons_enabled(False)
        
        params['filter_by'] = filter_map[filter_type]
        params['filter_term'] = filter_value
        
        self.search_thread = RadioWorker(self.service, 'filter', params)
        self.search_thread.finished.connect(self._display_results)
        self.search_thread.error.connect(self._handle_error)
        self.search_thread.start()

    def _show_favorites(self):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        self.status_bar.showMessage("Loading favorites...")
        self._set_buttons_enabled(False)
        
        self.search_thread = RadioWorker(self.service, 'favorites', {})
        self.search_thread.finished.connect(self._display_favorites)
        self.search_thread.error.connect(self._handle_error)
        self.search_thread.start()

    def _load_filter_data(self, filter_type: str):
        if self.filter_load_thread and self.filter_load_thread.isRunning():
            return
        
        op_map = {
            "Country": ('countries', self.countries_loaded, self._on_countries_loaded),
            "Language": ('languages', self.languages_loaded, self._on_languages_loaded),
            "Tag": ('tags', self.tags_loaded, self._on_tags_loaded)
        }
        
        if filter_type in op_map:
            op, loaded, callback = op_map[filter_type]
            if not loaded:
                self.status_bar.showMessage(f"Loading {filter_type.lower()}...")
                self._set_buttons_enabled(False)
                self.filter_load_thread = RadioWorker(self.service, op, {})
                self.filter_load_thread.finished.connect(callback)
                self.filter_load_thread.error.connect(self._handle_error)
                self.filter_load_thread.start()
            else:
                self._populate_filter_combo()

    def _on_countries_loaded(self, countries):
        self.filter_widget.set_countries(countries)
        self.countries_loaded = True
        self.status_bar.showMessage(f"Loaded {len(countries)} countries", 3000)
        self._set_buttons_enabled(True)
        self.filter_load_thread = None

    def _on_languages_loaded(self, languages):
        self.filter_widget.set_languages(languages)
        self.languages_loaded = True
        self.status_bar.showMessage(f"Loaded {len(languages)} languages", 3000)
        self._set_buttons_enabled(True)
        self.filter_load_thread = None

    def _on_tags_loaded(self, tags):
        self.filter_widget.set_tags(tags)
        self.tags_loaded = True
        self.status_bar.showMessage(f"Loaded top {len(tags[:250])} tags", 3000)
        self._set_buttons_enabled(True)
        self.filter_load_thread = None

    def _populate_filter_combo(self):
        self.filter_widget._populate_filter_combo()

    def _display_results(self, stations):
        if not stations:
            self.tree_widget.clear()
            self.status_bar.showMessage("No results found")
            self._set_buttons_enabled(True)
            self.search_thread = None
            return
        
        self.tree_widget.display_stations(stations)
        self.status_bar.showMessage(f"Found {len(stations)} stations")
        self._set_buttons_enabled(True)
        self.search_thread = None

    def _display_favorites(self, favorites):
        self.tree_widget.display_favorites(favorites)
        self.status_bar.showMessage(f"Showing {len(favorites)} favorite stations")
        self._set_buttons_enabled(True)
        self.search_thread = None

    def _play_station(self, station_data):
        name = station_data.name if isinstance(station_data, Station) else station_data.get("name", "Unknown")
        url = (station_data.url_resolved or station_data.url) if isinstance(station_data, Station) \
            else (station_data.get("url_resolved") or station_data.get("url", ""))
        
        QMessageBox.information(self, "Play Station",
            f"<b>Playing: {name}</b><br><br>Stream URL: {url}<br><br>"
            "<i>(This is a demo. Integrate with a media player like VLC to play the stream.)</i>")
        self.status_bar.showMessage(f"Playing: {name}")

    def _click_station(self, uuid: str):
        if self.click_thread and self.click_thread.isRunning():
            self.status_bar.showMessage("Click already in progress", 2000)
            return
        
        self.click_thread = RadioWorker(self.service, 'click', {'uuid': uuid})
        self.click_thread.finished.connect(lambda: self.status_bar.showMessage("Click registered successfully", 3000))
        self.click_thread.error.connect(lambda e: self.status_bar.showMessage(f"Click failed: {e}", 4000))
        
        self.click_thread.finished.connect(lambda: setattr(self, 'click_thread', None))
        self.click_thread.error.connect(lambda: setattr(self, 'click_thread', None))
        
        self.click_thread.start()

    def _add_favorite(self, station_data):
        if not isinstance(station_data, Station):
            return
        
        station_dict = {
            "uuid": station_data.uuid,
            "name": station_data.name,
            "url": station_data.url,
            "url_resolved": station_data.url_resolved,
            "country": station_data.country,
            "language": station_data.language,
            "tags": station_data.tags,
            "votes": station_data.votes,
            "codec": station_data.codec,
            "bitrate": station_data.bitrate,
            "homepage": station_data.homepage,
            "favicon": station_data.favicon,
        }
        self.service.add_favorite(station_dict)
        self.status_bar.showMessage(f"Added '{station_data.name}' to favorites")

    def _remove_favorite(self, uuid: str):
        self.service.remove_favorite(uuid)
        self.status_bar.showMessage(f"Removed station from favorites")

    def _show_station_info(self, station_data):
        if isinstance(station_data, Station):
            info = [
                f"<b>Name:</b> {station_data.name}",
                f"<b>Country:</b> {station_data.country or 'N/A'}",
                f"<b>Language:</b> {', '.join(station_data.language) if station_data.language else 'N/A'}",
                f"<b>Tags:</b> {', '.join(station_data.tags) if station_data.tags else 'None'}",
                f"<b>Codec:</b> {station_data.codec or 'N/A'}",
                f"<b>Bitrate:</b> {station_data.bitrate or 'N/A'} kbps",
                f"<b>Votes:</b> {station_data.votes}",
                f"<b>Homepage:</b> {station_data.homepage or 'N/A'}",
            ]
        else:
            info = [
                f"<b>Name:</b> {station_data.get('name', 'Unknown')}",
                f"<b>Country:</b> {station_data.get('country', 'N/A')}",
                f"<b>Language:</b> {', '.join(station_data.get('language', [])) if isinstance(station_data.get('language'), list) else station_data.get('language', 'N/A')}",
                f"<b>Codec:</b> {station_data.get('codec', 'N/A')}",
                f"<b>Bitrate:</b> {station_data.get('bitrate', 'N/A')} kbps",
            ]
        QMessageBox.information(self, "Station Information", "<br>".join(info))

    def _clear_cache(self):
        reply = QMessageBox.question(self, "Clear Cache", "Clear all cached data?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.service.clear_cache()
            self.countries_loaded = False
            self.languages_loaded = False
            self.tags_loaded = False
            self.status_bar.showMessage("Cache cleared successfully", 3000)

    def _handle_error(self, error_msg: str):
        QMessageBox.warning(self, "Error", f"An error occurred:\n{error_msg}")
        self.status_bar.showMessage("Error occurred", 4000)
        self._set_buttons_enabled(True)
        self.filter_load_thread = self.search_thread = None

    def _set_buttons_enabled(self, enabled: bool):
        self.filter_widget.set_buttons_enabled(enabled)

    def closeEvent(self, event):
        for thread in [self.filter_load_thread, self.search_thread, self.click_thread]:
            if thread and thread.isRunning():
                thread.wait()
        event.accept()
