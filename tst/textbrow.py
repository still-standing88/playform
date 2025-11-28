import sys
import bleach
from PySide6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QTextBrowser, 
    QVBoxLayout, 
    QWidget
)
from PySide6.QtCore import Qt

# --- 1. Define Whitelist for Bleach (Same as before) ---
ALLOWED_TAGS = {'p', 'b', 'i', 'strong', 'em', 'a', 'h1', 'img'}
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt']
}
ALLOWED_PROTOCOLS = {'http', 'https'}

def sanitize_html(html_input):
    """Sanitizes HTML using bleach with a strict whitelist."""
    return bleach.clean(
        html_input,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True
    )

# --- 2. PySide6 Application Setup with Link Handling ---
class HtmlViewer(QMainWindow):
    def __init__(self, sanitized_html):
        super().__init__()
        self.setWindowTitle("Sanitized HTML with External Link Support (PySide6)")
        self.setGeometry(100, 100, 800, 600)

        browser = QTextBrowser(self)
        browser.setReadOnly(True)

        # 💡 Feature 1: Enable text selection/copying
        browser.setTextInteractionFlags(
            Qt.TextSelectableByMouse | 
            Qt.TextSelectableByKeyboard
        )
        
        # 🚀 Feature 2: Enable opening links externally
        # When True, clicking an <a> tag will open the URL in the OS's default web browser.
        browser.setOpenExternalLinks(True)

        # Set the sanitized content
        browser.setHtml(sanitized_html)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(browser)
        self.setCentralWidget(central_widget)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Input HTML includes a safe link that will now open externally
    raw_html = """
    <h1>External Link Test</h1>
    <p>Click the link below to test the feature:</p>
    <a href="https://www.google.com">Search the Web (This should open externally)</a>
    <a href="javascript:alert('XSS!');">Bad Link (Still safely inert)</a> 
    """
    
    clean_html = sanitize_html(raw_html)
    
    print("--- Sanitized HTML Output ---")
    print(clean_html)
    
    # Run the GUI
    viewer = HtmlViewer(clean_html)
    viewer.show()
    sys.exit(app.exec())