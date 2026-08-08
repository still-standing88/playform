from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from tools.m4b_tools.audiobook_tools.bind_tab import BindTab
from tools.m4b_tools.audiobook_tools.split_tab import SplitTab
from tools.m4b_tools.audiobook_tools.slide_tab import SlideTab
from tools.m4b_tools.audiobook_tools.labels_tab import LabelsTab
from tools.m4b_tools.audiobook_tools.cover_tab import CoverTab


class AudiobookToolsUI(QWidget):
    """Single-audiobook operations: bind, split, slide, labels, cover — unified under one
    tool since they all act on one book/source at a time, unlike the CSV/multi-file-driven
    Combine + Metadata Dump operations in `tools.m4b_tools.combiner`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        self.bind_tab = BindTab(self)
        self.split_tab = SplitTab(self)
        self.slide_tab = SlideTab(self)
        self.labels_tab = LabelsTab(self)
        self.cover_tab = CoverTab(self)

        self.tabs.addTab(self.bind_tab, _("Bind"))
        self.tabs.addTab(self.split_tab, _("Split"))
        self.tabs.addTab(self.slide_tab, _("Slide"))
        self.tabs.addTab(self.labels_tab, _("Labels"))
        self.tabs.addTab(self.cover_tab, _("Cover"))

        layout.addWidget(self.tabs)
