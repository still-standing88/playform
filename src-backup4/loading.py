from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QDialog

class Worker(QThread):
    finished = Signal()
    def __init__(self, method):
        super().__init__()
        self.method = method

    def run(self):
        self.method()

class loadingDialog(QDialog):
    onLoadFinished = Signal()

    def __init__(self, method, parent=None):
        super().__init__(parent)
        self.method = method
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle("Loading")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(200, 200)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.ui()
        self.Layout()

        self.worker = Worker(self.method)
        self.worker.finished.connect(self.onFinished)

    def ui(self):
        self.label = QLabel("loading", self)

    def Layout(self):
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.label)

    def begin(self):
        self.show()
        self.worker.start()

    def onFinished(self):
        self.onLoadFinished.emit()
        self.close()

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_Escape, Qt.Key_F4] and (event.modifiers() & Qt.AltModifier):
            return
        super().keyPressEvent(event)

    def closeEvent(self,event):
        if self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
