from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPixmap, QPainter, QFont
from app_constance.styles import theme_qcolor

class LoadingSplash(QSplashScreen):
    def __init__(self):
        pixmap = QPixmap(400, 300)
        pixmap.fill(theme_qcolor("COLOR_BACKGROUND_1"))
        
        painter = QPainter(pixmap)
        painter.setPen(theme_qcolor("COLOR_TEXT_1"))
        font = QFont()
        font.setPointSize(16)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, _("PlayForm\nLoading..."))
        painter.end()
        
        super().__init__(pixmap, )#Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        
    def update_message(self, message):
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            theme_qcolor("COLOR_TEXT_3")
        )
        QApplication.processEvents()
