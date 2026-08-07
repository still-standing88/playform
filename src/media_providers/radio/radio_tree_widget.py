from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QApplication, QHeaderView
from PySide6.QtCore import Qt, Signal
from media_providers.radio.radio_browser_types import Station
from app_constance.styles import RADIO_TREE_STYLE


class RadioTreeWidget(QTreeWidget):
    play_requested = Signal(object)
    click_requested = Signal(str)
    favorite_added = Signal(object)
    favorite_removed = Signal(str)
    info_requested = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_stations: List[Station] = []
        self._setup_ui()
        
    def _setup_ui(self):
        self.setColumnCount(5)
        self.setHeaderLabels([_("Name"), _("Country"), _("Language(s)"), _("Codec"), _("Bitrate")])
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setStyleSheet(RADIO_TREE_STYLE)
        
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionsMovable(False)
        header.setSectionsClickable(False)
        
        self.setAccessibleName(_("Radio stations list"))
        self.setAccessibleDescription(_("List of radio stations. Right-click or double-click for options."))
        
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def display_stations(self, stations: List[Station]) -> None:
        self.clear()
        self.current_stations = stations
        
        for station in stations:
            item = QTreeWidgetItem(self)
            lang_str = ", ".join(station.language) if station.language else ""
            
            item.setText(0, station.name)
            item.setText(1, station.country or "")
            item.setText(2, lang_str)
            item.setText(3, station.codec or "")
            item.setText(4, str(station.bitrate) if station.bitrate else "")
            item.setData(0, Qt.ItemDataRole.UserRole, station)
            
            tags_str = ", ".join(station.tags) if station.tags else _("None")
            desc = _(
                "Station: {name}. Country: {country}. Language: {language}. Tags: {tags}. Codec: {codec}. Bitrate: {bitrate}."
            ).format(
                name=station.name,
                country=station.country or _("N/A"),
                language=lang_str or _("N/A"),
                tags=tags_str,
                codec=station.codec or _("N/A"),
                bitrate=station.bitrate or _("N/A"),
            )
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            self.addTopLevelItem(item)

    def display_favorites(self, favorites: List[Dict[str, Any]]) -> None:
        self.clear()
        self.current_stations = []
        
        for fav in favorites:
            item = QTreeWidgetItem(self)
            
            lang_data = fav.get("language", [])
            lang_str = ", ".join(lang_data) if isinstance(lang_data, list) else str(lang_data)
            
            item.setText(0, fav.get("name", _("Unknown")))
            item.setText(1, fav.get("country", ""))
            item.setText(2, lang_str)
            item.setText(3, fav.get("codec", ""))
            item.setText(4, str(fav.get("bitrate", "")))
            item.setData(0, Qt.ItemDataRole.UserRole, fav)
            
            desc = _("Favorite Station: {name}. Country: {country}. Language: {language}.").format(
                name=fav.get("name", _("Unknown")),
                country=fav.get("country", _("N/A")),
                language=lang_str or _("N/A"),
            )
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            self.addTopLevelItem(item)

    def _show_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return
        
        station_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not station_data:
            return

        uuid = station_data.uuid if isinstance(station_data, Station) else station_data.get("uuid")
        if not uuid:
            return
        
        menu = QMenu(self)
        
        play_action = menu.addAction(_("Play Station"))
        play_action.triggered.connect(lambda: self.play_requested.emit(station_data))
        
        click_action = menu.addAction(_("Register Click"))
        click_action.triggered.connect(lambda: self.click_requested.emit(uuid))
        
        menu.addSeparator()
        
        is_fav = self._is_favorite_item(station_data)
        if is_fav:
            fav_action = menu.addAction(_("Remove from Favorites"))
            fav_action.triggered.connect(lambda: self.favorite_removed.emit(uuid))
        else:
            fav_action = menu.addAction(_("Add to Favorites"))
            fav_action.triggered.connect(lambda: self.favorite_added.emit(station_data))
        
        menu.addSeparator()
        
        info_action = menu.addAction(_("Station Information"))
        info_action.triggered.connect(lambda: self.info_requested.emit(station_data))
        
        copy_action = menu.addAction(_("Copy Stream URL"))
        copy_action.triggered.connect(lambda: self._copy_url(station_data))
        
        menu.exec(self.viewport().mapToGlobal(position))

    def _on_item_double_clicked(self, item, column):
        station_data = item.data(0, Qt.ItemDataRole.UserRole)
        if station_data:
            self.play_requested.emit(station_data)

    def _is_favorite_item(self, station_data) -> bool:
        return not isinstance(station_data, Station)

    def _copy_url(self, station_data):
        url = (station_data.url_resolved or station_data.url) if isinstance(station_data, Station) \
            else (station_data.get("url_resolved") or station_data.get("url", ""))
        if url:
            QApplication.clipboard().setText(url)

    def get_station_count(self) -> int:
        return self.topLevelItemCount()
