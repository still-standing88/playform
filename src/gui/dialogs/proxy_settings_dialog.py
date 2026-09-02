"""Network proxy settings, split out of the Downloads preferences page.

Holds its own copy of the six proxy prefs while open and only writes them
back into the passed-in dict on accept, so Cancel here leaves the
Preferences dialog's pending state untouched.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QComboBox,
    QCheckBox, QDialogButtonBox, QMessageBox,
)

from ..prefs_panels.downloads_panel import PROXY_KEYS

__all__ = ["ProxySettingsDialog", "PROXY_KEYS"]


class ProxySettingsDialog(QDialog):
    def __init__(self, values: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Network Proxy"))
        self.setMinimumWidth(420)
        self._build_ui()
        self._load(values)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.enabled_check = QCheckBox(_("Enable Proxy"), self)
        self.enabled_check.setAccessibleDescription(
            _("Routes downloads through the proxy configured below."))
        self.enabled_check.toggled.connect(self._update_state)
        form.addRow(self.enabled_check)

        self.type_combo = QComboBox(self)
        self.type_combo.addItems(["http", "socks5"])
        self.type_combo.setAccessibleName(_("Proxy type"))
        form.addRow(_("Type:"), self.type_combo)

        self.host_edit = QLineEdit(self)
        self.host_edit.setAccessibleName(_("Proxy host"))
        form.addRow(_("Host:"), self.host_edit)

        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setAccessibleName(_("Proxy port"))
        form.addRow(_("Port:"), self.port_spin)

        self.user_edit = QLineEdit(self)
        self.user_edit.setAccessibleName(_("Proxy user name"))
        form.addRow(_("User:"), self.user_edit)

        self.pass_edit = QLineEdit(self)
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setAccessibleName(_("Proxy password"))
        form.addRow(_("Password:"), self.pass_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_state(self):
        enabled = self.enabled_check.isChecked()
        for widget in (self.type_combo, self.host_edit, self.port_spin,
                       self.user_edit, self.pass_edit):
            widget.setEnabled(enabled)

    def _load(self, values: dict):
        self.enabled_check.setChecked(bool(values.get("proxy_enabled", False)))
        type_index = self.type_combo.findText(values.get("proxy_type", "http"))
        self.type_combo.setCurrentIndex(type_index if type_index >= 0 else 0)
        self.host_edit.setText(values.get("proxy_host", ""))
        self.port_spin.setValue(int(values.get("proxy_port", 8080) or 8080))
        self.user_edit.setText(values.get("proxy_user", ""))
        self.pass_edit.setText(values.get("proxy_pass", ""))
        self._update_state()

    def _on_accept(self):
        if self.enabled_check.isChecked() and not self.host_edit.text().strip():
            QMessageBox.information(self, _("Network Proxy"),
                                    _("Enter a proxy host, or turn the proxy off."))
            self.host_edit.setFocus()
            return
        self.accept()

    def values(self) -> dict:
        return {
            "proxy_enabled": self.enabled_check.isChecked(),
            "proxy_type": self.type_combo.currentText(),
            "proxy_host": self.host_edit.text().strip(),
            "proxy_port": self.port_spin.value(),
            "proxy_user": self.user_edit.text(),
            "proxy_pass": self.pass_edit.text(),
        }
