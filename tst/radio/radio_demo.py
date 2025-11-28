import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QKeySequence

from radio_browser_widget import RadioBrowserWidget


class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radio Browser - Browse Internet Radio Stations")
        self.resize(1100, 650)
        
        self.radio_widget = RadioBrowserWidget(self, user_agent="RadioBrowserDemo/1.0")
        self.setCentralWidget(self.radio_widget)
        
        self.create_menu_bar()
        
        QTimer.singleShot(500, self.show_welcome)
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        refresh_action = QAction("&Refresh Search", self)
        refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        refresh_action.setStatusTip("Refresh current search results")
        refresh_action.triggered.connect(self.radio_widget.perform_search)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.setStatusTip("Exit application")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        search_menu = menubar.addMenu("&Search")
        
        focus_search_action = QAction("Focus &Search Box", self)
        focus_search_action.setShortcut(QKeySequence("Ctrl+F"))
        focus_search_action.setStatusTip("Focus the search input field")
        focus_search_action.triggered.connect(self.focus_search)
        search_menu.addAction(focus_search_action)
        
        perform_search_action = QAction("&Perform Search", self)
        perform_search_action.setShortcut(QKeySequence("Return"))
        perform_search_action.setStatusTip("Execute the current search")
        perform_search_action.triggered.connect(self.radio_widget.perform_search)
        search_menu.addAction(perform_search_action)
        
        search_menu.addSeparator()
        
        clear_cache_action = QAction("Clear &Cache", self)
        clear_cache_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        clear_cache_action.setStatusTip("Clear all cached data")
        clear_cache_action.triggered.connect(self.radio_widget.clear_cache)
        search_menu.addAction(clear_cache_action)
        
        favorites_menu = menubar.addMenu("&Favorites")
        
        show_favorites_action = QAction("Show &Favorites", self)
        show_favorites_action.setShortcut(QKeySequence("Ctrl+D"))
        show_favorites_action.setStatusTip("Display favorite stations")
        show_favorites_action.triggered.connect(self.radio_widget.show_favorites)
        favorites_menu.addAction(show_favorites_action)
        
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        instructions_action = QAction("&Instructions", self)
        instructions_action.setShortcut(QKeySequence("F1"))
        instructions_action.setStatusTip("Show usage instructions")
        instructions_action.triggered.connect(self.show_instructions)
        help_menu.addAction(instructions_action)
    
    def show_welcome(self):
        self.radio_widget.status_bar.showMessage(
            "Welcome! Select a filter or search to browse stations",
            6000
        )
    
    def focus_search(self):
        self.radio_widget.search_input.setFocus()
        self.radio_widget.search_input.selectAll()
    
    def show_about(self):
        QMessageBox.about(
            self,
            "About Radio Browser",
            "<h2>Radio Browser Demo</h2>"
            "<p>Browse and search thousands of internet radio stations.</p>"
            "<p><b>Built with PySide6 and the Radio Browser API.</b></p>"
        )
    
    def show_instructions(self):
        instructions = """
        <h3>How to Use Radio Browser</h3>
        
        <h4>Searching for Stations:</h4>
        <ul>
            <li><b>By Name:</b> Type a station name</li>
            <li><b>By Filter:</b> Select Country/Language/Tag and choose a value</li>
            <li><b>Auto-search:</b> Results update automatically when you make selections</li>
        </ul>
        
        <h4>Station Actions (Right-Click Menu):</h4>
        <ul>
            <li><b>Play Station:</b> Shows stream URL</li>
            <li><b>Register Click:</b> Marks station as played</li>
            <li><b>Add/Remove Favorites:</b> Save stations</li>
            <li><b>Station Information:</b> View details</li>
            <li><b>Copy Stream URL:</b> Copy to clipboard</li>
        </ul>
        
        <h4>Keyboard Shortcuts:</h4>
        <ul>
            <li><b>Ctrl+F:</b> Focus search box</li>
            <li><b>Ctrl+R:</b> Refresh search</li>
            <li><b>Ctrl+D:</b> Show favorites</li>
            <li><b>Ctrl+Shift+C:</b> Clear cache</li>
        </ul>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Instructions")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(instructions)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Radio Browser Demo")
    app.setOrganizationName("RadioBrowser")
    
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()