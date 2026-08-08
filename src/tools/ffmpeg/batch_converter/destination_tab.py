from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup, QLineEdit,
    QPushButton, QCheckBox, QFileDialog, QGroupBox
)


class DestinationTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.mode_group = QButtonGroup(self)
        self.original_folder_radio = QRadioButton(_("Store all files in their original folders"), self)
        self.target_folder_radio = QRadioButton(_("Store all files in this folder:"), self)
        self.original_folder_radio.setChecked(True)
        self.mode_group.addButton(self.original_folder_radio, 0)
        self.mode_group.addButton(self.target_folder_radio, 1)
        layout.addWidget(self.original_folder_radio)
        layout.addWidget(self.target_folder_radio)

        target_row = QHBoxLayout()
        self.target_path_edit = QLineEdit(self)
        self.target_path_edit.setAccessibleName(_("Destination folder path"))
        self.target_browse_button = QPushButton(_("Browse..."), self)
        target_row.addWidget(self.target_path_edit)
        target_row.addWidget(self.target_browse_button)
        layout.addLayout(target_row)

        self.preserve_subfolders_check = QCheckBox(_("Preserve subfolder structure"), self)
        layout.addWidget(self.preserve_subfolders_check)

        options_group = QGroupBox(_("Options"), self)
        options_layout = QVBoxLayout(options_group)
        self.overwrite_check = QCheckBox(_("Overwrite existing files (not recommended)"), self)
        self.delete_originals_check = QCheckBox(_("Delete original files (not recommended)"), self)
        self.create_log_check = QCheckBox(_("Create log file"), self)
        options_layout.addWidget(self.overwrite_check)
        options_layout.addWidget(self.delete_originals_check)
        options_layout.addWidget(self.create_log_check)

        log_row = QHBoxLayout()
        self.log_path_edit = QLineEdit(self)
        self.log_path_edit.setReadOnly(True)
        self.log_path_edit.setAccessibleName(_("Log file path"))
        self.set_log_file_button = QPushButton(_("Set Log File..."), self)
        log_row.addWidget(self.log_path_edit)
        log_row.addWidget(self.set_log_file_button)
        options_layout.addLayout(log_row)
        layout.addWidget(options_group)
        layout.addStretch()

        self.target_browse_button.clicked.connect(self._browse_target_folder)
        self.set_log_file_button.clicked.connect(self._browse_log_file)
        self.target_folder_radio.toggled.connect(self._update_enabled_state)
        self.create_log_check.toggled.connect(self._update_enabled_state)
        self._update_enabled_state()

    def _update_enabled_state(self):
        target_mode = self.target_folder_radio.isChecked()
        self.target_path_edit.setEnabled(target_mode)
        self.target_browse_button.setEnabled(target_mode)
        self.preserve_subfolders_check.setEnabled(target_mode)
        self.log_path_edit.setEnabled(self.create_log_check.isChecked())
        self.set_log_file_button.setEnabled(self.create_log_check.isChecked())

    def _browse_target_folder(self):
        directory = QFileDialog.getExistingDirectory(self, _("Select Destination Folder"), self.target_path_edit.text())
        if directory:
            self.target_path_edit.setText(directory)

    def _browse_log_file(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Select Log File"), self.log_path_edit.text(), "*.log")
        if path:
            self.log_path_edit.setText(path)

    def selected_options(self) -> dict:
        return {
            "store_in_original_folder": self.original_folder_radio.isChecked(),
            "target_folder": self.target_path_edit.text().strip(),
            "preserve_subfolders": self.preserve_subfolders_check.isChecked(),
            "overwrite_existing": self.overwrite_check.isChecked(),
            "delete_originals": self.delete_originals_check.isChecked(),
            "create_log_file": self.create_log_check.isChecked(),
            "log_file_path": self.log_path_edit.text().strip(),
        }
