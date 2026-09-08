from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread, Slot
from PySide6.QtGui import QKeyEvent, QGuiApplication
from app_constance.styles import TITLE_LABEL_STYLE


class ToolDialog(QDialog):
    dialog_hidden = Signal()

    # Same idea as DockManager.SCREEN_FIT_SAFETY_MARGIN: never open flush
    # against the edge of the work area.
    SCREEN_FIT_SAFETY_MARGIN = 16
    SCROLLBAR_ALLOWANCE = 24
    DEFAULT_WIDTH = 800
    DEFAULT_HEIGHT = 600

    def __init__(self, tool_widget, title, parent=None):
        super().__init__(parent)
        self.tool_widget = tool_widget
        self.title = title

        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setModal(True)
        # Tool UIs range from ~200px tall to over 1000px (Audiobook Tools).
        # A hard 600x400 minimum used to override the tool's real
        # minimumSizeHint, which silently squeezed and clipped the tall ones
        # instead of scrolling them; the scroll area below is what makes a
        # small minimum safe.
        self.setMinimumSize(480, 320)

        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title_bar = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        hide_btn = QPushButton(_("Hide"))
        hide_btn.setMinimumWidth(60)

        hide_btn.clicked.connect(self.hide_and_unlock)
        title_bar.addWidget(hide_btn)

        close_btn = QPushButton(_("Close"))
        close_btn.setMinimumWidth(60)
        close_btn.clicked.connect(self.close_dialog)
        title_bar.addWidget(close_btn)

        layout.addLayout(title_bar)

        self.tool_scroll = QScrollArea(self)
        self.tool_scroll.setWidget(self.tool_widget)
        self.tool_scroll.setWidgetResizable(True)
        self.tool_scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.tool_scroll)

        self._resize_to_fit_screen(title_bar.sizeHint().height())

    def _resize_to_fit_screen(self, title_bar_height: int):
        hint = self.tool_widget.sizeHint()
        margins = self.layout().contentsMargins()
        width = hint.width() + margins.left() + margins.right() + self.SCROLLBAR_ALLOWANCE
        height = (hint.height() + title_bar_height + self.layout().spacing()
                  + margins.top() + margins.bottom())

        # Never smaller than the old flat 800x600 default - tools that
        # already fit comfortably should keep the room they had.
        width = max(width, self.DEFAULT_WIDTH)
        height = max(height, self.DEFAULT_HEIGHT)

        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            width = min(width, area.width() - self.SCREEN_FIT_SAFETY_MARGIN)
            height = min(height, area.height() - self.SCREEN_FIT_SAFETY_MARGIN)

        self.resize(max(width, self.minimumWidth()), max(height, self.minimumHeight()))

        if screen is not None:
            self.move(
                max(area.left(), area.left() + (area.width() - self.width()) // 2),
                max(area.top(), area.top() + (area.height() - self.height()) // 2),
            )
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)
    
    @Slot()
    def hide_and_unlock(self):
        self.hide()
        self.dialog_hidden.emit()
    
    @Slot()
    def show_dialog(self):
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.show()
        self.raise_()
        self.activateWindow()
    
    def is_tool_active(self):
        if hasattr(self.tool_widget, 'thread'):
            thread = self.tool_widget.thread
            if isinstance(thread, QThread) and thread is not None:
                return thread.isRunning()
        return False
    
    @Slot()
    def close_dialog(self):
        if self.is_tool_active():
            QMessageBox.warning(
                self, 
                _("Tool Active"), 
                f"{self.title} {_("is currently processing. Please wait for it to complete or cancel the operation before closing.")}"
            )
        else:
            self.accept()
    
    def closeEvent(self, event):
        if self.is_tool_active():
            QMessageBox.warning(
                self, 
                _("Tool Active"), 
                f" {self.title} {_("is currently processing. Please wait for it to complete or cancel the operation before closing.")}"
            )
            event.ignore()
        else:
            event.accept()
