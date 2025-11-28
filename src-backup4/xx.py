import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit
from PySide6.QtCore import Qt
import pyttsx3

# Initialize the text-to-speech engine
engine = pyttsx3.init()

class KeySpeaker(QMainWindow):
    """
    A simple PySide6 application that speaks the name of the pressed key.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Key Speaker")
        self.setGeometry(100, 100, 400, 200)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Press any key to hear its name...")
        self.text_edit.setReadOnly(True)  # Make it read-only
        self.setCentralWidget(self.text_edit)

        # Set the central widget to receive key events
        self.text_edit.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        """
        Overrides the keyPressEvent to handle key presses.
        """
        # Get the key code from the event
        key = event.key()

        # Check for special keys and their string names
        if key == Qt.Key_Space:
            key_name = "Space"
        elif key == Qt.Key_Enter or key == Qt.Key_Return:
            key_name = "Enter"
        elif key == Qt.Key_Backspace:
            key_name = "Backspace"
        elif key == Qt.Key_Escape:
            key_name = "Escape"
        elif key == Qt.Key_Shift:
            key_name = "Shift"
        elif key == Qt.Key_Control:
            key_name = "Control"
        elif key == Qt.Key_Alt:
            key_name = "Alt"
        elif key == Qt.Key_Tab:
            key_name = "Tab"
        elif key == Qt.Key_PageUp:
            key_name = "Page Up"
        elif key == Qt.Key_PageDown:
            key_name = "Page Down"
        else:
            # For other keys, get the text from the event
            key_name = event.text()
            if key_name.isspace() or key_name == '':
                # If the text is empty or a space (already handled),
                # get the key name from the key code
                key_name = Qt.Key(key).name

        # Speak the name of the key
        if key_name and key_name.strip():
            engine.say(f"{key_name}")
            engine.runAndWait()

            # Update the text edit with the spoken key
            current_text = self.text_edit.toPlainText()
            self.text_edit.setPlainText(f"Pressed: {key_name}\n{current_text}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = KeySpeaker()
    window.show()
    sys.exit(app.exec())
