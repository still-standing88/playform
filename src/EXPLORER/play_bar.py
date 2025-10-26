from PySide6.QtCore import Qt, QRectF, QPointF, Signal, Slot, QTimer
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget, QToolTip


class PlayerBar(QWidget):
    # Exposed signals for external connections
    playPauseToggled = Signal(bool)   # True = playing
    forwardTriggered = Signal()
    backwardTriggered = Signal()
    seekRequested = Signal(float)     # 0.0–1.0 (percentage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._isPlaying = False
        self._hover_pos = None

        self.setMinimumHeight(28)
        self.setMouseTracking(True)
        
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._hide_tooltip)

    # --------------------------
    # State Management
    # --------------------------
    @Slot(bool)
    def setState(self, playing: bool):
        """Set play/pause state."""
        if self._isPlaying != playing:
            self._isPlaying = playing
            self.update()

    def getState(self) -> bool:
        """Return current playing state."""
        return self._isPlaying

    @Slot(float)
    def setProgress(self, value: float):
        """Set progress (0.0–1.0)."""
        self._progress = max(0.0, min(1.0, value))
        self.update()

    def getProgress(self) -> float:
        return self._progress

    # --------------------------
    # Painting
    # --------------------------
    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        # Progress bar
        progress_width = int(w * self._progress)
        painter.fillRect(QRectF(0, h - 6, progress_width, 6), QColor("#4e9cff"))

        # Center play/pause indicator
        center_x = w // 2
        center_y = h // 2
        size = int(h * 0.5)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))

        if self._isPlaying:
            # Pause symbol
            bar_w = int(size * 0.25)
            gap = int(bar_w * 0.6)
            painter.drawRect(int(center_x - gap - bar_w), int(center_y - size / 2), bar_w, size)
            painter.drawRect(int(center_x + gap), int(center_y - size / 2), bar_w, size)
        else:
            # Play triangle
            points = [
                QPointF(center_x - size * 0.35, center_y - size / 2),
                QPointF(center_x - size * 0.35, center_y + size / 2),
                QPointF(center_x + size * 0.45, center_y),
            ]
            painter.drawPolygon(points)

        # Hover preview marker (optional)
        if self._hover_pos is not None:
            pen = QPen(QColor("#ffffff80"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(self._hover_pos, h - 6, self._hover_pos, h - 2)

    # --------------------------
    # Mouse interactions
    # --------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            w = self.width()
            x = event.pos().x()
            center = w / 2
            margin = 40  # clickable center zone

            if abs(x - center) < margin:
                # Toggle play/pause
                self._isPlaying = not self._isPlaying
                self.playPauseToggled.emit(self._isPlaying)
                self.update()
            elif x < center - margin:
                self.backwardTriggered.emit()
            elif x > center + margin:
                self.forwardTriggered.emit()
            else:
                # Seek
                self._progress = x / w
                self.seekRequested.emit(self._progress)
                self.update()

    def mouseMoveEvent(self, event):
        self._hover_pos = event.pos().x()
        self.update()

    def leaveEvent(self, event):
        self._hover_pos = None
        self.update()
    
    def enterEvent(self, event):
        tooltip_text = "Click center: Play/Pause | Click left: Backward | Click right: Forward | Click bar: Seek"
        QToolTip.showText(self.mapToGlobal(event.pos()), tooltip_text, self)
        self._tooltip_timer.start(3000)
    
    def _hide_tooltip(self):
        QToolTip.hideText()
