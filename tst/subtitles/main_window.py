import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget)
from converter_widget import ConverterWidget
from editor_widget import EditorWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pysubs2 Subtitle Toolkit")
        self.setGeometry(100, 100, 800, 600)

        main_tabs = QTabWidget()
        self.setCentralWidget(main_tabs)

        converter_tool = ConverterWidget()
        editor_tool = EditorWidget()

        main_tabs.addTab(converter_tool, "Converter & Cleaner")
        main_tabs.addTab(editor_tool, "Subtitle Editor")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())