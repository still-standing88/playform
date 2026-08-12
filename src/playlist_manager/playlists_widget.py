from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QSplitter, QLabel, QMessageBox,
                               QFileDialog, QMenu,
                               QListWidgetItem)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal, Slot
from .playlist_view import PlaylistView
from .playlist_create_dialog import PlaylistCreateDialog
from .playlist_edit_dialog import PlaylistEditDialog
from .playlist_split_dialog import PlaylistSplitDialog
from .playlist_merge_dialog import PlaylistMergeDialog
import utilities.mpv_bootstrap
from media_core.av_play import Playlist, PlaylistManager
import os
import json
import re

from utilities.functions import get_app_path
from utilities import signal_manager


class PlaylistsWidget(QWidget):
    playlist_selected = Signal(Playlist)
    SUPPORTED_PLAYLIST_EXTENSIONS = {".json", ".m3u", ".m3u8", ".pls", ".xspf"}
    PLAYLIST_FILE_FILTER = _("Playlist Files (*.json *.m3u *.m3u8 *.pls *.xspf);;All Files (*)")
    
    def __init__(self, parent=None, play_callback=None):
        super().__init__(parent)
        self.play_callback = play_callback
        self.playlist_manager = PlaylistManager()
        self.playlist_paths = {}
        self.setup_ui()
        self.setup_playlists_context_menu()
        self.setup_data_paths()
        self.load_playlists_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(_("Playlists")))
        header_layout.addStretch()
        
        self.create_button = QPushButton(_("Create Playlist"))
        self.create_button.clicked.connect(self.create_playlist)
        header_layout.addWidget(self.create_button)

        self.import_button = QPushButton(_("Import Playlist"))
        self.import_button.clicked.connect(self.import_playlist)
        header_layout.addWidget(self.import_button)
        
        layout.addLayout(header_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.playlists_list = QListWidget()
        self.playlists_list.setMaximumWidth(250)
        self.playlists_list.currentItemChanged.connect(self.on_current_playlist_changed)
        self.playlists_list.itemDoubleClicked.connect(self.edit_playlist)
        self.playlists_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlists_list.customContextMenuRequested.connect(self.show_playlists_context_menu)
        splitter.addWidget(self.playlists_list)
        
        self.playlist_view = PlaylistView(
            play_callback=self.play_callback,
            playlist_changed_callback=self.persist_current_playlist
        )
        splitter.addWidget(self.playlist_view)
        
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
    def setup_data_paths(self):
        app_dir = get_app_path()
        self.data_dir = os.path.join(app_dir, "data")
        self.playlists_dir = os.path.join(self.data_dir, "playlists")
        self.playlists_json_path = os.path.join(self.data_dir, "playlists.json")
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.playlists_dir, exist_ok=True)

    def setup_playlists_context_menu(self):
        self.playlists_context_menu = QMenu(self)

        self.rename_playlist_action = QAction(_("Rename"), self)
        self.rename_playlist_action.triggered.connect(self.rename_current_playlist)
        self.playlists_context_menu.addAction(self.rename_playlist_action)

        self.delete_playlist_action = QAction(_("Delete"), self)
        self.delete_playlist_action.triggered.connect(self.delete_current_playlist)
        self.playlists_context_menu.addAction(self.delete_playlist_action)

        self.playlists_context_menu.addSeparator()

        self.split_playlist_action = QAction(_("Split Playlist..."), self)
        self.split_playlist_action.triggered.connect(self.split_current_playlist)
        self.playlists_context_menu.addAction(self.split_playlist_action)

        self.merge_playlists_action = QAction(_("Merge Playlists..."), self)
        self.merge_playlists_action.triggered.connect(self.merge_playlists)
        self.playlists_context_menu.addAction(self.merge_playlists_action)

    @Slot(object)
    def show_playlists_context_menu(self, position):
        item = self.playlists_list.itemAt(position)
        if item is not None:
            self.playlists_list.setCurrentItem(item)

        has_playlist = item is not None
        has_multiple = self.playlists_list.count() >= 2

        self.rename_playlist_action.setEnabled(has_playlist)
        self.delete_playlist_action.setEnabled(has_playlist)
        self.split_playlist_action.setEnabled(has_playlist)
        self.merge_playlists_action.setEnabled(has_multiple)

        global_pos = self.playlists_list.viewport().mapToGlobal(position)
        self.playlists_context_menu.exec(global_pos)

    @Slot()
    def rename_current_playlist(self):
        item = self.playlists_list.currentItem()
        if item is not None:
            self.edit_playlist(item)

    @Slot()
    def delete_current_playlist(self):
        item = self.playlists_list.currentItem()
        if item is None:
            return

        name = item.text()
        reply = QMessageBox.question(
            self,
            _("Confirm"),
            _("Delete playlist '{name}'? This cannot be undone.").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        file_path = self.playlist_paths.get(name)
        self._remove_playlist_entry(name)

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        if self.playlists_list.count():
            if self.playlists_list.currentItem() is None:
                self.playlists_list.setCurrentRow(0)
        else:
            self.playlist_view.set_playlist(None)

        self.save_playlists_data()
        signal_manager.statusbar_message.emit(
            _("Deleted playlist '{name}'").format(name=name)
        )

    @Slot()
    def split_current_playlist(self):
        item = self.playlists_list.currentItem()
        if item is None:
            return

        name = item.text()
        playlist = self.playlist_manager.get_playlist(name)
        if playlist is None:
            return

        if len(playlist.entries) < 2:
            QMessageBox.information(
                self,
                _("Split Playlist"),
                _("Playlist '{name}' needs at least 2 tracks to split.").format(name=name),
            )
            return

        dialog = PlaylistSplitDialog(name, playlist, self)
        dialog.playlist_split.connect(self.on_playlist_split)
        dialog.exec()

    @Slot(str, list)
    def on_playlist_split(self, source_name, named_parts):
        added_names = []
        for name, playlist in named_parts:
            unique_name = self._ensure_unique_playlist_name(name)
            self.playlist_manager.playlists[unique_name] = playlist
            self.playlist_paths[unique_name] = self._default_playlist_path(unique_name)
            self.add_playlist_to_list(unique_name)
            added_names.append(unique_name)

        if not added_names:
            return

        self.save_playlists_data()
        signal_manager.statusbar_message.emit(
            _("Split '{name}' into {count} playlists").format(
                name=source_name, count=len(added_names)
            )
        )

        for i in range(self.playlists_list.count()):
            if self.playlists_list.item(i).text() == added_names[0]:
                self.playlists_list.setCurrentRow(i)
                break

    @Slot()
    def merge_playlists(self):
        if self.playlists_list.count() < 2:
            QMessageBox.information(
                self,
                _("Merge Playlists"),
                _("You need at least two playlists to merge."),
            )
            return

        current_item = self.playlists_list.currentItem()
        preselected = [current_item.text()] if current_item else []

        dialog = PlaylistMergeDialog(self.playlist_manager, preselected, self)
        dialog.playlists_merged.connect(self.on_playlist_created)
        dialog.exec()

    def _safe_playlist_filename(self, name):
        safe_name = re.sub(r'[<>:"/\\\\|?*]+', "_", name).strip().strip(".")
        return safe_name or "playlist"

    def _default_playlist_path(self, name, extension=".json"):
        return os.path.join(
            self.playlists_dir, f"{self._safe_playlist_filename(name)}{extension}"
        )

    def _load_playlist_from_path(self, name, file_path):
        playlist = self.playlist_manager.load_playlist(name, file_path)
        playlist.title = name
        self.playlist_paths[name] = file_path
        if not any(self.playlists_list.item(i).text() == name for i in range(self.playlists_list.count())):
            self.add_playlist_to_list(name)
        self._update_playlist_list_item(name)
        return playlist

    def _update_playlist_list_item(self, name):
        for i in range(self.playlists_list.count()):
            item = self.playlists_list.item(i)
            if item.text() == name:
                file_path = self.playlist_paths.get(name, "")
                item.setToolTip(file_path)
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                break

    def _ensure_unique_playlist_name(self, base_name):
        if base_name not in self.playlist_manager.playlists:
            return base_name

        suffix = 2
        while f"{base_name} ({suffix})" in self.playlist_manager.playlists:
            suffix += 1
        return f"{base_name} ({suffix})"

    def _remove_playlist_entry(self, name):
        self.playlist_manager.remove_playlist(name)
        self.playlist_paths.pop(name, None)

        for i in range(self.playlists_list.count()):
            item = self.playlists_list.item(i)
            if item.text() == name:
                self.playlists_list.takeItem(i)
                break

    def _confirm_remove_missing_playlist(self, name, file_path):
        reply = QMessageBox.question(
            self,
            _("Missing Playlist"),
            _(
                "Playlist '{name}' could not be found at:\n{path}\n\nRemove it from the playlist list?"
            ).format(name=name, path=file_path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._remove_playlist_entry(name)
            self.save_playlists_data()
            signal_manager.statusbar_message.emit(
                _("Removed missing playlist '{name}'").format(name=name)
            )
            return True
        return False
        
    def load_playlists_data(self):
        loaded_paths = set()

        try:
            from app_db import app_settings
            from app_db.settings_store import migrate_json_file
            data = migrate_json_file(app_settings, self.playlists_json_path, "playlists_registry", default={})
        except Exception as e:
            print(f"Error loading playlists registry: {e}")
            data = {}

        if data:
            try:
                for playlist_info in data.get("playlists", []):
                    name = playlist_info.get("name")
                    file_path = playlist_info.get("file_path")

                    if not name or not file_path:
                        continue

                    if not os.path.exists(file_path):
                        self.playlist_paths[name] = file_path
                        self.add_playlist_to_list(name)
                        self._update_playlist_list_item(name)
                        self._confirm_remove_missing_playlist(name, file_path)
                        continue

                    try:
                        self._load_playlist_from_path(name, file_path)
                        loaded_paths.add(os.path.normcase(os.path.abspath(file_path)))
                    except Exception as e:
                        print(f"Error loading playlist {name}: {e}")
                            
            except Exception as e:
                print(f"Error loading playlists data: {e}")

        try:
            for filename in sorted(os.listdir(self.playlists_dir)):
                file_path = os.path.join(self.playlists_dir, filename)
                if not os.path.isfile(file_path):
                    continue
                extension = os.path.splitext(filename)[1].lower()
                if extension not in self.SUPPORTED_PLAYLIST_EXTENSIONS:
                    continue

                normalized_path = os.path.normcase(os.path.abspath(file_path))
                if normalized_path in loaded_paths:
                    continue

                name = os.path.splitext(filename)[0]
                if name in self.playlist_manager.playlists:
                    suffix = 2
                    base_name = name
                    while f"{base_name} ({suffix})" in self.playlist_manager.playlists:
                        suffix += 1
                    name = f"{base_name} ({suffix})"

                try:
                    self._load_playlist_from_path(name, file_path)
                    loaded_paths.add(normalized_path)
                except Exception as e:
                    print(f"Error loading playlist {name} from folder: {e}")
        except Exception as e:
            print(f"Error scanning playlists folder: {e}")

        if self.playlists_list.count() and self.playlists_list.currentItem() is None:
            self.playlists_list.setCurrentRow(0)
                
    def save_playlists_data(self):
        try:
            playlists_data = []
            
            for i in range(self.playlists_list.count()):
                item = self.playlists_list.item(i)
                name = item.text()
                playlist = self.playlist_manager.get_playlist(name)
                
                if playlist is not None:
                    file_path = self.playlist_paths.get(name) or self._default_playlist_path(name)
                    self.playlist_paths[name] = file_path
                    self.playlist_manager.save_playlist(name, file_path)
                    
                    playlist_info = {
                        "name": name,
                        "file_path": file_path
                    }
                    playlists_data.append(playlist_info)
                    
            data = {"playlists": playlists_data}

            from app_db import app_settings
            app_settings.set("playlists_registry", data)

        except Exception as e:
            print(f"Error saving playlists data: {e}")

    def persist_playlist(self, name):
        playlist = self.playlist_manager.get_playlist(name)
        if playlist is None:
            return

        file_path = self.playlist_paths.get(name) or self._default_playlist_path(name)
        self.playlist_paths[name] = file_path

        try:
            playlist.save(file_path)
        except Exception:
            self.playlist_manager.save_playlist(name, file_path)

        self.save_playlists_data()

    def persist_current_playlist(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            self.persist_playlist(current_item.text())
            
    def add_playlist_to_list(self, name):
        item = QListWidgetItem(name)
        self.playlists_list.addItem(item)
        self._update_playlist_list_item(name)

    @Slot()
    def import_playlist(self):
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self,
            _("Import Playlist"),
            "",
            self.PLAYLIST_FILE_FILTER,
        )
        if not file_path:
            return

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        name = self._ensure_unique_playlist_name(base_name)

        try:
            playlist = self._load_playlist_from_path(name, file_path)
        except Exception as e:
            QMessageBox.warning(
                self,
                _("Import Failed"),
                _("Could not import playlist:\n{path}\n\n{error}").format(
                    path=file_path,
                    error=e,
                ),
            )
            return

        self.save_playlists_data()
        signal_manager.statusbar_message.emit(
            _("Imported playlist '{name}'").format(name=name)
        )

        for i in range(self.playlists_list.count()):
            if self.playlists_list.item(i).text() == name:
                self.playlists_list.setCurrentRow(i)
                break
        
    @Slot()
    def create_playlist(self):
        dialog = PlaylistCreateDialog(self)
        dialog.playlist_created.connect(self.on_playlist_created)
        dialog.exec()
        
    @Slot(str, object)
    def on_playlist_created(self, name, playlist):
        if name in [self.playlists_list.item(i).text() for i in range(self.playlists_list.count())]:
            QMessageBox.warning(
                self,
                _("Warning"),
                _("Playlist '{name}' already exists").format(name=name),
            )
            return
            
        self.playlist_manager.playlists[name] = playlist
        self.playlist_paths[name] = self._default_playlist_path(name)
        self.add_playlist_to_list(name)
        self.save_playlists_data()
        signal_manager.statusbar_message.emit(
            _("Playlist '{name}' created").format(name=name)
        )
        
        for i in range(self.playlists_list.count()):
            if self.playlists_list.item(i).text() == name:
                self.playlists_list.setCurrentRow(i)
                self.on_playlist_selected(self.playlists_list.item(i))
                break
                
    @Slot(object)
    def edit_playlist(self, item):
        name = item.text()
        playlist = self.playlist_manager.get_playlist(name)
        
        if playlist is not None:
            dialog = PlaylistEditDialog(name, playlist, self)
            dialog.playlist_updated.connect(self.on_playlist_updated)
            dialog.exec()
            
    @Slot(str, str)
    def on_playlist_updated(self, old_name, new_name):
        if old_name != new_name:
            if new_name in [self.playlists_list.item(i).text() for i in range(self.playlists_list.count())]:
                QMessageBox.warning(
                    self,
                    _("Warning"),
                    _("Playlist '{new_name}' already exists").format(
                        new_name=new_name
                    ),
                )
                return
                
            playlist = self.playlist_manager.get_playlist(old_name)
            if playlist is not None:
                self.playlist_manager.playlists[new_name] = playlist
                del self.playlist_manager.playlists[old_name]
                old_path = self.playlist_paths.pop(old_name, None)
                extension = os.path.splitext(old_path)[1] if old_path else ".json"
                new_path = self._default_playlist_path(new_name, extension or ".json")
                if old_path and os.path.exists(old_path) and not os.path.exists(new_path):
                    try:
                        os.replace(old_path, new_path)
                    except OSError:
                        new_path = old_path
                elif old_path and not os.path.exists(old_path):
                    new_path = old_path
                self.playlist_paths[new_name] = new_path
                
                for i in range(self.playlists_list.count()):
                    if self.playlists_list.item(i).text() == old_name:
                        self.playlists_list.item(i).setText(new_name)
                        break
                self._update_playlist_list_item(new_name)
                        
        self.save_playlists_data()
        signal_manager.statusbar_message.emit(
            _("Playlist '{new_name}' updated").format(new_name=new_name)
        )
        
    @Slot(object, object)
    def on_current_playlist_changed(self, current, previous):
        if previous is not None:
            self.persist_playlist(previous.text())
        self.on_playlist_selected(current)

    @Slot(object)
    def on_playlist_selected(self, item):
        if item is None:
            self.playlist_view.set_playlist(None)
            return

        name = item.text()
        file_path = self.playlist_paths.get(name)
        playlist = self.playlist_manager.get_playlist(name)

        if file_path and not os.path.exists(file_path):
            if self._confirm_remove_missing_playlist(name, file_path):
                self.playlist_view.set_playlist(None)
            return

        if file_path and os.path.exists(file_path):
            try:
                playlist = self._load_playlist_from_path(name, file_path)
            except Exception as e:
                print(f"Error reloading playlist {name}: {e}")
                self.playlist_view.set_playlist(None)
                return

        if playlist is not None:
            self.playlist_view.set_playlist(playlist)
            self.playlist_selected.emit(playlist)
        else:
            self.playlist_view.set_playlist(None)
                
    def get_current_playlist(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            name = current_item.text()
            return self.playlist_manager.get_playlist(name)
        return None
        
    def refresh_current_playlist(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            self.on_playlist_selected(current_item)
