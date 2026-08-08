import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QFileDialog
)
from PySide6.QtCore import Qt, Signal

from app_constance.file_filter import file_filter as default_file_filter

PATH_ROLE = Qt.ItemDataRole.UserRole


class OrderedFileListWidget(QWidget):
    """A manually-orderable file list: Add/Remove/Move Up/Move Down/Clear.

    For workflows where sequence matters and the user needs full control over it
    (e.g. audiobook chapter order), unlike `PathTreeWidget` which is aimed at
    format-filtered file/folder *source* selection instead.
    """

    files_changed = Signal()

    def __init__(self, parent=None, file_dialog_filter: str = None):
        super().__init__(parent)
        self._file_dialog_filter = file_dialog_filter or default_file_filter
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setAccessibleName(_("Ordered file list"))
        self.list_widget.setAccessibleDescription(
            _("Files in processing order. Use the Move Up/Move Down buttons to reorder.")
        )
        layout.addWidget(self.list_widget, stretch=1)

        button_column = QVBoxLayout()
        self.add_button = QPushButton(_("Add Files..."), self)
        self.remove_button = QPushButton(_("Remove"), self)
        self.move_up_button = QPushButton(_("Move Up"), self)
        self.move_down_button = QPushButton(_("Move Down"), self)
        self.clear_button = QPushButton(_("Clear All"), self)

        for button in (self.add_button, self.remove_button, self.move_up_button,
                       self.move_down_button, self.clear_button):
            button_column.addWidget(button)
        button_column.addStretch()
        layout.addLayout(button_column)

        self.add_button.clicked.connect(self.add_files_dialog)
        self.remove_button.clicked.connect(self.remove_selected)
        self.move_up_button.clicked.connect(self.move_selected_up)
        self.move_down_button.clicked.connect(self.move_selected_down)
        self.clear_button.clicked.connect(self.clear)

    @staticmethod
    def _normalize(path: str) -> str:
        return os.path.normcase(os.path.normpath(path))

    def has_path(self, path: str) -> bool:
        target = self._normalize(path)
        for i in range(self.list_widget.count()):
            if self._normalize(self.list_widget.item(i).data(PATH_ROLE)) == target:
                return True
        return False

    def add_files_dialog(self):
        paths, _filter = QFileDialog.getOpenFileNames(self, _("Add Files"), "", self._file_dialog_filter)
        self.add_files(paths)

    def add_files(self, paths: list) -> int:
        added = 0
        for path in paths:
            if not path or self.has_path(path):
                continue
            item = QListWidgetItem(os.path.basename(path))
            item.setData(PATH_ROLE, path)
            item.setToolTip(path)
            self.list_widget.addItem(item)
            added += 1
        if added:
            self.files_changed.emit()
        return added

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.files_changed.emit()

    def move_selected_up(self):
        rows = sorted(self.list_widget.row(i) for i in self.list_widget.selectedItems())
        for row in rows:
            if row <= 0:
                continue
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            item.setSelected(True)
        self.files_changed.emit()

    def move_selected_down(self):
        rows = sorted((self.list_widget.row(i) for i in self.list_widget.selectedItems()), reverse=True)
        for row in rows:
            if row >= self.list_widget.count() - 1:
                continue
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            item.setSelected(True)
        self.files_changed.emit()

    def clear(self):
        self.list_widget.clear()
        self.files_changed.emit()

    def file_paths(self) -> list:
        return [self.list_widget.item(i).data(PATH_ROLE) for i in range(self.list_widget.count())]

    def is_empty(self) -> bool:
        return self.list_widget.count() == 0
