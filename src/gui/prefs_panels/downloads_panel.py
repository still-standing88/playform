from PySide6.QtWidgets import (QWidget, QFormLayout, QSpinBox, QLineEdit, QCheckBox,
                                QComboBox, QPushButton, QHBoxLayout, QGroupBox, QVBoxLayout)
from PySide6.QtCore import Qt


class DownloadsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        outer = QVBoxLayout(self)

        transfer_group = QGroupBox(_("Transfers"), self)
        form = QFormLayout(transfer_group)

        self.parallel_spin = QSpinBox(self)
        self.parallel_spin.setRange(1, 10)
        form.addRow(_("Max Parallel Downloads:"), self.parallel_spin)

        self.speed_spin = QSpinBox(self)
        self.speed_spin.setRange(0, 1048576)
        self.speed_spin.setSuffix(_(" KB/s"))
        self.speed_spin.setSpecialValueText(_("Unlimited"))
        form.addRow(_("Speed Limit:"), self.speed_spin)

        self.retry_spin = QSpinBox(self)
        self.retry_spin.setRange(0, 20)
        form.addRow(_("Retry Count:"), self.retry_spin)

        self.retry_delay_spin = QSpinBox(self)
        self.retry_delay_spin.setRange(250, 60000)
        self.retry_delay_spin.setSuffix(_(" ms"))
        form.addRow(_("Retry Delay:"), self.retry_delay_spin)

        outer.addWidget(transfer_group)

        paths_group = QGroupBox(_("Locations"), self)
        paths_form = QFormLayout(paths_group)

        dir_row = QHBoxLayout()
        self.download_dir_edit = QLineEdit(self)
        browse_btn = QPushButton(_("Browse..."), self)
        browse_btn.clicked.connect(lambda: self._browse_dir(self.download_dir_edit))
        dir_row.addWidget(self.download_dir_edit)
        dir_row.addWidget(browse_btn)
        paths_form.addRow(_("Default Download Folder:"), dir_row)

        podcast_row = QHBoxLayout()
        self.podcast_dir_edit = QLineEdit(self)
        podcast_browse_btn = QPushButton(_("Browse..."), self)
        podcast_browse_btn.clicked.connect(lambda: self._browse_dir(self.podcast_dir_edit))
        podcast_row.addWidget(self.podcast_dir_edit)
        podcast_row.addWidget(podcast_browse_btn)
        paths_form.addRow(_("Podcasts Folder:"), podcast_row)

        outer.addWidget(paths_group)

        proxy_group = QGroupBox(_("Network Proxy"), self)
        proxy_form = QFormLayout(proxy_group)

        self.proxy_enabled_check = QCheckBox(_("Enable Proxy"), self)
        self.proxy_enabled_check.stateChanged.connect(self._update_proxy_state)
        proxy_form.addRow(self.proxy_enabled_check)

        self.proxy_type_combo = QComboBox(self)
        self.proxy_type_combo.addItems(["http", "socks5"])
        proxy_form.addRow(_("Type:"), self.proxy_type_combo)

        self.proxy_host_edit = QLineEdit(self)
        proxy_form.addRow(_("Host:"), self.proxy_host_edit)

        self.proxy_port_spin = QSpinBox(self)
        self.proxy_port_spin.setRange(1, 65535)
        proxy_form.addRow(_("Port:"), self.proxy_port_spin)

        self.proxy_user_edit = QLineEdit(self)
        proxy_form.addRow(_("User:"), self.proxy_user_edit)

        self.proxy_pass_edit = QLineEdit(self)
        self.proxy_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        proxy_form.addRow(_("Password:"), self.proxy_pass_edit)

        outer.addWidget(proxy_group)
        outer.addStretch(1)

    def _browse_dir(self, edit):
        from PySide6.QtWidgets import QFileDialog
        chosen = QFileDialog.getExistingDirectory(self, _("Select Folder"), edit.text() or "")
        if chosen:
            edit.setText(chosen)

    def _update_proxy_state(self):
        enabled = self.proxy_enabled_check.isChecked()
        for widget in (self.proxy_type_combo, self.proxy_host_edit,
                       self.proxy_port_spin, self.proxy_user_edit, self.proxy_pass_edit):
            widget.setEnabled(enabled)

    def load_settings(self, prefs):
        self.parallel_spin.setValue(prefs.get("download_max_parallel", 2))
        self.speed_spin.setValue(prefs.get("download_speed_limit_kbps", 0))
        self.retry_spin.setValue(prefs.get("download_retry_count", 3))
        self.retry_delay_spin.setValue(prefs.get("download_retry_delay_ms", 2000))
        self.download_dir_edit.setText(prefs.get("download_dir", ""))
        self.podcast_dir_edit.setText(prefs.get("download_podcast_dir", ""))
        self.proxy_enabled_check.setChecked(prefs.get("proxy_enabled", False))
        type_index = self.proxy_type_combo.findText(prefs.get("proxy_type", "http"))
        self.proxy_type_combo.setCurrentIndex(type_index if type_index >= 0 else 0)
        self.proxy_host_edit.setText(prefs.get("proxy_host", ""))
        self.proxy_port_spin.setValue(int(prefs.get("proxy_port", 8080) or 8080))
        self.proxy_user_edit.setText(prefs.get("proxy_user", ""))
        self.proxy_pass_edit.setText(prefs.get("proxy_pass", ""))
        self._update_proxy_state()

    def save_settings(self, prefs):
        prefs["download_max_parallel"] = self.parallel_spin.value()
        prefs["download_speed_limit_kbps"] = self.speed_spin.value()
        prefs["download_retry_count"] = self.retry_spin.value()
        prefs["download_retry_delay_ms"] = self.retry_delay_spin.value()
        prefs["download_dir"] = self.download_dir_edit.text().strip()
        prefs["download_podcast_dir"] = self.podcast_dir_edit.text().strip()
        prefs["proxy_enabled"] = self.proxy_enabled_check.isChecked()
        prefs["proxy_type"] = self.proxy_type_combo.currentText()
        prefs["proxy_host"] = self.proxy_host_edit.text().strip()
        prefs["proxy_port"] = self.proxy_port_spin.value()
        prefs["proxy_user"] = self.proxy_user_edit.text()
        prefs["proxy_pass"] = self.proxy_pass_edit.text()
