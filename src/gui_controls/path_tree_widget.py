import os
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QCheckBox, QRadioButton, QButtonGroup, QComboBox,
    QFileDialog, QMessageBox, QStyle
)
from PySide6.QtCore import Qt, Signal

from utilities.formats import formats
from app_constance.file_filter import file_filter

PATH_ROLE = Qt.ItemDataRole.UserRole
TYPE_ROLE = Qt.ItemDataRole.UserRole + 1
FORMATS_ROLE = Qt.ItemDataRole.UserRole + 2


def all_known_extensions() -> list[str]:
    return sorted({*formats["audio"], *formats["video"]})


class AddFolderDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Add Folder"))
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit(self)
        self.path_edit.setAccessibleName(_("Folder path"))
        self.browse_button = QPushButton(_("Browse..."), self)
        self.browse_button.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit)
        path_row.addWidget(self.browse_button)
        layout.addLayout(path_row)

        self.subfolders_check = QCheckBox(_("Include all subfolders"), self)
        layout.addWidget(self.subfolders_check)

        self.scope_group = QButtonGroup(self)
        self.audio_radio = QRadioButton(_("Audio formats"), self)
        self.video_radio = QRadioButton(_("Video formats"), self)
        self.all_radio = QRadioButton(_("All formats"), self)
        self.custom_radio = QRadioButton(_("Custom format"), self)
        self.audio_radio.setChecked(True)
        for button_id, radio in enumerate((self.audio_radio, self.video_radio, self.all_radio, self.custom_radio)):
            self.scope_group.addButton(radio, button_id)
            layout.addWidget(radio)

        self.custom_combo = QComboBox(self)
        self.custom_combo.addItems(all_known_extensions())
        self.custom_combo.setEnabled(False)
        self.custom_combo.setAccessibleName(_("Custom format extension"))
        layout.addWidget(self.custom_combo)
        self.custom_radio.toggled.connect(self.custom_combo.setEnabled)

        button_row = QHBoxLayout()
        self.ok_button = QPushButton(_("OK"), self)
        self.cancel_button = QPushButton(_("Cancel"), self)
        self.ok_button.clicked.connect(self._on_accept)
        self.cancel_button.clicked.connect(self.reject)
        button_row.addStretch()
        button_row.addWidget(self.ok_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

    def _browse(self):
        directory = QFileDialog.getExistingDirectory(self, _("Select Folder"), self.path_edit.text())
        if directory:
            self.path_edit.setText(directory)

    def _on_accept(self):
        path = self.path_edit.text().strip()
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, _("Invalid Folder"), _("Please select a valid, existing folder."))
            return
        self.accept()

    def result_data(self) -> tuple[str, bool, set[str]]:
        path = self.path_edit.text().strip()
        recursive = self.subfolders_check.isChecked()

        if self.audio_radio.isChecked():
            extensions = set(formats["audio"])
        elif self.video_radio.isChecked():
            extensions = set(formats["video"])
        elif self.custom_radio.isChecked():
            extensions = {self.custom_combo.currentText()}
        else:
            extensions = {*formats["audio"], *formats["video"]}

        return path, recursive, extensions


class PathTreeWidget(QTreeWidget):
    paths_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._known_paths: set[str] = set()
        self._setup_ui()

    def _setup_ui(self):
        self.setColumnCount(2)
        self.setHeaderLabels([_("Path"), _("Formats")])
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setAccessibleName(_("Source files and folders"))
        self.setAccessibleDescription(
            _("Files and folders queued for processing. Right-click, or use the Add "
              "button, to add files or folders. Select an item and press Delete to remove it.")
        )

        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)

    @staticmethod
    def _normalize(path: str) -> str:
        return os.path.normcase(os.path.normpath(path))

    def has_path(self, path: str) -> bool:
        return self._normalize(path) in self._known_paths

    def clear_paths(self):
        self.clear()
        self._known_paths.clear()
        self.paths_changed.emit()

    def add_file(self, path: str) -> bool:
        if not path or self.has_path(path):
            return False

        item = QTreeWidgetItem()
        item.setText(0, os.path.basename(path) or path)
        item.setToolTip(0, path)
        item.setData(0, PATH_ROLE, path)
        item.setData(0, TYPE_ROLE, "file")
        item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.addTopLevelItem(item)

        self._known_paths.add(self._normalize(path))
        self.paths_changed.emit()
        return True

    def add_files(self, paths: list[str]) -> int:
        added = 0
        for path in paths:
            if self.add_file(path):
                added += 1
        return added

    def add_folder(self, path: str, format_scope: set[str], recursive: bool = False) -> bool:
        if not path or not os.path.isdir(path) or self.has_path(path):
            return False

        item = self._make_folder_item(path, format_scope)
        self.addTopLevelItem(item)
        item.setExpanded(False)
        self._known_paths.add(self._normalize(path))

        if recursive:
            self._add_subfolders(item, path, format_scope)

        self.paths_changed.emit()
        return True

    def _make_folder_item(self, path: str, format_scope: set[str]) -> QTreeWidgetItem:
        label = os.path.basename(os.path.normpath(path)) or path
        formats_label = ", ".join(sorted(format_scope)) if format_scope else _("All")

        item = QTreeWidgetItem()
        item.setText(0, label)
        item.setText(1, formats_label)
        item.setToolTip(0, path)
        item.setData(0, PATH_ROLE, path)
        item.setData(0, TYPE_ROLE, "folder")
        item.setData(0, FORMATS_ROLE, sorted(format_scope))
        item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        return item

    def _add_subfolders(self, parent_item: QTreeWidgetItem, path: str, format_scope: set[str]):
        try:
            subdirs = sorted((e for e in os.scandir(path) if e.is_dir()), key=lambda e: e.name.lower())
        except OSError:
            return

        for entry in subdirs:
            normalized = self._normalize(entry.path)
            if normalized in self._known_paths:
                continue

            child = self._make_folder_item(entry.path, format_scope)
            parent_item.addChild(child)
            child.setExpanded(False)
            self._known_paths.add(normalized)
            self._add_subfolders(child, entry.path, format_scope)

    def add_file_dialog(self):
        paths, _filter = QFileDialog.getOpenFileNames(self, _("Add Files"), "", file_filter)
        if paths:
            self.add_files(paths)

    def add_folder_dialog(self):
        dialog = AddFolderDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            path, recursive, format_scope = dialog.result_data()
            self.add_folder(path, format_scope, recursive)

    def _collect_normalized_paths(self, item: QTreeWidgetItem) -> list[str]:
        path = item.data(0, PATH_ROLE)
        collected = [self._normalize(path)] if path else []
        for i in range(item.childCount()):
            collected.extend(self._collect_normalized_paths(item.child(i)))
        return collected

    def remove_selected(self):
        for item in self.selectedItems():
            parent = item.parent()
            index = parent.indexOfChild(item) if parent else self.indexOfTopLevelItem(item)
            if index < 0:
                continue

            for normalized in self._collect_normalized_paths(item):
                self._known_paths.discard(normalized)

            if parent:
                parent.takeChild(index)
            else:
                self.takeTopLevelItem(index)

        self.paths_changed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.remove_selected()
            return
        super().keyPressEvent(event)

    def _show_context_menu(self, position):
        menu = QMenu(self)

        add_menu = menu.addMenu(_("Add"))
        add_menu.addAction(_("Add File(s)..."), self.add_file_dialog)
        add_menu.addAction(_("Add Folder..."), self.add_folder_dialog)

        menu.addSeparator()
        remove_action = menu.addAction(_("Remove"))
        remove_action.setEnabled(bool(self.selectedItems()))
        remove_action.triggered.connect(self.remove_selected)

        clear_action = menu.addAction(_("Clear All"))
        clear_action.setEnabled(self.topLevelItemCount() > 0)
        clear_action.triggered.connect(self.clear_paths)

        menu.exec(self.viewport().mapToGlobal(position))

    def iter_entries(self):
        def _walk(item: QTreeWidgetItem):
            path = item.data(0, PATH_ROLE)
            entry_type = item.data(0, TYPE_ROLE)
            entry_formats = item.data(0, FORMATS_ROLE)
            if path:
                yield path, entry_type, entry_formats
            for i in range(item.childCount()):
                yield from _walk(item.child(i))

        for i in range(self.topLevelItemCount()):
            yield from _walk(self.topLevelItem(i))
