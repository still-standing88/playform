from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from .toggle_button import ToggleButton


class AccordionSection(QWidget):
    """A single collapsible section: a clickable header + a content widget."""

    toggled = Signal(object, bool)  # (section, is_open)

    def __init__(self, title: str, content: QWidget, parent=None):
        super().__init__(parent)
        self.content = content
        self._syncing = False

        self.header = ToggleButton(title)
        self.header.actuated.connect(self._on_header_actuated)

        self.content.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.content)

    def _on_header_actuated(self, is_open: bool):
        if self._syncing:
            return
        self.set_open(is_open)

    def set_open(self, open_: bool, emit: bool = True):
        # ToggleButton.actuated fires on setActuated() too, not just user
        # clicks, so this guard prevents _on_header_actuated from recursing
        # back into set_open when the change originates here.
        self._syncing = True
        try:
            self.header.setActuated(open_)
        finally:
            self._syncing = False
        self.content.setVisible(open_)
        if emit:
            self.toggled.emit(self, open_)

    def is_open(self) -> bool:
        return self.header.isActuated()


class Accordion(QWidget):
    """
    Container of AccordionSections with single-open exclusivity, but the
    open section can be collapsed to leave all sections closed - unlike
    QToolBox, which always keeps exactly one page open.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sections = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)
        self._layout.addStretch()  # keeps sections pinned to top when collapsed

    def add_section(self, title: str, content: QWidget) -> AccordionSection:
        section = AccordionSection(title, content)
        section.toggled.connect(self._on_section_toggled)
        self._sections.append(section)
        # insert before the trailing stretch
        self._layout.insertWidget(self._layout.count() - 1, section)
        return section

    def _on_section_toggled(self, section, is_open):
        if is_open:
            for other in self._sections:
                if other is not section and other.is_open():
                    other.set_open(False, emit=False)

    def collapse_all(self):
        for s in self._sections:
            s.set_open(False, emit=False)

    def open_section(self, index: int):
        for i, s in enumerate(self._sections):
            s.set_open(i == index, emit=False)

    def current_index(self) -> int:
        for i, s in enumerate(self._sections):
            if s.is_open():
                return i
        return -1
