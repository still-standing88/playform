from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class M4BToolsUI(QWidget):
    """Placeholder for the M4B Tools module.

    Scope is deferred until the reference manuals for the underlying M4B
    library/CLI are provided (see TOOLS_REWRITE_PLAN.md, section 3). The
    Tools menu entry for this module stays disabled until then.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel(_("M4B Tools is coming soon."), self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
