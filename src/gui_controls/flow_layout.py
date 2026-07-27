# Ported from Qt's official "Flow Layout" example
# (https://doc.qt.io/qt-6/qtwidgets-layouts-flowlayout-example.html), adapted
# for PySide6. Wraps its child widgets onto as many rows as the available
# width needs, instead of a QToolBar's single fixed row.
from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QSizePolicy, QWidget


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, h_spacing=6, v_spacing=6):
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items = []
        self.setContentsMargins(QMargins(margin, margin, margin, margin))

    def addItem(self, item):
        self._items.append(item)

    def horizontalSpacing(self):
        return self._h_spacing

    def verticalSpacing(self):
        return self._v_spacing

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
            hint = item.sizeHint()
            space_x = self.horizontalSpacing()
            space_y = self.verticalSpacing()
            next_x = x + hint.width() + space_x

            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + hint.width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = next_x
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y() + bottom


class FlowContainer(QWidget):
    """A plain QWidget's default sizeHint(), when its layout hasHeightForWidth,
    resolves height by querying heightForWidth() at the layout's own (tiny,
    single-item-wide) sizeHint width - a worst-case near-one-column wrap that
    hugely overstates the height actually needed once really laid out at the
    container's real width. That worst-case height, in a QToolBar specifically,
    then gets locked in as the toolbar's row height regardless of its actual
    width, permanently reserving far more space than it uses. Basing the
    query on this widget's own current width (falling back to a size-policy
    hint only before the first real layout pass) avoids that trap."""

    def __init__(self, parent=None, fallback_width=900):
        super().__init__(parent)
        self._fallback_width = fallback_width
        self._last_width = -1

    def sizeHint(self):
        layout = self.layout()
        if layout is None:
            return super().sizeHint()
        width = self.width() if self.width() > 0 else self._fallback_width
        return QSize(width, layout.heightForWidth(width))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # A plain width change doesn't by itself make the *enclosing* layout
        # (here, QToolBarLayout) re-query sizeHint()/heightForWidth() at the
        # new width - without forcing that, the toolbar's reserved row height
        # stays whatever it was the first time this widget was shown, and
        # rows that wrap in later at a narrower width render past that
        # now-too-short boundary.
        if event.size().width() != self._last_width:
            self._last_width = event.size().width()
            self.updateGeometry()
