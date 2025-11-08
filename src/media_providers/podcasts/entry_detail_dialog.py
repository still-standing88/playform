from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt
import html


class EntryDetailDialog(QDialog):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle("Full Entry Details")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(700, 500)
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.display_entry()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard |
            Qt.TextInteractionFlag.LinksAccessibleByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByKeyboard |
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.browser.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.browser.setTabChangesFocus(False)
        layout.addWidget(self.browser)
        
        btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)

    def display_entry(self):
        html_parts = []
        html_parts.append("<div style='font-family: Arial, sans-serif; padding: 20px; line-height: 1.6;'>")
        html_parts.append("<h2 style='color: #2c3e50; border-bottom: 2px solid #ccc;'>Full Entry Data</h2>")
        
        attrs = {}
        if isinstance(self.entry, dict):
            attrs = self.entry
        elif hasattr(self.entry, '__dict__'):
            attrs = vars(self.entry)
        else:
            try:
                keys = getattr(self.entry, 'keys', None)
                if keys and callable(keys):
                    key_list = list(keys())  # type: ignore[arg-type]
                    for key in key_list:
                        attrs[key] = self.entry[key]
            except:
                pass
        
        for key, value in sorted(attrs.items()):
            if key.startswith('_'):
                continue
            
            display_key = key.replace('_', ' ').title()
            html_parts.append(f"<div style='margin: 15px 0;'>")
            html_parts.append(f"<strong style='color: #2c3e50;'>{display_key}:</strong><br>")
            
            formatted_value = self.format_value(value)
            html_parts.append(f"<div style='margin-left: 20px; color: #34495e;'>{formatted_value}</div>")
            html_parts.append("</div>")
        
        html_parts.append("</div>")
        self.browser.setHtml(''.join(html_parts))

    def format_value(self, value):
        if value is None:
            return "<em style='color: #999;'>None</em>"
        
        if isinstance(value, str):
            if value.startswith('http://') or value.startswith('https://'):
                return f"<a href='{value}'>{value}</a>"
            import html
            escaped = html.escape(value)
            return escaped.replace('\n', '<br>')
        
        if isinstance(value, dict):
            if 'value' in value:
                return self.format_value(value['value'])
            parts = []
            for k, v in value.items():
                parts.append(f"<strong>{k}:</strong> {self.format_value(v)}")
            return "<br>".join(parts)
        
        if isinstance(value, (list, tuple)):
            if not value:
                return "<em style='color: #999;'>Empty</em>"
            items = [str(item) for item in value[:10]]
            if len(value) > 10:
                items.append(f"<em>... and {len(value) - 10} more</em>")
            return "<br>".join(f"• {item}" for item in items)
        
        return str(value)

    def copy_to_clipboard(self):
        text_parts = []
        text_parts.append("=" * 60)
        text_parts.append("FULL ENTRY DATA")
        text_parts.append("=" * 60)
        text_parts.append("")
        
        attrs = {}
        if isinstance(self.entry, dict):
            attrs = self.entry
        elif hasattr(self.entry, '__dict__'):
            attrs = vars(self.entry)
        else:
            try:
                keys = getattr(self.entry, 'keys', None)
                if keys and callable(keys):
                    key_list = list(keys())  # type: ignore[arg-type]
                    for key in key_list:
                        attrs[key] = self.entry[key]
            except:
                pass
        
        for key, value in sorted(attrs.items()):
            if key.startswith('_'):
                continue
            
            display_key = key.replace('_', ' ').title()
            text_parts.append(f"{display_key}:")
            text_parts.append(f"  {self.format_value_as_text(value)}")
            text_parts.append("")
        
        text_parts.append("=" * 60)
        
        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(text_parts))
        QMessageBox.information(self, "Copied", "Entry data copied to clipboard")

    def format_value_as_text(self, value):
        if value is None:
            return "None"
        
        if isinstance(value, str):
            return value
        
        if isinstance(value, dict):
            if 'value' in value:
                return self.format_value_as_text(value['value'])
            parts = []
            for k, v in value.items():
                parts.append(f"  {k}: {self.format_value_as_text(v)}")
            return "\n".join(parts)
        
        if isinstance(value, (list, tuple)):
            if not value:
                return "Empty"
            items = [str(item) for item in value[:50]]
            if len(value) > 50:
                items.append(f"... and {len(value) - 50} more")
            return "\n  ".join(f"• {item}" for item in items)
        
        return str(value)
