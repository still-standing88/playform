from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
import sys


class TreeViewExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TreeView with Categories and Data")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.tree_view = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Name", "Age", "Department", "Salary"])
        
        self.tree_view.setModel(self.model)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setColumnWidth(0, 200)
        self.tree_view.setColumnWidth(1, 80)
        self.tree_view.setColumnWidth(2, 150)
        self.tree_view.setColumnWidth(3, 120)
        
        layout.addWidget(self.tree_view)
        
        self.populate_data()
        
    def populate_data(self):
        engineering_category = QStandardItem("Engineering Department")
        engineering_category.setData("Category: Engineering Department with 3 employees", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp1 = [
            QStandardItem("Alice Johnson"),
            QStandardItem("28"),
            QStandardItem("Software"),
            QStandardItem("$95,000")
        ]
        emp1[0].setData("Employee: Alice Johnson, Age 28, Department Software, Salary $95,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp2 = [
            QStandardItem("Bob Smith"),
            QStandardItem("35"),
            QStandardItem("Hardware"),
            QStandardItem("$105,000")
        ]
        emp2[0].setData("Employee: Bob Smith, Age 35, Department Hardware, Salary $105,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp3 = [
            QStandardItem("Charlie Davis"),
            QStandardItem("42"),
            QStandardItem("Network"),
            QStandardItem("$110,000")
        ]
        emp3[0].setData("Employee: Charlie Davis, Age 42, Department Network, Salary $110,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        engineering_category.appendRow(emp1)
        engineering_category.appendRow(emp2)
        engineering_category.appendRow(emp3)
        self.model.appendRow([engineering_category, QStandardItem(""), QStandardItem(""), QStandardItem("")])
        
        sales_category = QStandardItem("Sales Department")
        sales_category.setData("Category: Sales Department with 3 employees", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp4 = [
            QStandardItem("Diana Martinez"),
            QStandardItem("31"),
            QStandardItem("Regional Sales"),
            QStandardItem("$85,000")
        ]
        emp4[0].setData("Employee: Diana Martinez, Age 31, Department Regional Sales, Salary $85,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp5 = [
            QStandardItem("Ethan Wilson"),
            QStandardItem("29"),
            QStandardItem("Enterprise Sales"),
            QStandardItem("$92,000")
        ]
        emp5[0].setData("Employee: Ethan Wilson, Age 29, Department Enterprise Sales, Salary $92,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp6 = [
            QStandardItem("Fiona Brown"),
            QStandardItem("38"),
            QStandardItem("Sales Manager"),
            QStandardItem("$115,000")
        ]
        emp6[0].setData("Employee: Fiona Brown, Age 38, Department Sales Manager, Salary $115,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        sales_category.appendRow(emp4)
        sales_category.appendRow(emp5)
        sales_category.appendRow(emp6)
        self.model.appendRow([sales_category, QStandardItem(""), QStandardItem(""), QStandardItem("")])
        
        hr_category = QStandardItem("Human Resources")
        hr_category.setData("Category: Human Resources with 2 employees", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp7 = [
            QStandardItem("George Taylor"),
            QStandardItem("45"),
            QStandardItem("Recruitment"),
            QStandardItem("$78,000")
        ]
        emp7[0].setData("Employee: George Taylor, Age 45, Department Recruitment, Salary $78,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp8 = [
            QStandardItem("Hannah Anderson"),
            QStandardItem("33"),
            QStandardItem("Benefits Admin"),
            QStandardItem("$72,000")
        ]
        emp8[0].setData("Employee: Hannah Anderson, Age 33, Department Benefits Admin, Salary $72,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        hr_category.appendRow(emp7)
        hr_category.appendRow(emp8)
        self.model.appendRow([hr_category, QStandardItem(""), QStandardItem(""), QStandardItem("")])
        
        finance_category = QStandardItem("Finance Department")
        finance_category.setData("Category: Finance Department with 2 employees", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp9 = [
            QStandardItem("Ian Thompson"),
            QStandardItem("40"),
            QStandardItem("Accounting"),
            QStandardItem("$88,000")
        ]
        emp9[0].setData("Employee: Ian Thompson, Age 40, Department Accounting, Salary $88,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        emp10 = [
            QStandardItem("Julia White"),
            QStandardItem("36"),
            QStandardItem("Financial Analysis"),
            QStandardItem("$98,000")
        ]
        emp10[0].setData("Employee: Julia White, Age 36, Department Financial Analysis, Salary $98,000", Qt.ItemDataRole.AccessibleDescriptionRole)
        
        finance_category.appendRow(emp9)
        finance_category.appendRow(emp10)
        self.model.appendRow([finance_category, QStandardItem(""), QStandardItem(""), QStandardItem("")])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TreeViewExample()
    window.show()
    sys.exit(app.exec())