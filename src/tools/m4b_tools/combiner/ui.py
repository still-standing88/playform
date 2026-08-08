from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from tools.m4b_tools.combiner.combine_tab import CombineTab
from tools.m4b_tools.combiner.metadata_dump_tab import MetadataDumpTab


class AudiobookCombinerUI(QWidget):
    """Multi-book, CSV/glob-driven operations: combine several audiobooks into one, and
    dump chapter/metadata CSVs across a batch of files — unified under one tool since both
    share the same "point at many files, produce one consolidated result" shape, unlike the
    single-book operations in `tools.m4b_tools.audiobook_tools`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        self.combine_tab = CombineTab(self)
        self.metadata_dump_tab = MetadataDumpTab(self)

        self.tabs.addTab(self.combine_tab, _("Combine"))
        self.tabs.addTab(self.metadata_dump_tab, _("Metadata Dump"))

        layout.addWidget(self.tabs)
