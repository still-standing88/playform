from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont

class LoadingSplash(QSplashScreen):
    def __init__(self):
        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor(45, 45, 48))
        
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "PlayForm\nLoading...")
        painter.end()
        
        super().__init__(pixmap, )#Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        
    def update_message(self, message):
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            QColor(200, 200, 200)
        )
        QApplication.processEvents()
