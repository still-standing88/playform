from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt

import html
from app_constance.styles import border_color, secondary_text_color


class EntryDetailDialog(QDialog):


    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self._rendered = False
        self.setWindowTitle(_("Full Entry Details"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(700, 500)
        self.setMinimumSize(600, 400)

        self.setup_ui()

    def showEvent(self, event):
        super().showEvent(event)
        # The HTML takes its colors from the browser's palette, which only
        # reflects the active theme's stylesheet once the widget is polished --
        # rendering from __init__ baked black text onto the dark theme.
        if not self._rendered:
            self._rendered = True
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
        
        copy_btn = QPushButton(_("Copy to Clipboard"))
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)
        
        close_btn = QPushButton(_("Close"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)

    def display_entry(self):
        palette = self.browser.palette()
        heading_color = palette.text().color().name()
        value_color = palette.windowText().color().name()
        muted_color = secondary_text_color()
        rule_color = border_color()

        html_parts = []
        html_parts.append("<div style='padding: 20px; line-height: 1.6;'>")
        html_parts.append(
            f"<h2 style='color: {heading_color}; border-bottom: 2px solid {rule_color};'>"
            f"{html.escape(_('Full Entry Data'))}</h2>"
        )
        
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
            html_parts.append(f"<strong style='color: {heading_color};'>{display_key}:</strong><br>")

            formatted_value = self.format_value(value, muted_color)
            html_parts.append(f"<div style='margin-left: 20px; color: {value_color};'>{formatted_value}</div>")
            html_parts.append("</div>")

        html_parts.append("</div>")
        self.browser.setHtml(''.join(html_parts))

    def format_value(self, value, muted_color="#999"):
        if value is None:
            return f"<em style='color: {muted_color};'>{html.escape(_('None'))}</em>"

        if isinstance(value, str):
            if value.startswith('http://') or value.startswith('https://'):
                return f"<a href='{value}'>{value}</a>"
            escaped = html.escape(value)
            return escaped.replace('\n', '<br>')

        if isinstance(value, dict):
            if 'value' in value:
                return self.format_value(value['value'], muted_color)
            parts = []
            for k, v in value.items():
                parts.append(f"<strong>{k}:</strong> {self.format_value(v, muted_color)}")
            return "<br>".join(parts)

        if isinstance(value, (list, tuple)):
            if not value:
                return f"<em style='color: {muted_color};'>{html.escape(_('Empty'))}</em>"
            items = [str(item) for item in value[:10]]
            if len(value) > 10:
                items.append(
                    _("<em>... and {count} more</em>").format(
                        count=len(value) - 10
                    )
                )
            return "<br>".join(f"• {item}" for item in items)
        
        return str(value)

    def copy_to_clipboard(self):
        text_parts = []
        text_parts.append("=" * 60)
        text_parts.append(_("FULL ENTRY DATA"))
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
        QMessageBox.information(
            self,
            _("Copied"),
            _("Entry data copied to clipboard"),
        )

    def format_value_as_text(self, value):
        if value is None:
            return _("None")
        
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
                return _("Empty")
            items = [str(item) for item in value[:50]]
            if len(value) > 50:
                items.append(_("... and {count} more").format(count=len(value) - 50))
            return "\n  ".join(f"• {item}" for item in items)
        
        return str(value)
