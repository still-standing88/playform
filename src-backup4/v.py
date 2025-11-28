from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
import sys

class CustomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WindowModal Dialog")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setModal(True)

        # Prevent ESC from closing
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        hide_button = QPushButton("Hide this dialog")
        hide_button.clicked.connect(self.hide_and_unlock)

        layout = QVBoxLayout()
        layout.addWidget(hide_button)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        # Ignore Escape key
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def hide_and_unlock(self):
        # Remove window modality so parent can be used
        #self.setWindowModality(Qt.WindowModality.NonModal)
        self.hide()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Window")

        self.dialog = CustomDialog(self)

        open_btn = QPushButton("Open Dialog")
        open_btn.clicked.connect(self.open_dialog)

        layout = QVBoxLayout()
        layout.addWidget(open_btn)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_dialog(self):
        # Restore window modality
        self.dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

app = QApplication(sys.argv)
win = MainWindow()
win.show()
app.exec()
