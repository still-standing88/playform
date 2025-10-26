from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget


class SegmentTimelineWidget(QWidget):
    # Signals
    segmentAdded = Signal(float, float)        # start, end in 0.0–1.0
    segmentUpdated = Signal(int, float, float) # segment_id, new start, end
    segmentRemoved = Signal(int)               # segment_id
    segmentSelected = Signal(int)              # segment_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        self.setMouseTracking(True)

        # internal state
        self.segments = []  # list of dicts: {'id': int, 'start': float, 'end': float}
        self.next_id = 1
        self.focused_segment_id = None
        self._hover_pos = None
        self._dragging = None   # {'id', 'edge'} edge='start'/'end'
        self._min_segment_width = 0.01  # in 0.0–1.0 scale

    # --------------------------
    # Segment management
    # --------------------------
    def setSegments(self, segments):
        """Replace the current segments with a given list."""
        self.segments = []
        for seg in segments:
            self.segments.append({'id': self.next_id, 'start': seg[0], 'end': seg[1]})
            self.next_id += 1
        self.focused_segment_id = None
        self.update()

    def clearFocusedSegment(self):
        if self.focused_segment_id is not None:
            self.segments = [s for s in self.segments if s['id'] != self.focused_segment_id]
            self.segmentRemoved.emit(self.focused_segment_id)
            self.focused_segment_id = None
            self.update()

    # --------------------------
    # Painting
    # --------------------------
    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        # Draw segments
        for seg in self.segments:
            x_start = seg['start'] * w
            x_end = seg['end'] * w
            color = QColor("#4e9cff80") if seg['id'] != self.focused_segment_id else QColor("#ff9f4080")
            painter.fillRect(QRectF(x_start, 8, x_end - x_start, h - 16), color)

        # Draw hover line if applicable
        if self._hover_pos is not None:
            pen = QPen(QColor("#ffffff80"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(self._hover_pos, 0, self._hover_pos, h)

    # --------------------------
    # Mouse handling
    # --------------------------
    def mousePressEvent(self, event):
        x = event.pos().x()
        w = self.width()
        pos_norm = x / w

        # Check if clicking on existing segment edges (resize)
        for seg in self.segments:
            edge_margin = 0.02
            if abs(pos_norm - seg['start']) < edge_margin:
                self._dragging = {'id': seg['id'], 'edge': 'start'}
                return
            elif abs(pos_norm - seg['end']) < edge_margin:
                self._dragging = {'id': seg['id'], 'edge': 'end'}
                return
            # Click inside → select
            if seg['start'] <= pos_norm <= seg['end']:
                self.focused_segment_id = seg['id']
                self.segmentSelected.emit(seg['id'])
                self.update()
                return

        # Else: add new segment at click position
        new_start = max(0.0, pos_norm - 0.05)
        new_end = min(1.0, pos_norm + 0.05)
        # Validate against overlaps
        if not self._checkOverlap(new_start, new_end):
            new_seg = {'id': self.next_id, 'start': new_start, 'end': new_end}
            self.segments.append(new_seg)
            self.focused_segment_id = new_seg['id']
            self.segmentAdded.emit(new_start, new_end)
            self.next_id += 1
            self.update()

    def mouseMoveEvent(self, event):
        self._hover_pos = event.pos().x()
        if self._dragging is not None:
            w = self.width()
            pos_norm = self._hover_pos / w
            seg = next((s for s in self.segments if s['id'] == self._dragging['id']), None)
            if seg:
                if self._dragging['edge'] == 'start':
                    new_start = min(pos_norm, seg['end'] - self._min_segment_width)
                    if not self._checkOverlap(new_start, seg['end'], ignore_id=seg['id']):
                        seg['start'] = new_start
                        self.segmentUpdated.emit(seg['id'], seg['start'], seg['end'])
                elif self._dragging['edge'] == 'end':
                    new_end = max(pos_norm, seg['start'] + self._min_segment_width)
                    if not self._checkOverlap(seg['start'], new_end, ignore_id=seg['id']):
                        seg['end'] = new_end
                        self.segmentUpdated.emit(seg['id'], seg['start'], seg['end'])
            self.update()
        else:
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = None

    def leaveEvent(self, event):
        self._hover_pos = None
        self.update()

    # --------------------------
    # Utilities
    # --------------------------
    def _checkOverlap(self, start, end, ignore_id=None):
        """Return True if overlap exists with existing segments (excluding ignore_id)."""
        for seg in self.segments:
            if ignore_id is not None and seg['id'] == ignore_id:
                continue
            if max(seg['start'], start) < min(seg['end'], end):
                return True
        return False
