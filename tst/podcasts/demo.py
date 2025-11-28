import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt
from feed_widget import FeedWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Feed Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        self.feed_widget = FeedWidget()
        self.setCentralWidget(self.feed_widget)
        
        self.setAccessibleName("Feed Manager Application")
        self.setAccessibleDescription("RSS and podcast feed management application")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Feed Manager")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()