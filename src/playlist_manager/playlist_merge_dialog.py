from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
                               QPushButton, QListWidget, QListWidgetItem, QMessageBox)
from PySide6.QtCore import Qt, Signal, Slot
import utilities.mpv_bootstrap
from media_core.av_play import Playlist, PlaylistManager


class PlaylistMergeDialog(QDialog):
    playlists_merged = Signal(str, Playlist)

    def __init__(self, playlist_manager: PlaylistManager, preselected_names=None, parent=None):
        super().__init__(parent)
        self.playlist_manager = playlist_manager
        self.setWindowTitle(_("Merge Playlists"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(420, 380)
        self.setup_ui()
        self.load_playlists(preselected_names or [])

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel(_("Select at least two playlists to merge, in order:")))

        self.playlists_list = QListWidget()
        self.playlists_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.playlists_list)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(_("New playlist name:")))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(_("Enter a name for the merged playlist"))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_button = QPushButton(_("Cancel"))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        merge_button = QPushButton(_("Merge"))
        merge_button.clicked.connect(self.confirm_merge)
        merge_button.setDefault(True)
        buttons_layout.addWidget(merge_button)

        layout.addLayout(buttons_layout)

    def load_playlists(self, preselected_names):
        self.playlists_list.clear()

        for name in self.playlist_manager.list_playlists():
            playlist = self.playlist_manager.get_playlist(name)
            count = len(playlist.entries) if playlist else 0
            item = QListWidgetItem(_("{name} ({count} tracks)").format(name=name, count=count))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if name in preselected_names else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.playlists_list.addItem(item)

        if preselected_names:
            self.name_edit.setText(_("{names} (Merged)").format(names=" + ".join(preselected_names)))

    def _checked_names(self):
        names = []
        for i in range(self.playlists_list.count()):
            item = self.playlists_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                names.append(item.data(Qt.ItemDataRole.UserRole))
        return names

    @Slot()
    def confirm_merge(self):
        selected_names = self._checked_names()
        if len(selected_names) < 2:
            QMessageBox.warning(self, _("Warning"), _("Please select at least two playlists to merge"))
            return

        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, _("Warning"), _("Please enter a name for the merged playlist"))
            self.name_edit.setFocus()
            return

        if name in self.playlist_manager.playlists:
            QMessageBox.warning(
                self, _("Warning"), _("Playlist '{name}' already exists").format(name=name)
            )
            self.name_edit.setFocus()
            return

        source_playlists = [self.playlist_manager.get_playlist(n) for n in selected_names]
        merged = source_playlists[0]
        for playlist in source_playlists[1:]:
            merged = merged.merge(playlist)
        merged.title = name

        self.playlists_merged.emit(name, merged)
        self.accept()
