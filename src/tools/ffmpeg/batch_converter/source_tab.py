from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from gui_controls.path_tree_widget import PathTreeWidget


class SourceTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        button_row = QHBoxLayout()
        self.add_files_button = QPushButton(_("Add Files..."), self)
        self.add_folder_button = QPushButton(_("Add Folder..."), self)
        self.remove_button = QPushButton(_("Remove Selected"), self)
        self.clear_button = QPushButton(_("Clear All"), self)
        button_row.addWidget(self.add_files_button)
        button_row.addWidget(self.add_folder_button)
        button_row.addStretch()
        button_row.addWidget(self.remove_button)
        button_row.addWidget(self.clear_button)
        layout.addLayout(button_row)

        self.tree = PathTreeWidget(self)
        layout.addWidget(self.tree)

        self.add_files_button.clicked.connect(self.tree.add_file_dialog)
        self.add_folder_button.clicked.connect(self.tree.add_folder_dialog)
        self.remove_button.clicked.connect(self.tree.remove_selected)
        self.clear_button.clicked.connect(self.tree.clear_paths)

    def has_sources(self) -> bool:
        return self.tree.topLevelItemCount() > 0

    def iter_entries(self):
        return self.tree.iter_entries()
