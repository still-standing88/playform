from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QCheckBox,
                               QSpinBox, QTextEdit, QLineEdit, QPushButton,
                               QHBoxLayout, QFileDialog, QMessageBox, QGroupBox,
                               QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt
from utilities.functions import is_valid_mpv_options

class AdvancedPanel(QWidget):
    # Each entry: (settings key, dialog kind). dialog kind "file" ->
    # QFileDialog.getOpenFileName, "dir" -> getExistingDirectory. Display
    # labels are built in setup_ui() (via _path_labels) so _() resolves
    # after translations are installed, not at class-definition time.
    PATH_ENTRIES = [
        ("youtube_cookies", "file"),
        ("yt-dlp_path", "dir"),
        ("ffmpeg_path", "dir"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        # Labels built lazily in setup_ui() so _() is resolved after
        # translations are installed, not at class-definition time.
        self._path_values = {"youtube_cookies": "", "yt-dlp_path": "", "ffmpeg_path": ""}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        mpv_group = QGroupBox(_("MPV Settings"))
        mpv_group.setObjectName("mpvGroupBox")
        mpv_layout = QFormLayout(mpv_group)

        self.mpv_logging_check = QCheckBox(_("Enable MPV Logging"))
        self.mpv_logging_check.toggled.connect(self.toggle_mpv_logging_options)
        mpv_layout.addRow(_("MPV Logging:"), self.mpv_logging_check)

        self.debug_level_spin = QSpinBox()
        self.debug_level_spin.setRange(0, 2)
        mpv_layout.addRow(_("Debug Level:"), self.debug_level_spin)
        self.debug_level_row = mpv_layout.rowCount() - 1

        self.mpv_options_edit = QTextEdit()
        self.mpv_options_edit.setMaximumHeight(100)
        self.mpv_options_edit.setTabChangesFocus(True)

        original_focus_out = self.mpv_options_edit.focusOutEvent
        def custom_focus_out(e):
            self.validate_mpv_options()
            original_focus_out(e)
        self.mpv_options_edit.focusOutEvent = custom_focus_out

        mpv_layout.addRow(_("Extra MPV Options:"), self.mpv_options_edit)

        layout.addWidget(mpv_group)

        ytdlp_group = QGroupBox(_("yt-dlp Settings"))
        self.ytdlp_layout = QFormLayout(ytdlp_group)

        # One shared path field + Browse button, driven by whichever entry
        # is selected in the list -- replaces three near-identical
        # edit+browse rows (cookies file / yt-dlp path / ffmpeg path).
        self._path_labels = {
            "youtube_cookies": _("YouTube Cookies File"),
            "yt-dlp_path": _("yt-dlp Path"),
            "ffmpeg_path": _("FFmpeg Path"),
        }

        self.path_list = QListWidget()
        self.path_list.setMaximumHeight(90)
        self.path_list.setAccessibleName(_("Path setting to edit"))
        for key, _kind in self.PATH_ENTRIES:
            item = QListWidgetItem(self._path_labels[key])
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.path_list.addItem(item)
        self.path_list.currentItemChanged.connect(self._on_path_selection_changed)
        self.ytdlp_layout.addRow(_("Path Setting:"), self.path_list)

        path_row = QWidget()
        path_row_layout = QHBoxLayout(path_row)
        path_row_layout.setContentsMargins(0, 0, 0, 0)
        self.path_value_edit = QLineEdit()
        self.path_value_edit.setReadOnly(True)
        self.path_browse_btn = QPushButton(_("Browse"))
        self.path_browse_btn.clicked.connect(self.browse_selected_path)
        path_row_layout.addWidget(self.path_value_edit)
        path_row_layout.addWidget(self.path_browse_btn)
        self.ytdlp_layout.addRow(_("Path:"), path_row)

        self.ytdlp_logging_check = QCheckBox(_("Enable yt-dlp Logging"))
        self.ytdlp_logging_check.toggled.connect(self.toggle_ytdlp_logging_options)
        self.ytdlp_layout.addRow(_("yt-dlp Logging:"), self.ytdlp_logging_check)

        self.ytdlp_verbose_check = QCheckBox(_("Enable Verbose Output"))
        self.ytdlp_layout.addRow(_("Verbose Output:"), self.ytdlp_verbose_check)
        self.ytdlp_verbose_row = self.ytdlp_layout.rowCount() - 1

        layout.addWidget(ytdlp_group)
        layout.addStretch()

        self.path_list.setCurrentRow(0)

    def toggle_mpv_logging_options(self, checked):
        mpv_group = self.findChild(QGroupBox, "mpvGroupBox")
        if mpv_group:
            mpv_layout = mpv_group.findChild(QFormLayout)
            if mpv_layout:
                label_item = mpv_layout.itemAt(self.debug_level_row, QFormLayout.ItemRole.LabelRole)
                field_item = mpv_layout.itemAt(self.debug_level_row, QFormLayout.ItemRole.FieldRole)
                if label_item and label_item.widget():
                    label_item.widget().setVisible(checked)
                if field_item and field_item.widget():
                    field_item.widget().setVisible(checked)

    def toggle_ytdlp_logging_options(self, checked):
        label_item = self.ytdlp_layout.itemAt(self.ytdlp_verbose_row, QFormLayout.ItemRole.LabelRole)
        field_item = self.ytdlp_layout.itemAt(self.ytdlp_verbose_row, QFormLayout.ItemRole.FieldRole)
        if label_item and label_item.widget():
            label_item.widget().setVisible(checked)
        if field_item and field_item.widget():
            field_item.widget().setVisible(checked)

    def validate_mpv_options(self):
        text = self.mpv_options_edit.toPlainText().strip()
        if text and not is_valid_mpv_options(text):
            QMessageBox.warning(self, _("Invalid MPV Options"),
                              _("The MPV options are not valid. Please check the syntax."))
            self.mpv_options_edit.setFocus()
            return False
        return True

    def _selected_path_key(self):
        item = self.path_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_path_selection_changed(self, current, previous):
        key = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.path_value_edit.setText(self._path_values.get(key, "") if key else "")

    def _dialog_kind_for(self, key):
        for entry_key, kind in self.PATH_ENTRIES:
            if entry_key == key:
                return kind
        return "dir"

    def browse_selected_path(self):
        key = self._selected_path_key()
        if not key:
            return

        if self._dialog_kind_for(key) == "file":
            path, __ = QFileDialog.getOpenFileName(self, _("Select Cookies File"),
                                                     "", "Text Files (*.txt);;All Files (*)")
        else:
            path = QFileDialog.getExistingDirectory(self, _("Select Directory"))

        if path:
            self._path_values[key] = path
            self.path_value_edit.setText(path)

    def load_settings(self, prefs):
        self.mpv_logging_check.setChecked(prefs["mpv_logging"])
        self.debug_level_spin.setValue(prefs["debug_level"])
        self.mpv_options_edit.setPlainText(prefs["mpv_extra_options"])

        self._path_values["youtube_cookies"] = prefs["youtube_cookies"]
        self._path_values["yt-dlp_path"] = prefs["yt-dlp_path"]
        self._path_values["ffmpeg_path"] = prefs["ffmpeg_path"]
        self._on_path_selection_changed(self.path_list.currentItem(), None)

        self.ytdlp_logging_check.setChecked(prefs["yt-dlp_logging"])
        self.ytdlp_verbose_check.setChecked(prefs["yt-dlp_verbose_output"])

        self.toggle_mpv_logging_options(prefs["mpv_logging"])
        self.toggle_ytdlp_logging_options(prefs["yt-dlp_logging"])

    def save_settings(self, prefs):
        prefs["mpv_logging"] = self.mpv_logging_check.isChecked()
        prefs["debug_level"] = self.debug_level_spin.value()
        prefs["mpv_extra_options"] = self.mpv_options_edit.toPlainText().strip()
        prefs["youtube_cookies"] = self._path_values["youtube_cookies"]
        prefs["yt-dlp_path"] = self._path_values["yt-dlp_path"]
        prefs["ffmpeg_path"] = self._path_values["ffmpeg_path"]
        prefs["yt-dlp_logging"] = self.ytdlp_logging_check.isChecked()
        prefs["yt-dlp_verbose_output"] = self.ytdlp_verbose_check.isChecked()
