from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QKeyEvent
from app_constance.styles import TITLE_LABEL_STYLE


class ToolDialog(QDialog):
    dialog_hidden = Signal()
    
    def __init__(self, tool_widget, title, parent=None):
        super().__init__(parent)
        self.tool_widget = tool_widget
        self.title = title
        
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.resize(800, 600)
        
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        title_bar = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        
        hide_btn = QPushButton("Hide")
        hide_btn.setFixedSize(60, 25)
        hide_btn.setToolTip("Hide this dialog")
        hide_btn.clicked.connect(self.hide_and_unlock)
        title_bar.addWidget(hide_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(60, 25)
        close_btn.setToolTip("Close this dialog")
        close_btn.clicked.connect(self.close_dialog)
        title_bar.addWidget(close_btn)
        
        layout.addLayout(title_bar)
        layout.addWidget(self.tool_widget)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)
    
    def hide_and_unlock(self):
        self.hide()
        self.dialog_hidden.emit()
    
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
    
    def close_dialog(self):
        if self.is_tool_active():
            QMessageBox.warning(
                self, 
                "Tool Active", 
                f"The {self.title} is currently processing. Please wait for it to complete or cancel the operation before closing."
            )
        else:
            self.accept()
    
    def closeEvent(self, event):
        if self.is_tool_active():
            QMessageBox.warning(
                self, 
                "Tool Active", 
                f"The {self.title} is currently processing. Please wait for it to complete or cancel the operation before closing."
            )
            event.ignore()
        else:
            event.accept()