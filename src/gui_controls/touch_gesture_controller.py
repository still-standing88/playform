import math
import time

from PySide6.QtCore import QObject, QEvent, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QEventPoint
from PySide6.QtWidgets import QApplication

from app_constance.touch_gestures import normalize_settings


class TouchGestureController(QObject):
    triggered = Signal(str, object)
    started = Signal(str)
    updated = Signal(str, object)
    finished = Signal(str, bool)

    def __init__(self, surface, settings, can_interact=None):
        super().__init__(surface)
        self.surface = surface
        self.settings = normalize_settings(settings)
        self.can_interact = can_interact or (lambda: True)
        self._active = False
        self._mode = None
        self._pending_tap = None
        self._second_tap = False
        self._last_touch = 0.0
        self._tap_timer = QTimer(self)
        self._tap_timer.setSingleShot(True)
        self._tap_timer.timeout.connect(self._deliver_tap)
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._long_press)
        self.attach(surface)

    def attach(self, widget):
        widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        widget.installEventFilter(self)

    def set_settings(self, settings):
        self.cancel()
        self.settings = normalize_settings(settings)

    def cancel(self):
        self._tap_timer.stop()
        self._hold_timer.stop()
        self._pending_tap = None
        mode = self._mode
        self._active = False
        self._mode = None
        if mode and mode != "ignored":
            self.finished.emit(mode, True)

    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self.surface and kind in (QEvent.Type.Hide, QEvent.Type.WindowDeactivate):
            self.cancel()
        if kind in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            if kind == QEvent.Type.TouchBegin and (not self.settings["enabled"] or not self.can_interact()):
                event.ignore()
                return False
            if kind != QEvent.Type.TouchBegin and not self._active:
                return False
            self._last_touch = time.monotonic()
            if kind == QEvent.Type.TouchCancel:
                self.cancel()
            else:
                self._touch(event)
            event.accept()
            return True
        if time.monotonic() - self._last_touch < 0.5:
            if kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick, QEvent.Type.MouseMove):
                if event.source() != Qt.MouseEventSource.MouseEventNotSynthesized:
                    return True
        return False

    def _region(self, point):
        third = self.surface.width() / 3
        return "left" if point.x() < third else "center" if point.x() < third * 2 else "right"

    def _matches_pending(self, point):
        if self._pending_tap is None:
            return False
        previous, timestamp = self._pending_tap
        distance = max(40, QApplication.styleHints().touchDoubleTapDistance())
        return (time.monotonic() - timestamp <= self.settings["double_tap_ms"] / 1000
                and self._region(point) == self._region(previous)
                and (point - previous).manhattanLength() <= distance)

    def _touch(self, event):
        points = {p.id(): self.surface.mapFromGlobal(p.globalPosition()) for p in event.points()}
        active = {p.id(): points[p.id()] for p in event.points() if p.state() != QEventPoint.State.Released}
        if event.type() == QEvent.Type.TouchBegin:
            if not points:
                return
            self._active = True
            self._mode = None
            self._moved = False
            self._primary = next(iter(points))
            self._origin = QPointF(points[self._primary])
            self._last_position = QPointF(self._origin)
            self._pair = None
            self._second_tap = self._matches_pending(self._origin)
            if self._second_tap:
                self._tap_timer.stop()
            else:
                self._deliver_tap()
            self._hold_timer.start(self.settings["hold_ms"])
        if len(active) > 2:
            self._ignore_sequence()
        elif len(active) == 2:
            self._multi_touch(active)
        elif len(active) == 1 and self._pair is None and self._mode != "ignored":
            point = points.get(self._primary)
            if point is not None:
                self._single_move(point)
        elif self._pair is not None and active and self._mode != "ignored":
            mode = self._mode
            self._mode = "ignored"
            if mode:
                self.finished.emit(mode, False)
        if event.type() == QEvent.Type.TouchEnd or not active:
            point = points.get(self._primary, self._last_position)
            if self._pair is None and self._mode in (None, "horizontal_drag", "vertical_drag_left", "vertical_drag_right"):
                self._single_move(point)
            mode = self._mode
            self._active = False
            self._mode = None
            self._hold_timer.stop()
            if mode is None and self._pair is None and not self._moved:
                self._tap(point)
            elif mode != "ignored":
                self.finished.emit(mode, False)

    def _clear_pending(self):
        self._tap_timer.stop()
        self._pending_tap = None

    def _ignore_sequence(self):
        self._hold_timer.stop()
        self._clear_pending()
        previous = self._mode
        self._mode = "ignored"
        if previous and previous != "ignored":
            self.finished.emit(previous, True)

    def _start(self, gesture):
        self._hold_timer.stop()
        self._clear_pending()
        self._mode = gesture
        self.started.emit(gesture)

    def _single_move(self, point):
        delta = point - self._origin
        if self._mode is None and max(abs(delta.x()), abs(delta.y())) >= self.settings["drag_threshold"]:
            self._moved = True
            if abs(delta.x()) >= abs(delta.y()) * 1.2:
                self._start("horizontal_drag")
            elif abs(delta.y()) >= abs(delta.x()) * 1.2:
                side = "left" if self._origin.x() < self.surface.width() / 2 else "right"
                self._start("vertical_drag_" + side)
            else:
                self._hold_timer.stop()
                self._clear_pending()
        if self._mode in ("horizontal_drag", "vertical_drag_left", "vertical_drag_right"):
            width, height = max(1, self.surface.width()), max(1, self.surface.height())
            self.updated.emit(self._mode, {
                "x": delta.x() / width, "y": delta.y() / height,
                "dx": (point.x() - self._last_position.x()) / width,
                "dy": (point.y() - self._last_position.y()) / height,
            })
        self._last_position = QPointF(point)

    def _multi_touch(self, points):
        if self._mode == "ignored":
            return
        ids = tuple(sorted(points))
        first, second = (points[i] for i in ids)
        center = (first + second) / 2
        distance = math.hypot(first.x() - second.x(), first.y() - second.y())
        if self._pair is None:
            previous = self._mode
            self._mode = None
            if previous:
                self.finished.emit(previous, True)
            self._pair = (ids, center, max(1, distance))
            self._hold_timer.stop()
            self._clear_pending()
        ids_start, center_start, distance_start = self._pair
        if ids != ids_start:
            self._ignore_sequence()
            return
        delta = center - center_start
        if self._mode is None:
            threshold = self.settings["drag_threshold"]
            if abs(distance - distance_start) >= threshold:
                self._start("pinch")
            elif math.hypot(delta.x(), delta.y()) >= threshold:
                self._start("two_finger_drag")
        if self._mode in ("pinch", "two_finger_drag"):
            self.updated.emit(self._mode, {
                "scale": distance / distance_start,
                "x": delta.x() / max(1, self.surface.width()),
                "y": delta.y() / max(1, self.surface.height()),
            })

    def _tap(self, point):
        if self._second_tap and self._matches_pending(point):
            self._clear_pending()
            self.triggered.emit("double_tap_" + self._region(point), QPointF(point))
            return
        self._deliver_tap()
        self._pending_tap = (QPointF(point), time.monotonic())
        self._tap_timer.start(self.settings["double_tap_ms"])

    def _deliver_tap(self):
        if self._pending_tap is None:
            return
        point, _ = self._pending_tap
        self._clear_pending()
        if self.settings["enabled"] and self.can_interact():
            self.triggered.emit("tap", point)

    def _long_press(self):
        if not self._active or self._mode is not None:
            return
        self._clear_pending()
        self._mode = "long_press"
        if self.settings["bindings"]["long_press"] == "temporary_speed":
            self.started.emit("long_press")
        else:
            self.triggered.emit("long_press", QPointF(self._last_position))
