from PySide6.QtWidgets import (QWidget, QFormLayout, QSpinBox, QLineEdit, QCheckBox,
                                QPushButton, QHBoxLayout, QGroupBox, QVBoxLayout)

# Duplicated rather than imported from the dialog module: gui.dialogs's
# package init pulls prefs_dialog -> prefs_panels back in.
PROXY_KEYS = ("proxy_enabled", "proxy_type", "proxy_host", "proxy_port",
              "proxy_user", "proxy_pass")


class DownloadsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Edited through the Network Proxy dialog, then written back out in
        # save_settings().
        self._proxy_values = {}
        self.setup_ui()

    def setup_ui(self):
        outer = QVBoxLayout(self)

        transfer_group = QGroupBox(_("Transfers"), self)
        form = QFormLayout(transfer_group)

        self.parallel_spin = QSpinBox(self)
        self.parallel_spin.setRange(1, 10)
        self.parallel_spin.setAccessibleName(_("Maximum parallel downloads"))
        form.addRow(_("Max Parallel Downloads:"), self.parallel_spin)

        self.speed_spin = QSpinBox(self)
        self.speed_spin.setRange(0, 1048576)
        self.speed_spin.setSuffix(_(" KB/s"))
        self.speed_spin.setSpecialValueText(_("Unlimited"))
        self.speed_spin.setAccessibleName(_("Download speed limit"))
        form.addRow(_("Speed Limit:"), self.speed_spin)

        self.retry_spin = QSpinBox(self)
        self.retry_spin.setRange(0, 20)
        self.retry_spin.setAccessibleName(_("Retry count"))
        form.addRow(_("Retry Count:"), self.retry_spin)

        self.retry_delay_spin = QSpinBox(self)
        self.retry_delay_spin.setRange(250, 60000)
        self.retry_delay_spin.setSuffix(_(" ms"))
        self.retry_delay_spin.setAccessibleName(_("Retry delay"))
        form.addRow(_("Retry Delay:"), self.retry_delay_spin)

        outer.addWidget(transfer_group)

        notify_group = QGroupBox(_("Notifications"), self)
        notify_form = QFormLayout(notify_group)
        self.notify_finished_check = QCheckBox(_("Notify when a download finishes"), self)
        self.notify_finished_check.setAccessibleDescription(
            _("Shows a system tray notification when a download completes or fails."))
        notify_form.addRow(self.notify_finished_check)
        outer.addWidget(notify_group)

        paths_group = QGroupBox(_("Locations"), self)
        paths_form = QFormLayout(paths_group)

        dir_row = QHBoxLayout()
        self.download_dir_edit = QLineEdit(self)
        self.download_dir_edit.setAccessibleName(_("Default download folder"))
        self.download_dir_edit.setAccessibleDescription(
            _("Folder new downloads are saved to. Leave empty to use the "
              "application's own downloads folder."))
        browse_btn = QPushButton(_("Browse..."), self)
        browse_btn.setAccessibleName(_("Browse for default download folder"))
        browse_btn.clicked.connect(lambda: self._browse_dir(self.download_dir_edit))
        dir_row.addWidget(self.download_dir_edit)
        dir_row.addWidget(browse_btn)
        paths_form.addRow(_("Default Download Folder:"), dir_row)

        podcast_row = QHBoxLayout()
        self.podcast_dir_edit = QLineEdit(self)
        self.podcast_dir_edit.setAccessibleName(_("Podcasts folder"))
        self.podcast_dir_edit.setAccessibleDescription(
            _("Folder podcast episodes are saved to, each feed in its own "
              "subfolder. Leave empty to use the application's own podcasts folder."))
        podcast_browse_btn = QPushButton(_("Browse..."), self)
        podcast_browse_btn.setAccessibleName(_("Browse for podcasts folder"))
        podcast_browse_btn.clicked.connect(lambda: self._browse_dir(self.podcast_dir_edit))
        podcast_row.addWidget(self.podcast_dir_edit)
        podcast_row.addWidget(podcast_browse_btn)
        paths_form.addRow(_("Podcasts Folder:"), podcast_row)

        outer.addWidget(paths_group)

        proxy_group = QGroupBox(_("Network"), self)
        proxy_layout = QFormLayout(proxy_group)

        self.proxy_button = QPushButton(_("Proxy Settings..."), self)
        self.proxy_button.setAccessibleDescription(
            _("Opens the network proxy settings dialog."))
        self.proxy_button.clicked.connect(self._open_proxy_dialog)
        proxy_layout.addRow(self.proxy_button)

        self.proxy_summary_edit = QLineEdit(self)
        self.proxy_summary_edit.setReadOnly(True)
        self.proxy_summary_edit.setAccessibleName(_("Current proxy"))
        proxy_layout.addRow(_("Proxy:"), self.proxy_summary_edit)

        outer.addWidget(proxy_group)
        outer.addStretch(1)

    def _browse_dir(self, edit):
        from PySide6.QtWidgets import QFileDialog
        chosen = QFileDialog.getExistingDirectory(self, _("Select Folder"), edit.text() or "")
        if chosen:
            edit.setText(chosen)

    def _open_proxy_dialog(self):
        from ..dialogs.proxy_settings_dialog import ProxySettingsDialog
        dialog = ProxySettingsDialog(self._proxy_values, self)
        if dialog.exec():
            self._proxy_values.update(dialog.values())
            self._refresh_proxy_summary()

    def _refresh_proxy_summary(self):
        if not self._proxy_values.get("proxy_enabled"):
            self.proxy_summary_edit.setText(_("No proxy"))
            return
        self.proxy_summary_edit.setText("{type}://{host}:{port}".format(
            type=self._proxy_values.get("proxy_type") or "http",
            host=self._proxy_values.get("proxy_host") or "",
            port=self._proxy_values.get("proxy_port") or 8080))

    def load_settings(self, prefs):
        self.parallel_spin.setValue(prefs.get("download_max_parallel", 2))
        self.speed_spin.setValue(prefs.get("download_speed_limit_kbps", 0))
        self.retry_spin.setValue(prefs.get("download_retry_count", 3))
        self.retry_delay_spin.setValue(prefs.get("download_retry_delay_ms", 2000))
        self.notify_finished_check.setChecked(bool(prefs.get("download_notify_finished", True)))
        self.download_dir_edit.setText(prefs.get("download_dir", ""))
        self.podcast_dir_edit.setText(prefs.get("download_podcast_dir", ""))
        self._proxy_values = {key: prefs.get(key) for key in PROXY_KEYS}
        self._refresh_proxy_summary()

    def save_settings(self, prefs):
        prefs["download_max_parallel"] = self.parallel_spin.value()
        prefs["download_speed_limit_kbps"] = self.speed_spin.value()
        prefs["download_retry_count"] = self.retry_spin.value()
        prefs["download_retry_delay_ms"] = self.retry_delay_spin.value()
        prefs["download_notify_finished"] = self.notify_finished_check.isChecked()
        prefs["download_dir"] = self.download_dir_edit.text().strip()
        prefs["download_podcast_dir"] = self.podcast_dir_edit.text().strip()
        for key in PROXY_KEYS:
            if key in self._proxy_values:
                prefs[key] = self._proxy_values[key]
