from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QRadioButton, QSpinBox, QMessageBox, QButtonGroup)
from PySide6.QtCore import Qt, Signal, Slot
import utilities.mpv_bootstrap
from media_core.av_play import Playlist


class PlaylistSplitDialog(QDialog):
    playlist_split = Signal(str, list)  # source_name, [(name, Playlist), ...]

    def __init__(self, name, playlist: Playlist, parent=None):
        super().__init__(parent)
        self.source_name = name
        self.playlist = playlist
        self.setWindowTitle(_("Split Playlist"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(420, 240)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        track_count = len(self.playlist.entries)
        layout.addWidget(QLabel(
            _("Split '{name}' ({count} tracks) into new playlists:").format(
                name=self.source_name, count=track_count
            )
        ))

        self.mode_group = QButtonGroup(self)

        at_track_layout = QHBoxLayout()
        self.at_track_radio = QRadioButton(_("Split after track:"))
        self.at_track_radio.setChecked(True)
        self.mode_group.addButton(self.at_track_radio)
        at_track_layout.addWidget(self.at_track_radio)
        self.split_index_spin = QSpinBox()
        self.split_index_spin.setMinimum(1)
        self.split_index_spin.setMaximum(max(1, track_count - 1))
        self.split_index_spin.valueChanged.connect(self.update_preview)
        at_track_layout.addWidget(self.split_index_spin)
        at_track_layout.addStretch()
        layout.addLayout(at_track_layout)

        parts_layout = QHBoxLayout()
        self.parts_radio = QRadioButton(_("Split into equal parts:"))
        self.mode_group.addButton(self.parts_radio)
        parts_layout.addWidget(self.parts_radio)
        self.num_parts_spin = QSpinBox()
        self.num_parts_spin.setMinimum(2)
        self.num_parts_spin.setMaximum(max(2, track_count))
        self.num_parts_spin.valueChanged.connect(self.update_preview)
        parts_layout.addWidget(self.num_parts_spin)
        parts_layout.addStretch()
        layout.addLayout(parts_layout)

        self.at_track_radio.toggled.connect(self.update_preview)

        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: gray;")
        layout.addWidget(self.preview_label)

        layout.addStretch()

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_button = QPushButton(_("Cancel"))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        self.split_button = QPushButton(_("Split"))
        self.split_button.clicked.connect(self.confirm_split)
        self.split_button.setDefault(True)
        buttons_layout.addWidget(self.split_button)

        layout.addLayout(buttons_layout)

        if track_count < 2:
            self.at_track_radio.setEnabled(False)
            self.parts_radio.setEnabled(False)
            self.split_index_spin.setEnabled(False)
            self.num_parts_spin.setEnabled(False)
            self.split_button.setEnabled(False)
            self.preview_label.setText(_("This playlist needs at least 2 tracks to split."))
        else:
            self.update_preview()

    @Slot()
    def update_preview(self):
        track_count = len(self.playlist.entries)
        if track_count < 2:
            return

        if self.at_track_radio.isChecked():
            split_at = self.split_index_spin.value()
            self.preview_label.setText(
                _("Part 1: tracks 1-{a}\nPart 2: tracks {b}-{c}").format(
                    a=split_at, b=split_at + 1, c=track_count
                )
            )
        else:
            num_parts = self.num_parts_spin.value()
            parts = self.playlist.split_into_parts(num_parts)
            sizes = ", ".join(str(len(part.entries)) for part in parts)
            self.preview_label.setText(
                _("{count} parts with track counts: {sizes}").format(count=len(parts), sizes=sizes)
            )

    @Slot()
    def confirm_split(self):
        track_count = len(self.playlist.entries)
        if track_count < 2:
            return

        if self.at_track_radio.isChecked():
            parts = self.playlist.split([self.split_index_spin.value()])
        else:
            parts = self.playlist.split_into_parts(self.num_parts_spin.value())

        if len(parts) < 2:
            QMessageBox.warning(
                self, _("Warning"), _("Could not split the playlist with the current settings")
            )
            return

        named_parts = [(f"{self.source_name} - Part {i + 1}", part) for i, part in enumerate(parts)]
        self.playlist_split.emit(self.source_name, named_parts)
        self.accept()
