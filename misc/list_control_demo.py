"""
Comprehensive demonstration of the ListCtrl widget
Shows all features including:
- Column management
- Item operations
- Sorting
- Styling
- Keyboard navigation
- Accessibility
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QSpinBox, QColorDialog, QComboBox,
    QGroupBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from list_control import ListCtrl


class ListCtrlDemo(QMainWindow):
    """Demo application showcasing all ListCtrl features"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional ListCtrl Demo")
        self.resize(1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QHBoxLayout(central)
        
        # Left side: List control
        self.list_ctrl = ListCtrl()
        main_layout.addWidget(self.list_ctrl, stretch=2)
        
        # Right side: Controls
        controls_layout = QVBoxLayout()
        main_layout.addLayout(controls_layout, stretch=1)
        
        # Setup controls
        self._setup_column_controls(controls_layout)
        self._setup_item_controls(controls_layout)
        self._setup_style_controls(controls_layout)
        self._setup_feature_controls(controls_layout)
        
        controls_layout.addStretch()
        
        # Initialize with sample data
        self._setup_sample_data()
        
        # Connect signals
        self._connect_signals()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label)
    
    def _setup_column_controls(self, parent_layout):
        """Setup column management controls"""
        group = QGroupBox("Column Management")
        layout = QVBoxLayout(group)
        
        # Add column
        add_layout = QHBoxLayout()
        self.col_name_input = QLineEdit()
        self.col_name_input.setPlaceholderText("Column name")
        add_layout.addWidget(self.col_name_input)
        
        self.col_width_input = QSpinBox()
        self.col_width_input.setRange(50, 500)
        self.col_width_input.setValue(150)
        self.col_width_input.setSuffix(" px")
        add_layout.addWidget(self.col_width_input)
        
        add_btn = QPushButton("Add Column")
        add_btn.clicked.connect(self._add_column)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        # Remove column
        remove_layout = QHBoxLayout()
        self.col_index_input = QSpinBox()
        self.col_index_input.setRange(0, 10)
        self.col_index_input.setPrefix("Index: ")
        remove_layout.addWidget(self.col_index_input)
        
        remove_btn = QPushButton("Remove Column")
        remove_btn.clicked.connect(self._remove_column)
        remove_layout.addWidget(remove_btn)
        layout.addLayout(remove_layout)
        
        # Info
        self.col_count_label = QLabel("Columns: 0")
        layout.addWidget(self.col_count_label)
        
        parent_layout.addWidget(group)
    
    def _setup_item_controls(self, parent_layout):
        """Setup item management controls"""
        group = QGroupBox("Item Management")
        layout = QVBoxLayout(group)
        
        # Add item
        add_layout = QHBoxLayout()
        self.item_text_input = QLineEdit()
        self.item_text_input.setPlaceholderText("Item text")
        add_layout.addWidget(self.item_text_input)
        
        add_btn = QPushButton("Add Item")
        add_btn.clicked.connect(self._add_item)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        # Remove item
        remove_layout = QHBoxLayout()
        self.item_index_input = QSpinBox()
        self.item_index_input.setRange(0, 1000)
        self.item_index_input.setPrefix("Row: ")
        remove_layout.addWidget(self.item_index_input)
        
        remove_btn = QPushButton("Remove Item")
        remove_btn.clicked.connect(self._remove_item)
        remove_layout.addWidget(remove_btn)
        layout.addLayout(remove_layout)
        
        # Clear buttons
        btn_layout = QHBoxLayout()
        clear_items_btn = QPushButton("Clear Items")
        clear_items_btn.clicked.connect(self.list_ctrl.clear_items)
        btn_layout.addWidget(clear_items_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.list_ctrl.clear_all)
        btn_layout.addWidget(clear_all_btn)
        layout.addLayout(btn_layout)
        
        # Info
        self.item_count_label = QLabel("Items: 0")
        layout.addWidget(self.item_count_label)
        
        self.selected_label = QLabel("Selected: None")
        layout.addWidget(self.selected_label)
        
        parent_layout.addWidget(group)
    
    def _setup_style_controls(self, parent_layout):
        """Setup styling controls"""
        group = QGroupBox("Styling")
        layout = QVBoxLayout(group)
        
        # Row color
        color_layout = QHBoxLayout()
        self.row_input = QSpinBox()
        self.row_input.setRange(0, 1000)
        self.row_input.setPrefix("Row: ")
        color_layout.addWidget(self.row_input)
        
        bg_color_btn = QPushButton("BG Color")
        bg_color_btn.clicked.connect(self._set_bg_color)
        color_layout.addWidget(bg_color_btn)
        
        text_color_btn = QPushButton("Text Color")
        text_color_btn.clicked.connect(self._set_text_color)
        color_layout.addWidget(text_color_btn)
        layout.addLayout(color_layout)
        
        # Font
        font_layout = QHBoxLayout()
        bold_btn = QPushButton("Bold")
        bold_btn.clicked.connect(self._make_bold)
        font_layout.addWidget(bold_btn)
        
        italic_btn = QPushButton("Italic")
        italic_btn.clicked.connect(self._make_italic)
        font_layout.addWidget(italic_btn)
        layout.addLayout(font_layout)
        
        parent_layout.addWidget(group)
    
    def _setup_feature_controls(self, parent_layout):
        """Setup feature toggles"""
        group = QGroupBox("Features")
        layout = QVBoxLayout(group)
        
        # Alternate colors
        self.alternate_toggle = QCheckBox("Alternate Row Colors")
        self.alternate_toggle.toggled.connect(self.list_ctrl.set_alternate_row_colors)
        layout.addWidget(self.alternate_toggle)
        
        # Sorting
        sort_layout = QHBoxLayout()
        sort_label = QLabel("Sort by column:")
        sort_layout.addWidget(sort_label)
        
        self.sort_column = QSpinBox()
        self.sort_column.setRange(0, 10)
        sort_layout.addWidget(self.sort_column)
        
        sort_btn = QPushButton("Sort")
        sort_btn.clicked.connect(self._sort_items)
        sort_layout.addWidget(sort_btn)
        layout.addLayout(sort_layout)
        
        # Actions
        show_selected_btn = QPushButton("Show Selected Items")
        show_selected_btn.clicked.connect(self._show_selected)
        layout.addWidget(show_selected_btn)
        
        parent_layout.addWidget(group)
    
    def _setup_sample_data(self):
        """Initialize with sample data"""
        # Add columns
        self.list_ctrl.append_column("Name", 180)
        self.list_ctrl.append_column("Age", 80, Qt.AlignmentFlag.AlignRight)
        self.list_ctrl.append_column("Department", 150)
        self.list_ctrl.append_column("Email", 220)
        self.list_ctrl.append_column("Status", 100)
        
        self.list_ctrl.set_alternate_row_colors(True)
        self.alternate_toggle.setChecked(True)
        
        # Sample data
        employees = [
            ["Alice Johnson", "28", "Engineering", "alice.j@company.com", "Active"],
            ["Bob Smith", "35", "Marketing", "bob.s@company.com", "Active"],
            ["Charlie Brown", "42", "Sales", "charlie.b@company.com", "On Leave"],
            ["Diana Prince", "31", "Engineering", "diana.p@company.com", "Active"],
            ["Eve Wilson", "26", "HR", "eve.w@company.com", "Active"],
            ["Frank Miller", "39", "Finance", "frank.m@company.com", "Active"],
            ["Grace Lee", "33", "Engineering", "grace.l@company.com", "Remote"],
            ["Henry Davis", "45", "Operations", "henry.d@company.com", "Active"],
            ["Iris Chen", "29", "Design", "iris.c@company.com", "Active"],
            ["Jack Taylor", "37", "Engineering", "jack.t@company.com", "Active"],
            ["Karen White", "32", "Marketing", "karen.w@company.com", "Active"],
            ["Leo Martinez", "41", "Sales", "leo.m@company.com", "Active"],
            ["Mary Johnson", "27", "HR", "mary.j@company.com", "Part-time"],
            ["Nathan Green", "36", "Finance", "nathan.g@company.com", "Active"],
            ["Olivia Brown", "30", "Engineering", "olivia.b@company.com", "Remote"],
        ]
        
        for emp in employees:
            row = self.list_ctrl.append_item(emp[0])
            for col_idx, text in enumerate(emp[1:], 1):
                self.list_ctrl.set_item_text(row, col_idx, text)
        
        # Highlight some special cases
        # Remote workers in light blue
        for row in [6, 14]:  # Grace, Olivia
            self.list_ctrl.set_item_background_color(row, QColor("#e6f2ff"))
        
        # On leave in light yellow
        self.list_ctrl.set_item_background_color(2, QColor("#fff9e6"))
        
        # Part-time in light green
        self.list_ctrl.set_item_background_color(12, QColor("#e6ffe6"))
        
        # Engineering department in bold
        bold_font = QFont()
        bold_font.setBold(True)
        for row in [0, 3, 6, 9, 14]:
            self.list_ctrl.set_item_font(row, bold_font)
        
        self._update_counts()
    
    def _connect_signals(self):
        """Connect all signals"""
        self.list_ctrl.item_selected.connect(self._on_item_selected)
        self.list_ctrl.item_activated.connect(self._on_item_activated)
        self.list_ctrl.column_clicked.connect(self._on_column_clicked)
    
    def _add_column(self):
        """Add a new column"""
        name = self.col_name_input.text()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a column name")
            return
        
        width = self.col_width_input.value()
        self.list_ctrl.append_column(name, width)
        self.col_name_input.clear()
        self._update_counts()
        self.status_label.setText(f"Added column: {name}")
    
    def _remove_column(self):
        """Remove a column"""
        index = self.col_index_input.value()
        if self.list_ctrl.remove_column(index):
            self._update_counts()
            self.status_label.setText(f"Removed column {index}")
        else:
            QMessageBox.warning(self, "Error", f"Cannot remove column {index}")
    
    def _add_item(self):
        """Add a new item"""
        text = self.item_text_input.text()
        if not text:
            QMessageBox.warning(self, "Error", "Please enter item text")
            return
        
        row = self.list_ctrl.append_item(text)
        self.item_text_input.clear()
        self._update_counts()
        self.status_label.setText(f"Added item at row {row}")
    
    def _remove_item(self):
        """Remove an item"""
        index = self.item_index_input.value()
        if self.list_ctrl.remove_item(index):
            self._update_counts()
            self.status_label.setText(f"Removed item at row {index}")
        else:
            QMessageBox.warning(self, "Error", f"Cannot remove item {index}")
    
    def _set_bg_color(self):
        """Set background color for a row"""
        row = self.row_input.value()
        color = QColorDialog.getColor()
        if color.isValid():
            self.list_ctrl.set_item_background_color(row, color)
            self.status_label.setText(f"Set background color for row {row}")
    
    def _set_text_color(self):
        """Set text color for a row"""
        row = self.row_input.value()
        color = QColorDialog.getColor()
        if color.isValid():
            self.list_ctrl.set_item_text_color(row, color)
            self.status_label.setText(f"Set text color for row {row}")
    
    def _make_bold(self):
        """Make a row bold"""
        row = self.row_input.value()
        font = QFont()
        font.setBold(True)
        self.list_ctrl.set_item_font(row, font)
        self.status_label.setText(f"Made row {row} bold")
    
    def _make_italic(self):
        """Make a row italic"""
        row = self.row_input.value()
        font = QFont()
        font.setItalic(True)
        self.list_ctrl.set_item_font(row, font)
        self.status_label.setText(f"Made row {row} italic")
    
    def _sort_items(self):
        """Sort items by column"""
        column = self.sort_column.value()
        self.list_ctrl.sort_items(column, Qt.SortOrder.AscendingOrder)
        self.status_label.setText(f"Sorted by column {column}")
    
    def _show_selected(self):
        """Show selected items"""
        selected = self.list_ctrl.get_selected_items()
        if selected:
            items_text = ", ".join(str(i) for i in selected)
            QMessageBox.information(self, "Selected Items", 
                                  f"Selected rows: {items_text}")
        else:
            QMessageBox.information(self, "Selected Items", "No items selected")
    
    def _update_counts(self):
        """Update count labels"""
        self.col_count_label.setText(f"Columns: {self.list_ctrl.get_column_count()}")
        self.item_count_label.setText(f"Items: {self.list_ctrl.get_item_count()}")
    
    def _on_item_selected(self, row):
        """Handle item selection"""
        selected = self.list_ctrl.get_selected_items()
        if selected:
            self.selected_label.setText(f"Selected: {', '.join(map(str, selected))}")
        else:
            self.selected_label.setText("Selected: None")
        
        # Update text in status bar
        name = self.list_ctrl.get_item_text(row, 0)
        self.status_label.setText(f"Selected: Row {row} - {name}")
    
    def _on_item_activated(self, row):
        """Handle item activation (double-click or Enter)"""
        name = self.list_ctrl.get_item_text(row, 0)
        dept = self.list_ctrl.get_item_text(row, 2)
        email = self.list_ctrl.get_item_text(row, 3)
        
        QMessageBox.information(self, "Item Activated",
                              f"Row {row} activated\n\n"
                              f"Name: {name}\n"
                              f"Department: {dept}\n"
                              f"Email: {email}")
    
    def _on_column_clicked(self, column):
        """Handle column header click"""
        col = self.list_ctrl._model.get_column(column)
        if col:
            order = "ascending" if col.sort_order == Qt.SortOrder.AscendingOrder else "descending"
            self.status_label.setText(f"Sorted by column {column} ({col.title}) - {order}")


def main():
    """Run the demo application"""
    app = QApplication(sys.argv)
    
    # Set application-wide style
    app.setStyle("Fusion")
    
    demo = ListCtrlDemo()
    demo.show()
    
    # Print keyboard shortcuts
    print("\n" + "="*60)
    print("KEYBOARD SHORTCUTS AND ACCESSIBILITY FEATURES")
    print("="*60)
    print("\nNavigation:")
    print("  ↑/↓        - Navigate between items")
    print("  Home/End   - Jump to first/last item")
    print("  Page Up/Dn - Scroll by page")
    print("  Tab        - Navigate between items (alternative)")
    print("\nSelection:")
    print("  Ctrl+Click - Multi-select items")
    print("  Shift+↑/↓  - Extend selection")
    print("  Ctrl+A     - Select all (standard Qt)")
    print("\nActivation:")
    print("  Enter      - Activate item (triggers dialog)")
    print("  Double-click - Activate item")
    print("\nAccessibility:")
    print("  - Full screen reader support")
    print("  - Each row announced with all column data")
    print("  - Row position announced (e.g., 'Row 3 of 15')")
    print("  - Sort indicators visible and announced")
    print("\nColumn Headers:")
    print("  - Click to sort (toggles ascending/descending)")
    print("  - Drag right edge to resize")
    print("  - Visual sort indicators")
    print("\nPerformance:")
    print("  - Virtual scrolling (handles millions of rows)")
    print("  - Efficient model/view architecture")
    print("  - Uniform item sizes for optimal rendering")
    print("="*60 + "\n")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
