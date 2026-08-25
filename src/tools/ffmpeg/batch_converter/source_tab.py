from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from gui_controls.path_tree_widget import PathTreeWidget


class SourceTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Remove/Clear live only in the tree's context menu now -- with two
        # add buttons on the left and destructive actions one right-click
        # away, the button row stays readable without losing any action.
        button_row = QHBoxLayout()
        self.add_files_button = QPushButton(_("Add Files..."), self)
        self.add_folder_button = QPushButton(_("Add Folder..."), self)
        button_row.addWidget(self.add_files_button)
        button_row.addWidget(self.add_folder_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.tree = PathTreeWidget(self)
        layout.addWidget(self.tree)

        self.add_files_button.clicked.connect(self.tree.add_file_dialog)
        self.add_folder_button.clicked.connect(self.tree.add_folder_dialog)

    def has_sources(self) -> bool:
        return self.tree.topLevelItemCount() > 0

    def iter_entries(self):
        return self.tree.iter_entries()
