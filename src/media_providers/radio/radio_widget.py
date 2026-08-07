from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from media_providers.radio.radio_browser_types import FilterBy, Station
from media_providers.radio.radio_service import RadioService
from media_providers.radio.radio_worker import RadioWorker
from media_providers.radio.radio_filter_widget import RadioFilterWidget
from media_providers.radio.radio_tree_widget import RadioTreeWidget
from app_constance.styles import RADIO_GROUP_BOX_STYLE


class RadioBrowserWidget(QWidget):
    play_requested = Signal(str)
    
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
        
        results_group = QGroupBox(_("Results"))
        results_group.setStyleSheet(RADIO_GROUP_BOX_STYLE)
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(5, 5, 5, 5)
        
        self.tree_widget = RadioTreeWidget(self)
        results_layout.addWidget(self.tree_widget)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_bar.showMessage(_("Ready - Enter search term or select filters"))

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
        
        self.status_bar.showMessage(
            _("Searching for '{search_name}'...").format(search_name=search_name)
        )
        self._set_buttons_enabled(False)
        
        self.search_thread = RadioWorker(self.service, 'search', params)
        self.search_thread.finished.connect(self._display_results)
        self.search_thread.error.connect(self._handle_error)
        self.search_thread.start()

    def _apply_filter(self, filter_type: str, filter_value: str, params: Dict):
        if self.search_thread and self.search_thread.isRunning():
            return
        
        filter_map = {
            _("Country"): FilterBy.COUNTRY_EXACT,
            _("Language"): FilterBy.LANGUAGE_EXACT,
            _("Tag"): FilterBy.TAG_EXACT,
            _("Codec"): FilterBy.CODEC_EXACT,
        }
        
        self.status_bar.showMessage(
            _("Filtering by {filter_type}: {filter_value}...").format(
                filter_type=filter_type,
                filter_value=filter_value,
            )
        )
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
        
        self.status_bar.showMessage(_("Loading favorites..."))
        self._set_buttons_enabled(False)
        
        self.search_thread = RadioWorker(self.service, 'favorites', {})
        self.search_thread.finished.connect(self._display_favorites)
        self.search_thread.error.connect(self._handle_error)
        self.search_thread.start()

    def _load_filter_data(self, filter_type: str):
        if self.filter_load_thread and self.filter_load_thread.isRunning():
            return
        
        op_map = {
            _("Country"): ('countries', self.countries_loaded, self._on_countries_loaded),
            _("Language"): ('languages', self.languages_loaded, self._on_languages_loaded),
            _("Tag"): ('tags', self.tags_loaded, self._on_tags_loaded),
        }
        
        if filter_type in op_map:
            op, loaded, callback = op_map[filter_type]
            if not loaded:
                self.status_bar.showMessage(
                    _("Loading {filter_type}...").format(
                        filter_type=filter_type.lower()
                    )
                )
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
        self.status_bar.showMessage(
            _("Loaded {count} countries").format(count=len(countries)),
            3000,
        )
        self._set_buttons_enabled(True)
        self.filter_load_thread = None

    def _on_languages_loaded(self, languages):
        self.filter_widget.set_languages(languages)
        self.languages_loaded = True
        self.status_bar.showMessage(
            _("Loaded {count} languages").format(count=len(languages)),
            3000,
        )
        self._set_buttons_enabled(True)
        self.filter_load_thread = None

    def _on_tags_loaded(self, tags):
        self.filter_widget.set_tags(tags)
        self.tags_loaded = True
        self.status_bar.showMessage(
            _("Loaded top {count} tags").format(count=len(tags[:250])),
            3000,
        )
        self._set_buttons_enabled(True)
        self.filter_load_thread = None

    def _populate_filter_combo(self):
        self.filter_widget._populate_filter_combo()

    def _display_results(self, stations):
        if not stations:
            self.tree_widget.clear()
            self.status_bar.showMessage(_("No results found"))
            self._set_buttons_enabled(True)
            self.search_thread = None
            return
        
        self.tree_widget.display_stations(stations)
        self.status_bar.showMessage(
            _("Found {count} stations").format(count=len(stations))
        )
        self._set_buttons_enabled(True)
        self.search_thread = None

    def _display_favorites(self, favorites):
        self.tree_widget.display_favorites(favorites)
        self.status_bar.showMessage(
            _("Showing {count} favorite stations").format(count=len(favorites))
        )
        self._set_buttons_enabled(True)
        self.search_thread = None

    def _play_station(self, station_data):
        name = station_data.name if isinstance(station_data, Station) else station_data.get("name", _("Unknown"))
        url = (station_data.url_resolved or station_data.url) if isinstance(station_data, Station) \
            else (station_data.get("url_resolved") or station_data.get("url", ""))
        
        if url:
            self.play_requested.emit(url)
            self.status_bar.showMessage(_("Playing: {name}").format(name=name))
        else:
            QMessageBox.warning(
                self,
                _("No URL"),
                _("No stream URL found for {name}").format(name=name),
            )

    def _click_station(self, uuid: str):
        if self.click_thread and self.click_thread.isRunning():
            self.status_bar.showMessage(_("Click already in progress"), 2000)
            return
        
        self.click_thread = RadioWorker(self.service, 'click', {'uuid': uuid})
        self.click_thread.finished.connect(
            lambda: self.status_bar.showMessage(_("Click registered successfully"), 3000)
        )
        self.click_thread.error.connect(
            lambda e: self.status_bar.showMessage(
                _("Click failed: {error}").format(error=e),
                4000,
            )
        )
        
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
        self.status_bar.showMessage(
            _("Added '{name}' to favorites").format(name=station_data.name)
        )

    def _remove_favorite(self, uuid: str):
        self.service.remove_favorite(uuid)
        self.status_bar.showMessage(_("Removed station from favorites"))

    def _show_station_info(self, station_data):
        if isinstance(station_data, Station):
            info = [
                _("<b>Name:</b> {name}").format(name=station_data.name),
                _("<b>Country:</b> {country}").format(country=station_data.country or _("N/A")),
                _("<b>Language:</b> {language}").format(
                    language=', '.join(station_data.language) if station_data.language else _("N/A")
                ),
                _("<b>Tags:</b> {tags}").format(
                    tags=', '.join(station_data.tags) if station_data.tags else _("None")
                ),
                _("<b>Codec:</b> {codec}").format(codec=station_data.codec or _("N/A")),
                _("<b>Bitrate:</b> {bitrate} kbps").format(bitrate=station_data.bitrate or _("N/A")),
                _("<b>Votes:</b> {votes}").format(votes=station_data.votes),
                _("<b>Homepage:</b> {homepage}").format(homepage=station_data.homepage or _("N/A")),
            ]
        else:
            info = [
                _("<b>Name:</b> {name}").format(name=station_data.get('name', _("Unknown"))),
                _("<b>Country:</b> {country}").format(country=station_data.get('country', _("N/A"))),
                _("<b>Language:</b> {language}").format(
                    language=', '.join(station_data.get('language', []))
                    if isinstance(station_data.get('language'), list)
                    else station_data.get('language', _("N/A"))
                ),
                _("<b>Codec:</b> {codec}").format(codec=station_data.get('codec', _("N/A"))),
                _("<b>Bitrate:</b> {bitrate} kbps").format(bitrate=station_data.get('bitrate', _("N/A"))),
            ]
        QMessageBox.information(self, _("Station Information"), "<br>".join(info))

    def _clear_cache(self):
        reply = QMessageBox.question(self, _("Clear Cache"), _("Clear all cached data?"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.service.clear_cache()
            self.countries_loaded = False
            self.languages_loaded = False
            self.tags_loaded = False
            self.status_bar.showMessage(_("Cache cleared successfully"), 3000)

    def _handle_error(self, error_msg: str):
        QMessageBox.warning(
            self,
            _("Error"),
            _("An error occurred:\n{error}").format(error=error_msg),
        )
        self.status_bar.showMessage(_("Error occurred"), 4000)
        self._set_buttons_enabled(True)
        self.filter_load_thread = self.search_thread = None

    def _set_buttons_enabled(self, enabled: bool):
        self.filter_widget.set_buttons_enabled(enabled)

    def closeEvent(self, event):
        for thread in [self.filter_load_thread, self.search_thread, self.click_thread]:
            if thread and thread.isRunning():
                thread.wait()
        event.accept()
