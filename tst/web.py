import sys
# Core imports for application and GUI
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import QUrl, QCoreApplication, Qt
# QQuickWidget is needed to host the QML-based WebView component
from PySide6.QtQuickWidgets import QQuickWidget
# Crucial import: QtWebView must be imported and initialized
from PySide6.QtWebView import QtWebView 

# --- QML Item Content ---
# QtWebView provides a 'WebView' QML type. We embed it here.
# It loads the specified URL and automatically handles rendering using the native platform's web rendering engine.
QML_VIEW_ITEM = """
import QtQuick
import QtWebView

// The WebView element is provided by PySide6.QtWebView
WebView {
    id: webView
    // Using a simple, non-interactive URL for demonstration
    url: "https://www.qt.io"
    
    // Fill the container (the QQuickWidget)
    width: parent.width
    height: parent.height
}
"""

def main():
    # --- MANDATORY INITIALIZATION STEP ---
    # The QtWebView documentation states that initialize() must be called
    # before the QGuiApplication (or QApplication) instance is created.
    try:
        QtWebView.initialize()
        print("INFO: QtWebView initialized successfully.")
    except Exception as e:
        # In some environments, this might raise an error if the native backend isn't available.
        print(f"WARNING: QtWebView initialization failed: {e}")

    # 1. Create the application instance
    # Use QApplication for a standard desktop app environment
    app = QApplication(sys.argv)

    # 2. Setup the Main Window
    main_window = QMainWindow()
    main_window.setWindowTitle("PySide6 Native WebView (QtWebView)")
    main_window.resize(1000, 650)

    # Set up a container widget and layout
    container = QWidget()
    layout = QVBoxLayout(container)
    
    # 3. Create the QQuickWidget to host the QML WebView component
    quick_widget = QQuickWidget()
    
    # Load the QML content directly from the string
    # We use a data URL to load the QML string directly without needing a separate .qml file.
    quick_widget.setSource(QUrl.fromUserInput("data:text/plain;charset=utf-8," + QML_VIEW_ITEM))
    
    # Ensure the QML item resizes with the widget
    quick_widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

    layout.addWidget(quick_widget)
    main_window.setCentralWidget(container)

    # 4. Run the application
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
