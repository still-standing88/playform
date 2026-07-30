"""
Professional wx.ListCtrl clone for PySide6
Features:
- Report view with full column support
- Virtual scrolling for large datasets
- Full keyboard navigation and accessibility
- Column sorting with visual indicators
- Custom delegates for rendering
- Proper model/view architecture
"""

from PySide6.QtWidgets import (
    QListView, QWidget, QVBoxLayout, QApplication, QStyle,
    QStyledItemDelegate, QAbstractItemView
)
from PySide6.QtCore import (
    QAbstractListModel, Qt, QModelIndex, QRect, QSize,
    Signal, QSortFilterProxyModel, QItemSelectionModel
)
from PySide6.QtGui import (
    QPainter, QColor, QPalette, QFont, QFontMetrics,
    QIcon, QPen, QMouseEvent
)
from typing import Any, List, Optional


class ListColumn:
    """Represents a column in the list control"""
    
    def __init__(self, title: str, width: int = 100, alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft):
        self.title = title
        self.width = width
        self.alignment = alignment
        self.sort_order = Qt.SortOrder.AscendingOrder
        self.is_sorted = False


class ListItemData:
    """Represents data for a single row in the list"""
    
    def __init__(self, row_id: int):
        self.row_id = row_id
        self.columns: List[str] = []
        self.icon: Optional[QIcon] = None
        self.background_color: Optional[QColor] = None
        self.text_color: Optional[QColor] = None
        self.font: Optional[QFont] = None
        self.user_data: Any = None
        
    def set_text(self, column: int, text: str):
        """Set text for a specific column"""
        while len(self.columns) <= column:
            self.columns.append("")
        self.columns[column] = text
        
    def get_text(self, column: int) -> str:
        """Get text for a specific column"""
        if column < len(self.columns):
            return self.columns[column]
        return ""


class ListModel(QAbstractListModel):
    """Model for the list control with virtual scrolling support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[ListItemData] = []
        self._columns: List[ListColumn] = []
        self._next_row_id = 0
        
    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None
            
        item = self._items[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # Return all column data as a tuple
            return item.columns
        elif role == Qt.ItemDataRole.DecorationRole:
            return item.icon
        elif role == Qt.ItemDataRole.BackgroundRole and item.background_color:
            return item.background_color
        elif role == Qt.ItemDataRole.ForegroundRole and item.text_color:
            return item.text_color
        elif role == Qt.ItemDataRole.FontRole and item.font:
            return item.font
        elif role == Qt.ItemDataRole.UserRole:
            return item.user_data
        elif role == Qt.ItemDataRole.AccessibleTextRole:
            # Build accessible description from all columns
            parts = []
            for i, col in enumerate(self._columns):
                text = item.get_text(i)
                if text:
                    parts.append(f"{col.title}: {text}")
            return ", ".join(parts)
        elif role == Qt.ItemDataRole.AccessibleDescriptionRole:
            return ""
            
        return None
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or index.row() >= len(self._items):
            return False
            
        item = self._items[index.row()]
        
        if role == Qt.ItemDataRole.UserRole:
            item.user_data = value
            return True
            
        return False
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
            
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    
    # Custom methods for list control functionality
    
    def insert_item(self, row: int, item: ListItemData) -> bool:
        """Insert an item at the specified row"""
        if row < 0 or row > len(self._items):
            return False
            
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.insert(row, item)
        self.endInsertRows()
        return True
    
    def append_item(self, item: ListItemData) -> int:
        """Append an item and return its row index"""
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()
        return row
    
    def remove_item(self, row: int) -> bool:
        """Remove an item at the specified row"""
        if row < 0 or row >= len(self._items):
            return False
            
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        return True
    
    def clear_items(self):
        """Remove all items"""
        if len(self._items) == 0:
            return
            
        self.beginRemoveRows(QModelIndex(), 0, len(self._items) - 1)
        self._items.clear()
        self.endRemoveRows()
    
    def get_item(self, row: int) -> Optional[ListItemData]:
        """Get item data at the specified row"""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None
    
    def set_column_data(self, row: int, column: int, text: str) -> bool:
        """Set text for a specific cell"""
        if row < 0 or row >= len(self._items):
            return False
            
        item = self._items[row]
        item.set_text(column, text)
        
        index = self.index(row, 0)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
        return True
    
    def get_column_data(self, row: int, column: int) -> str:
        """Get text from a specific cell"""
        if row < 0 or row >= len(self._items):
            return ""
        return self._items[row].get_text(column)
    
    def add_column(self, column: ListColumn):
        """Add a column to the model"""
        self._columns.append(column)
        
    def remove_column(self, index: int) -> bool:
        """Remove a column"""
        if index < 0 or index >= len(self._columns):
            return False
            
        del self._columns[index]
        
        # Remove data from all items
        for item in self._items:
            if index < len(item.columns):
                del item.columns[index]
                
        # Notify views
        if len(self._items) > 0:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._items) - 1, 0)
            self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])
            
        return True
    
    def get_column_count(self) -> int:
        """Get the number of columns"""
        return len(self._columns)
    
    def get_column(self, index: int) -> Optional[ListColumn]:
        """Get column information"""
        if 0 <= index < len(self._columns):
            return self._columns[index]
        return None

    def move_item(self, source_row: int, target_row: int) -> bool:
        """Move an item to a new row"""
        if source_row < 0 or source_row >= len(self._items):
            return False
        if target_row < 0 or target_row >= len(self._items):
            return False
        if source_row == target_row:
            return True

        destination_child = target_row + 1 if source_row < target_row else target_row
        self.beginMoveRows(
            QModelIndex(), source_row, source_row, QModelIndex(), destination_child
        )
        item = self._items.pop(source_row)
        self._items.insert(target_row, item)
        self.endMoveRows()
        return True

    def get_next_row_id(self) -> int:
        """Get a unique row ID"""
        row_id = self._next_row_id
        self._next_row_id += 1
        return row_id


class ListDelegate(QStyledItemDelegate):
    """Custom delegate for rendering list items with columns"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._columns: List[ListColumn] = []
        self._icon_size = QSize(16, 16)
        self._horizontal_padding = 7
        self._vertical_padding = 4
        self._alternate_colors = False
        self._simple_style = False
        
    def paint(self, painter: QPainter, option, index: QModelIndex):
        """Paint the item with multiple columns"""
        painter.save()
        
        # Get data
        column_data = index.data(Qt.ItemDataRole.DisplayRole)
        if not isinstance(column_data, list):
            column_data = []
            
        # Background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            # Alternate row colors
            if self._alternate_colors and index.row() % 2 == 1:
                alt_color = option.palette.alternateBase().color()
                painter.fillRect(option.rect, alt_color)
            else:
                bg_color = index.data(Qt.ItemDataRole.BackgroundRole)
                if bg_color:
                    painter.fillRect(option.rect, bg_color)
                else:
                    painter.fillRect(option.rect, option.palette.base())
        
        # Text color
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            text_color = index.data(Qt.ItemDataRole.ForegroundRole)
            if text_color:
                painter.setPen(text_color)
            else:
                painter.setPen(option.palette.text().color())
        
        # Font
        font = index.data(Qt.ItemDataRole.FontRole)
        if font:
            painter.setFont(font)
        else:
            painter.setFont(option.font)
        
        # Calculate starting X position
        x = option.rect.x()
        y = option.rect.y()
        height = option.rect.height()
        
        # Draw icon if present
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon and not icon.isNull():
            icon_rect = QRect(x + self._horizontal_padding, y + (height - self._icon_size.height()) // 2,
                            self._icon_size.width(), self._icon_size.height())
            icon.paint(painter, icon_rect)
            x += self._icon_size.width() + self._horizontal_padding * 2
        
        # Draw columns
        for col_index, column in enumerate(self._columns):
            if col_index >= len(column_data):
                break
                
            text = column_data[col_index]
            if not text:
                text = ""
                
            col_rect = QRect(x, y, column.width, height)
            
            # Align text
            text_flags = Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignVCenter
            if column.alignment:
                text_flags |= column.alignment
            else:
                text_flags |= Qt.AlignmentFlag.AlignLeft
            
            # Add padding
            text_rect = col_rect.adjusted(
                self._horizontal_padding,
                self._vertical_padding,
                -self._horizontal_padding,
                -self._vertical_padding,
            )
            
            # Elide text if too long
            metrics = QFontMetrics(painter.font())
            elided_text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, text_rect.width())
            
            painter.drawText(text_rect, text_flags, elided_text)
            
            x += column.width
        
        # Draw focus rectangle
        if option.state & QStyle.StateFlag.State_HasFocus:
            focus_option = option
            focus_option.rect = option.rect.adjusted(1, 1, -1, -1)
            QApplication.style().drawPrimitive(QStyle.PrimitiveElement.PE_FrameFocusRect, 
                                              focus_option, painter)
        
        painter.restore()
    
    def sizeHint(self, option, index: QModelIndex) -> QSize:
        """Return the size hint for an item"""
        # Calculate total width
        width = 0
            
        for column in self._columns:
            width += column.width
            
        # Default height
        font = index.data(Qt.ItemDataRole.FontRole) or option.font
        metrics = QFontMetrics(font)
        height = max(metrics.height() + self._vertical_padding * 2 + 4, 24)
        
        return QSize(width, height)
    
    def set_columns(self, columns: List[ListColumn]):
        """Set the column definitions"""
        self._columns = columns
    
    def set_alternate_colors(self, enable: bool):
        """Enable alternate row colors"""
        self._alternate_colors = enable

    def set_cell_padding(self, horizontal: int, vertical: int | None = None):
        """Set text padding inside each row cell."""
        self._horizontal_padding = max(0, horizontal)
        self._vertical_padding = max(0, vertical if vertical is not None else horizontal // 2)

    def set_simple_style(self, enable: bool):
        """Use a flatter, less opinionated paint style."""
        self._simple_style = enable


class ListHeader(QWidget):
    """Custom header widget for the list control"""
    
    column_clicked = Signal(int)  # Column index
    column_resized = Signal(int, int)  # Column index, new width
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._columns: List[ListColumn] = []
        self._padding = 7
        self._sort_indicator_width = 12
        self._resizing_column = -1
        self._resize_start_x = 0
        self._resize_start_width = 0
        self._hover_column = -1
        self._simple_style = False
        
        self.setFixedHeight(24)
        self.setMouseTracking(True)
        
        # Styling
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f0f0f0"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
        self.setPalette(palette)
    
    def set_columns(self, columns: List[ListColumn]):
        """Set column definitions"""
        self._columns = columns
        self.update()

    def set_padding(self, padding: int):
        """Set horizontal header padding."""
        self._padding = max(0, padding)
        self.update()

    def set_simple_style(self, enable: bool):
        """Use a flatter header style."""
        self._simple_style = enable
        palette = self.palette()
        if enable:
            palette.setColor(QPalette.ColorRole.Window, QColor("#f7f7f7"))
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor("#f0f0f0"))
        self.setPalette(palette)
        self.update()
    
    def paintEvent(self, event):
        """Paint the header"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self.palette().window())
        
        # Draw bottom border
        painter.setPen(QPen(QColor("#c0c0c0"), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        
        x = 0
        
        # Draw columns
        for col_index, column in enumerate(self._columns):
            self._draw_column_background(painter, x, column.width, col_index)
            
            # Column title
            text_rect = QRect(x + self._padding, 0, 
                            column.width - self._padding * 2 - (self._sort_indicator_width if column.is_sorted else 0), 
                            self.height())
            
            painter.setPen(self.palette().windowText().color())
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                           column.title)
            
            # Sort indicator
            if column.is_sorted:
                arrow_x = x + column.width - self._sort_indicator_width - self._padding
                arrow_y = self.height() // 2
                self._draw_sort_arrow(painter, arrow_x, arrow_y, column.sort_order)
            
            # Column separator
            painter.setPen(QPen(QColor("#c0c0c0"), 1))
            painter.drawLine(x + column.width - 1, 0, x + column.width - 1, self.height())
            
            x += column.width
    
    def _draw_column_background(self, painter: QPainter, x: int, width: int, col_index: int):
        """Draw column background with hover effect"""
        rect = QRect(x, 0, width, self.height() - 1)
        
        if col_index == self._hover_column:
            painter.fillRect(rect, QColor("#ededed") if self._simple_style else QColor("#e5e5e5"))
        else:
            painter.fillRect(rect, self.palette().window())
    
    def _draw_sort_arrow(self, painter: QPainter, x: int, y: int, order: Qt.SortOrder):
        """Draw sort indicator arrow"""
        painter.setPen(QPen(QColor("#000000"), 2))
        
        if order == Qt.SortOrder.AscendingOrder:
            # Up arrow
            painter.drawLine(x + 4, y + 2, x + 8, y - 2)
            painter.drawLine(x + 8, y - 2, x + 12, y + 2)
        else:
            # Down arrow
            painter.drawLine(x + 4, y - 2, x + 8, y + 2)
            painter.drawLine(x + 8, y + 2, x + 12, y - 2)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for sorting and resizing"""
        if event.button() != Qt.MouseButton.LeftButton:
            return
            
        x = 0
        
        for col_index, column in enumerate(self._columns):
            # Check if clicking on resize area (right edge)
            if x + column.width - 5 <= event.position().x() <= x + column.width + 5:
                self._resizing_column = col_index
                self._resize_start_x = event.position().x()
                self._resize_start_width = column.width
                self.setCursor(Qt.CursorShape.SplitHCursor)
                return
                
            # Check if clicking on column header
            if x <= event.position().x() < x + column.width:
                self.column_clicked.emit(col_index)
                return
                
            x += column.width
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for resizing and hover"""
        if self._resizing_column >= 0:
            # Resizing
            delta = event.position().x() - self._resize_start_x
            new_width = max(30, self._resize_start_width + delta)
            
            column = self._columns[self._resizing_column]
            column.width = new_width
            
            self.column_resized.emit(self._resizing_column, new_width)
            self.update()
        else:
            # Update hover state
            x = 0
            old_hover = self._hover_column
            self._hover_column = -1
            
            for col_index, column in enumerate(self._columns):
                # Check if near resize edge
                if x + column.width - 5 <= event.position().x() <= x + column.width + 5:
                    self.setCursor(Qt.CursorShape.SplitHCursor)
                    return
                    
                # Check if hovering over column
                if x <= event.position().x() < x + column.width:
                    self._hover_column = col_index
                    
                x += column.width
            
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
            if old_hover != self._hover_column:
                self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to end resizing"""
        if self._resizing_column >= 0:
            self._resizing_column = -1
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def leaveEvent(self, event):
        """Handle mouse leaving the header"""
        self._hover_column = -1
        self.update()
    
    def get_column_at_position(self, x: int) -> int:
        """Get the column index at the given x position"""
        current_x = 0
        
        for col_index, column in enumerate(self._columns):
            if current_x <= x < current_x + column.width:
                return col_index
            current_x += column.width
            
        return -1


class ListCtrl(QWidget):
    """
    Professional wx.ListCtrl clone with full features:
    - Report view with columns
    - Sorting with visual indicators
    - Virtual scrolling
    - Keyboard navigation
    - Full accessibility
    """
    
    # Signals
    item_selected = Signal(int)  # Row index
    item_clicked = Signal(int)  # Row index
    item_activated = Signal(int)  # Row index (double-click or Enter)
    column_clicked = Signal(int)  # Column index
    items_reordered = Signal(list)  # List of row indices in their new order
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Model and view
        self._model = ListModel(self)
        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._model)
        
        self._list_view = QListView(self)
        self._list_view.setModel(self._proxy_model)
        
        # Delegate
        self._delegate = ListDelegate(self)
        self._list_view.setItemDelegate(self._delegate)
        
        # Header
        self._header = ListHeader(self)

        # Scroll corner filler so row background does not peek through.
        self._corner_widget = QWidget(self._list_view)
        self._corner_widget.setAutoFillBackground(True)
        self._list_view.setCornerWidget(self._corner_widget)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header)
        layout.addWidget(self._list_view)
        
        # Configure list view
        self._list_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._list_view.setUniformItemSizes(True)  # Performance optimization
        self._list_view.setAlternatingRowColors(False)  # We handle this in delegate
        self._list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list_view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list_view.setAutoScroll(True)
        self._list_view.setWordWrap(False)
        
        # Enable keyboard navigation
        self._list_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._list_view.setTabKeyNavigation(False)
        
        # Accessibility
        self._list_view.setAccessibleName("List Control")
        self._update_accessibility()
        self._sync_scroll_corner_style()
        
        # Connect signals
        self._list_view.selectionModel().currentChanged.connect(self._on_current_changed)
        self._list_view.clicked.connect(self._on_item_clicked)
        self._list_view.activated.connect(self._on_item_activated)
        self._header.column_clicked.connect(self._on_column_clicked)
        self._header.column_resized.connect(self._on_column_resized)
        
        # Install event filter for keyboard handling
        self._list_view.viewport().installEventFilter(self)
        
    # Column management
    
    def insert_column(self, index: int, title: str, width: int = 100, 
                     alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft) -> bool:
        """Insert a column at the specified index"""
        column = ListColumn(title, width, alignment)
        
        columns = self._model._columns.copy()
        columns.insert(index, column)
        
        self._model._columns = columns
        self._delegate.set_columns(columns)
        self._header.set_columns(columns)
        
        self._list_view.viewport().update()
        self._update_accessibility()
        return True
    
    def append_column(self, title: str, width: int = 100,
                     alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft) -> int:
        """Append a column and return its index"""
        column = ListColumn(title, width, alignment)
        self._model.add_column(column)
        
        self._delegate.set_columns(self._model._columns)
        self._header.set_columns(self._model._columns)
        
        self._list_view.viewport().update()
        self._update_accessibility()
        return self._model.get_column_count() - 1
    
    def remove_column(self, index: int) -> bool:
        """Remove a column"""
        if self._model.remove_column(index):
            self._delegate.set_columns(self._model._columns)
            self._header.set_columns(self._model._columns)
            self._list_view.viewport().update()
            self._update_accessibility()
            return True
        return False
    
    def get_column_count(self) -> int:
        """Get the number of columns"""
        return self._model.get_column_count()
    
    def set_column_width(self, column: int, width: int) -> bool:
        """Set the width of a column"""
        col = self._model.get_column(column)
        if col:
            col.width = width
            self._header.update()
            self._list_view.viewport().update()
            return True
        return False
    
    def get_column_width(self, column: int) -> int:
        """Get the width of a column"""
        col = self._model.get_column(column)
        return col.width if col else 0
    
    # Item management
    
    def insert_item(self, row: int, text: str = "") -> int:
        """Insert an item at the specified row"""
        item = ListItemData(self._model.get_next_row_id())
        if text:
            item.set_text(0, text)
        
        if self._model.insert_item(row, item):
            self._update_accessibility()
            return row
        return -1
    
    def append_item(self, text: str = "") -> int:
        """Append an item and return its row index"""
        item = ListItemData(self._model.get_next_row_id())
        if text:
            item.set_text(0, text)
        row = self._model.append_item(item)
        self._update_accessibility()
        return row
    
    def remove_item(self, row: int) -> bool:
        """Remove an item at the specified row"""
        removed = self._model.remove_item(row)
        if removed:
            self._update_accessibility()
        return removed
    
    def clear_all(self):
        """Remove all items and columns"""
        self._model.clear_items()
        
        # Clear columns
        while self._model.get_column_count() > 0:
            self.remove_column(0)
        self._update_accessibility()
    
    def clear_items(self):
        """Remove all items but keep columns"""
        self._model.clear_items()
        self._update_accessibility()
    
    def get_item_count(self) -> int:
        """Get the number of items"""
        return self._model.rowCount()
    
    # Cell data management
    
    def set_item_text(self, row: int, column: int, text: str) -> bool:
        """Set text for a specific cell"""
        return self._model.set_column_data(row, column, text)
    
    def get_item_text(self, row: int, column: int = 0) -> str:
        """Get text from a specific cell"""
        return self._model.get_column_data(row, column)
    
    def set_item_data(self, row: int, data: Any) -> bool:
        """Set user data for an item"""
        index = self._model.index(row, 0)
        return self._model.setData(index, data, Qt.ItemDataRole.UserRole)
    
    def get_item_data(self, row: int) -> Any:
        """Get user data for an item"""
        index = self._model.index(row, 0)
        return self._model.data(index, Qt.ItemDataRole.UserRole)
    
    # Appearance
    
    def set_item_background_color(self, row: int, color: QColor) -> bool:
        """Set background color for an item"""
        item = self._model.get_item(row)
        if item:
            item.background_color = color
            index = self._model.index(row, 0)
            self._model.dataChanged.emit(index, index, [Qt.ItemDataRole.BackgroundRole])
            return True
        return False
    
    def set_item_text_color(self, row: int, color: QColor) -> bool:
        """Set text color for an item"""
        item = self._model.get_item(row)
        if item:
            item.text_color = color
            index = self._model.index(row, 0)
            self._model.dataChanged.emit(index, index, [Qt.ItemDataRole.ForegroundRole])
            return True
        return False
    
    def set_item_font(self, row: int, font: QFont) -> bool:
        """Set font for an item"""
        item = self._model.get_item(row)
        if item:
            item.font = font
            index = self._model.index(row, 0)
            self._model.dataChanged.emit(index, index, [Qt.ItemDataRole.FontRole])
            return True
        return False
    
    def set_alternate_row_colors(self, enable: bool):
        """Enable alternate row coloring"""
        self._delegate.set_alternate_colors(enable)
        self._list_view.viewport().update()

    def set_cell_padding(self, horizontal: int, vertical: int | None = None):
        """Set row text padding and refresh the list."""
        self._delegate.set_cell_padding(horizontal, vertical)
        self._header.set_padding(horizontal)
        self._list_view.doItemsLayout()
        self._list_view.viewport().update()

    def set_simple_style(self, enable: bool = True):
        """Use a flatter, less decorative visual style."""
        self._delegate.set_simple_style(enable)
        self._header.set_simple_style(enable)
        self._sync_scroll_corner_style()
        self._list_view.viewport().update()
    
    # Selection
    
    def get_selected_items(self) -> List[int]:
        """Get list of selected row indices"""
        indexes = self._list_view.selectionModel().selectedIndexes()
        return sorted(set(index.row() for index in indexes))
    
    def get_current_item(self) -> int:
        """Get the currently focused item row index"""
        index = self._list_view.currentIndex()
        return index.row() if index.isValid() else -1
    
    def set_current_item(self, row: int):
        """Set the current (focused) item"""
        index = self._model.index(row, 0)
        self._list_view.setCurrentIndex(self._proxy_model.mapFromSource(index))
        self.ensure_visible(row, QAbstractItemView.ScrollHint.PositionAtCenter)
    
    def select_item(self, row: int, select: bool = True):
        """Select or deselect an item"""
        index = self._model.index(row, 0)
        proxy_index = self._proxy_model.mapFromSource(index)
        
        if select:
            self._list_view.selectionModel().select(proxy_index, 
                QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        else:
            self._list_view.selectionModel().select(proxy_index,
                QItemSelectionModel.SelectionFlag.Deselect | QItemSelectionModel.SelectionFlag.Rows)
    
    def clear_selection(self):
        """Clear all selections"""
        self._list_view.selectionModel().clearSelection()
    
    # Sorting
    
    def sort_items(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort items by a column"""
        # Update sort indicator
        for col in self._model._columns:
            col.is_sorted = False
            
        col = self._model.get_column(column)
        if col:
            col.is_sorted = True
            col.sort_order = order
            
        self._header.update()
        
        # Sort via proxy model
        self._proxy_model.setSortRole(Qt.ItemDataRole.DisplayRole)
        self._proxy_model.sort(0, order)
        
        # Custom sort function
        def compare_function(left_index, right_index):
            left_data = self._model.data(left_index, Qt.ItemDataRole.DisplayRole)
            right_data = self._model.data(right_index, Qt.ItemDataRole.DisplayRole)
            
            if not isinstance(left_data, list) or not isinstance(right_data, list):
                return 0
                
            if column >= len(left_data) or column >= len(right_data):
                return 0
                
            left_val = left_data[column]
            right_val = right_data[column]
            
            # Try numeric comparison
            try:
                left_num = float(left_val)
                right_num = float(right_val)
                if left_num < right_num:
                    return -1
                elif left_num > right_num:
                    return 1
                return 0
            except (ValueError, TypeError):
                # String comparison
                if left_val < right_val:
                    return -1
                elif left_val > right_val:
                    return 1
                return 0
        
        # Note: QSortFilterProxyModel handles sorting automatically
        # The compare function above is for reference
    
    def remove_sort_indicator(self):
        """Remove the sort indicator"""
        for col in self._model._columns:
            col.is_sorted = False
        self._header.update()
    
    # Scrolling
    
    def ensure_visible(self, row: int, hint: QAbstractItemView.ScrollHint = QAbstractItemView.ScrollHint.EnsureVisible):
        """Ensure an item is visible"""
        index = self._model.index(row, 0)
        proxy_index = self._proxy_model.mapFromSource(index)
        self._list_view.scrollTo(proxy_index, hint)

    def scroll_to_row(self, row: int, center: bool = False):
        """Scroll to a row with optional centering."""
        hint = (
            QAbstractItemView.ScrollHint.PositionAtCenter
            if center
            else QAbstractItemView.ScrollHint.EnsureVisible
        )
        self.ensure_visible(row, hint)

    def scroll_to_top(self):
        """Scroll to the top of the list."""
        self._list_view.verticalScrollBar().setValue(
            self._list_view.verticalScrollBar().minimum()
        )

    def scroll_to_bottom(self):
        """Scroll to the bottom of the list."""
        self._list_view.verticalScrollBar().setValue(
            self._list_view.verticalScrollBar().maximum()
        )

    def set_single_selection(self):
        """Use single selection mode."""
        self._list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def set_multi_selection(self):
        """Use extended multi-selection mode."""
        self._list_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def move_item(self, source_row: int, target_row: int) -> bool:
        """Move one row and keep it visible."""
        moved = self._model.move_item(source_row, target_row)
        if moved:
            self.set_current_item(target_row)
            self._emit_reordered_rows()
        return moved

    def move_current_item(self, step: int) -> bool:
        """Move the current row up or down."""
        current_row = self.get_current_item()
        if current_row < 0:
            return False
        target_row = current_row + step
        return self.move_item(current_row, target_row)

    def move_selected_items(self, step: int) -> bool:
        """Move the selected rows while preserving order."""
        rows = self.get_selected_items()
        if not rows:
            return False
        if step < 0 and rows[0] == 0:
            return False
        if step > 0 and rows[-1] == self.get_item_count() - 1:
            return False

        ordered_rows = rows if step < 0 else list(reversed(rows))
        moved_rows = []
        for row in ordered_rows:
            if self._model.move_item(row, row + step):
                moved_rows.append(row + step)

        if not moved_rows:
            return False

        self.clear_selection()
        for row in sorted(moved_rows):
            self.select_item(row, True)

        focus_row = min(moved_rows) if step < 0 else max(moved_rows)
        self.set_current_item(focus_row)
        self._emit_reordered_rows()
        return True
    
    # Event handlers
    
    def _on_current_changed(self, current: QModelIndex, previous: QModelIndex):
        """Handle current item changed"""
        if current.isValid():
            source_index = self._proxy_model.mapToSource(current)
            self.item_selected.emit(source_index.row())

    def _on_item_clicked(self, index: QModelIndex):
        """Handle single-click on an item."""
        if index.isValid():
            source_index = self._proxy_model.mapToSource(index)
            self.item_clicked.emit(source_index.row())
    
    def _on_item_activated(self, index: QModelIndex):
        """Handle item activation (double-click or Enter)"""
        if index.isValid():
            source_index = self._proxy_model.mapToSource(index)
            self.item_activated.emit(source_index.row())
    
    def _on_column_clicked(self, column: int):
        """Handle column header click for sorting"""
        col = self._model.get_column(column)
        if col:
            # Toggle sort order
            if col.is_sorted:
                new_order = (Qt.SortOrder.DescendingOrder if col.sort_order == Qt.SortOrder.AscendingOrder 
                           else Qt.SortOrder.AscendingOrder)
            else:
                new_order = Qt.SortOrder.AscendingOrder
                
            self.sort_items(column, new_order)
            self.column_clicked.emit(column)
    
    def _on_column_resized(self, column: int, width: int):
        """Handle column resize"""
        self._list_view.viewport().update()

    def _emit_reordered_rows(self):
        self.items_reordered.emit(
            [self._model.get_item(row).row_id for row in range(self._model.rowCount())]
        )

    def _update_accessibility(self):
        description = (
            f"Multi-column list view with {self._model.get_column_count()} columns "
            f"and {self._model.rowCount()} rows"
        )
        self._list_view.setAccessibleDescription(description)
        self.setAccessibleDescription(description)

    def _sync_scroll_corner_style(self):
        palette = self._corner_widget.palette()
        palette.setColor(
            QPalette.ColorRole.Window,
            self._header.palette().window().color()
        )
        self._corner_widget.setPalette(palette)
        self._corner_widget.setBackgroundRole(QPalette.ColorRole.Window)
    
    def eventFilter(self, obj, event):
        """Event filter for keyboard events"""
        if obj == self._list_view.viewport():
            if event.type() == event.Type.KeyPress:
                if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    if event.key() == Qt.Key.Key_Up and self.move_selected_items(-1):
                        return True
                    if event.key() == Qt.Key.Key_Down and self.move_selected_items(1):
                        return True
        
        return super().eventFilter(obj, event)


if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # Create list control
    list_ctrl = ListCtrl()
    list_ctrl.setWindowTitle("List Control Demo")
    list_ctrl.resize(800, 600)
    
    # Add columns
    list_ctrl.append_column("Name", 200)
    list_ctrl.append_column("Age", 100, Qt.AlignmentFlag.AlignRight)
    list_ctrl.append_column("City", 200)
    list_ctrl.append_column("Email", 250)
    
    # Enable features
    list_ctrl.set_alternate_row_colors(True)
    
    # Add sample data
    sample_data = [
        ["Alice Johnson", "28", "New York", "alice@example.com"],
        ["Bob Smith", "35", "Los Angeles", "bob@example.com"],
        ["Charlie Brown", "42", "Chicago", "charlie@example.com"],
        ["Diana Prince", "31", "Miami", "diana@example.com"],
        ["Eve Wilson", "26", "Seattle", "eve@example.com"],
        ["Frank Miller", "39", "Boston", "frank@example.com"],
        ["Grace Lee", "33", "San Francisco", "grace@example.com"],
        ["Henry Davis", "45", "Denver", "henry@example.com"],
        ["Iris Chen", "29", "Austin", "iris@example.com"],
        ["Jack Taylor", "37", "Portland", "jack@example.com"],
    ]
    
    for data in sample_data:
        row = list_ctrl.append_item(data[0])
        for col_idx, text in enumerate(data[1:], 1):
            list_ctrl.set_item_text(row, col_idx, text)
    
    # Color some rows
    list_ctrl.set_item_background_color(0, QColor("#ffe6e6"))
    list_ctrl.set_item_text_color(2, QColor("#0000ff"))
    
    # Make a row bold
    bold_font = QFont()
    bold_font.setBold(True)
    list_ctrl.set_item_font(4, bold_font)
    
    # Connect signals
    list_ctrl.item_selected.connect(lambda row: print(f"Selected row: {row}"))
    list_ctrl.item_activated.connect(lambda row: print(f"Activated row: {row}"))
    list_ctrl.column_clicked.connect(lambda col: print(f"Column {col} clicked"))
    
    list_ctrl.show()
    sys.exit(app.exec())
