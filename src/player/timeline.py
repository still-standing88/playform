from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget


class SegmentTimelineWidget(QWidget):

    segmentAdded = Signal(float, float)
    segmentUpdated = Signal(int, float, float)
    segmentRemoved = Signal(int)
    segmentSelected = Signal(int)

    markerAdded = Signal(float)
    markerMoved = Signal(int, float)
    markerRemoved = Signal(int)
    markerSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        self.setMouseTracking(True)


        self.segments = []
        self.next_id = 1
        self.focused_segment_id = None
        self._hover_pos = None
        self._dragging = None
        self._min_segment_width = 0.01


        self.markers = []
        self.next_marker_id = 1
        self.focused_marker_id = None

    def setSegments(self, segments):
        self.segments = []
        for seg in segments:
            self.segments.append({'id': self.next_id, 'start': seg[0], 'end': seg[1]})
            self.next_id += 1
        self.focused_segment_id = None
        self.update()

    def setMarkers(self, markers):
        self.markers = []
        for m in markers:
            self.markers.append({'id': self.next_marker_id, 'pos': m})
            self.next_marker_id += 1
        self.focused_marker_id = None
        self.update()

    def clearFocusedSegment(self):
        if self.focused_segment_id is not None:
            self.segments = [s for s in self.segments if s['id'] != self.focused_segment_id]
            self.segmentRemoved.emit(self.focused_segment_id)
            self.focused_segment_id = None
            self.update()

    def clearFocusedMarker(self):
        if self.focused_marker_id is not None:
            self.markers = [m for m in self.markers if m['id'] != self.focused_marker_id]
            self.markerRemoved.emit(self.focused_marker_id)
            self.focused_marker_id = None
            self.update()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        for seg in self.segments:
            x_start = seg['start'] * w
            x_end = seg['end'] * w
            color = QColor("#4e9cff80") if seg['id'] != self.focused_segment_id else QColor("#ff9f4080")
            painter.fillRect(QRectF(x_start, 8, x_end - x_start, h - 16), color)


        for m in self.markers:
            x = m['pos'] * w
            pen = QPen(QColor("#ffff0080"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(x, 4, x, h - 4)


        if self._hover_pos is not None:
            pen = QPen(QColor("#ffffff80"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(self._hover_pos, 0, self._hover_pos, h)

    def mousePressEvent(self, event):
        x = event.pos().x()
        w = self.width()
        pos_norm = x / w

        for m in self.markers:
            margin = 0.01
            if abs(pos_norm - m['pos']) < margin:
                self._dragging = {'marker': m['id']}
                self.focused_marker_id = m['id']
                self.markerSelected.emit(m['id'])
                return


        for seg in self.segments:
            edge_margin = 0.02
            if abs(pos_norm - seg['start']) < edge_margin:
                self._dragging = {'id': seg['id'], 'edge': 'start'}
                return
            elif abs(pos_norm - seg['end']) < edge_margin:
                self._dragging = {'id': seg['id'], 'edge': 'end'}
                return

            if seg['start'] <= pos_norm <= seg['end']:
                self.focused_segment_id = seg['id']
                self.segmentSelected.emit(seg['id'])
                self.update()
                return


        mods = event.modifiers()
        if mods & Qt.ShiftModifier or mods & Qt.ControlModifier:

            marker_pos = max(0.0, min(1.0, pos_norm))

            too_close = any(abs(marker_pos - m['pos']) < 0.01 for m in self.markers)
            if not too_close:
                new_marker = {'id': self.next_marker_id, 'pos': marker_pos}
                self.markers.append(new_marker)
                self.focused_marker_id = new_marker['id']
                self.markerAdded.emit(marker_pos)
                self.next_marker_id += 1
                self.update()
            return


        new_start = max(0.0, pos_norm - 0.05)
        new_end = min(1.0, pos_norm + 0.05)

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

            if 'marker' in self._dragging:
                mid = next((m for m in self.markers if m['id'] == self._dragging['marker']), None)
                if mid:
                    new_pos = max(0.0, min(1.0, pos_norm))
                    mid['pos'] = new_pos
                    self.markerMoved.emit(mid['id'], new_pos)
                    self.update()
                    return

            seg = next((s for s in self.segments if s['id'] == self._dragging.get('id')), None)
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

    def _checkOverlap(self, start, end, ignore_id=None):
        for seg in self.segments:
            if ignore_id is not None and seg['id'] == ignore_id:
                continue
            if max(seg['start'], start) < min(seg['end'], end):
                return True
        return False
