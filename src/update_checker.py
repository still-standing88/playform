import os
import sys
import json
import platform as _platform_mod
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QUrl, Qt
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser, QListWidget, QListWidgetItem,
    QMessageBox, QWidget,
)


_12H_MS = 12 * 60 * 60 * 1000
_CHECK_DELAY_MS = 3_000


def _current_platform() -> str:
    system_name = _platform_mod.system().lower()
    return "macos" if system_name == "darwin" else ("windows" if system_name == "windows" else "linux")


def _current_arch() -> str:
    machine = _platform_mod.machine().lower()
    if machine in ("amd64", "x86_64"):
        return "x64"
    elif machine in ("arm64", "aarch64"):
        return "arm64"
    elif machine in ("i386", "i686", "x86"):
        return "x86"
    return machine if machine else "unknown"


def _strip_v(tag: str) -> str:
    return tag.lstrip("vV")


def _is_newer(remote_tag: str, local_version: str) -> bool:
    try:
        remote = tuple(int(x) for x in _strip_v(remote_tag).split("."))
        local = tuple(int(x) for x in _strip_v(local_version).split("."))
        return remote > local
    except Exception:
        return False


def _is_frozen() -> bool:
    from utilities.functions import is_frozen

    return is_frozen()


def _get_app_path() -> str:
    from utilities.functions import get_app_path

    return get_app_path()


class UpdateAvailableDialog(QDialog):
    download_now = Signal(dict)
    download_later = Signal()

    def __init__(self, release: dict, parent=None, dev_mode: bool = False):
        super().__init__(parent)
        self._release = release
        self._dev_mode = dev_mode
        tag = release.get("tag_name", "")
        title = release.get("name") or tag
        self.setWindowTitle(_("Update Available - {title}").format(title=title))
        self.setModal(True)
        self.setMinimumSize(560, 420)
        self.resize(640, 500)
        self._build_ui(release, tag)

    def _build_ui(self, release: dict, tag: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        current = os.environ.get("APP_VERSION", "")
        header = QLabel(
            _(
                "<b>A new version of {app} is available!</b><br>"
                "Your version: <b>{current}</b> -> New version: <b>{new}</b>"
            ).format(
                app=os.environ.get("APP_NAME", "PlayForm"),
                current=current,
                new=_strip_v(tag),
            )
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        notes_label = QLabel(_("<b>Release notes:</b>"))
        layout.addWidget(notes_label)

        notes = QTextBrowser()
        notes.setMarkdown(release.get("body") or _("No release notes provided."))
        notes.setMinimumHeight(160)
        layout.addWidget(notes, 1)

        assets = release.get("assets", [])
        if assets:
            files_label = QLabel(_("<b>Release files ({count}):</b>").format(count=len(assets)))
            layout.addWidget(files_label)

            files_list = QListWidget()
            files_list.setMaximumHeight(100)
            for asset in assets:
                size_mb = asset.get("size", 0) / (1024 * 1024)
                item = QListWidgetItem(f"{asset['name']}  ({size_mb:.2f} MB)")
                files_list.addItem(item)
            layout.addWidget(files_list)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        later_btn = QPushButton(_("Download Later"))
        later_btn.setFixedWidth(120)
        later_btn.clicked.connect(self._on_later)
        btn_row.addWidget(later_btn)

        now_btn = QPushButton(_("Download Now"))
        now_btn.setFixedWidth(120)
        now_btn.setDefault(not self._dev_mode)
        now_btn.clicked.connect(self._on_now)
        if self._dev_mode:
            now_btn.setEnabled(False)
            now_btn.setToolTip(
                _(
                    "Automatic download is not available in developer mode.\n"
                    "Please download the update manually from the releases page."
                )
            )
        btn_row.addWidget(now_btn)

        layout.addLayout(btn_row)

    def _on_now(self):
        self.download_now.emit(self._release)
        self.accept()

    def _on_later(self):
        self.download_later.emit()
        self.reject()


class _DownloadProgressDialog(QDialog):
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Downloading Update"))
        self.setModal(True)
        self.setFixedSize(380, 120)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        self._label = QLabel(_("Downloading update files, please wait..."))
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

        cancel_btn = QPushButton(_("Cancel"))
        cancel_btn.clicked.connect(self._on_cancel)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def set_message(self, msg: str):
        self._label.setText(msg)

    def _on_cancel(self):
        self.cancelled.emit()
        self.reject()


class UpdateChecker(QObject):
    update_available = Signal(dict)
    no_update = Signal()
    check_error = Signal(str)
    download_ready = Signal(str, str)

    _singleton = None

    @classmethod
    def instance(cls, parent=None) -> "UpdateChecker":
        if cls._singleton is None:
            cls._singleton = cls(parent)
        return cls._singleton

    def __init__(self, parent=None):
        super().__init__(parent)

        self._repo = os.environ.get("APP_GITHUB_REPO", "")
        self._version = os.environ.get("APP_VERSION", "0.0.0")
        self._platform = _current_platform()
        self._arch = _current_arch()
        self._parent_widget: QWidget | None = parent

        self._nam = QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None
        self._download_nam = QNetworkAccessManager(self)

        self._update_downloader = None
        self._progress_dialog: _DownloadProgressDialog | None = None
        self._pending_release: dict | None = None
        self._expected_count = 0
        self._finished_count = 0

        self._timer = QTimer(self)
        self._timer.setInterval(_12H_MS)
        self._timer.timeout.connect(self.check_now)
        self._timer.start()

        QTimer.singleShot(_CHECK_DELAY_MS, self.check_now)

    def check_now(self, *, silent: bool = True):
        if not self._repo:
            return
        if self._reply and not self._reply.isFinished():
            if not silent:
                self._silent = False
            return

        self._silent = silent
        url = f"https://api.github.com/repos/{self._repo}/releases/latest"
        request = QNetworkRequest(QUrl(url))
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader,
            f"{os.environ.get('APP_NAME', 'App')}/{self._version}",
        )
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        self._reply = self._nam.get(request)
        self._reply.finished.connect(self._on_api_reply)

    @Slot()
    def _on_api_reply(self):
        reply = self._reply
        if reply is None:
            return

        try:
            http_status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            data = bytes(reply.readAll()).decode("utf-8", errors="replace")

            try:
                release = json.loads(data)
            except json.JSONDecodeError:
                release = {}

            if http_status == 404 or (
                reply.error() != QNetworkReply.NetworkError.NoError
                and http_status is not None
                and http_status >= 400
            ):
                self.check_error.emit(
                    release.get("message", _("HTTP {status}").format(status=http_status))
                )
                if not getattr(self, "_silent", True):
                    QMessageBox.information(
                        self._parent_widget,
                        _("No Releases Found"),
                        _("No releases have been published for this application yet."),
                    )
                return

            if reply.error() != QNetworkReply.NetworkError.NoError:
                err = reply.errorString()
                self.check_error.emit(err)
                if not getattr(self, "_silent", True):
                    QMessageBox.warning(
                        self._parent_widget,
                        _("Update Check Failed"),
                        _("Could not reach the update server:\n{error}").format(error=err),
                    )
                return

            if not release or "tag_name" not in release:
                if not getattr(self, "_silent", True):
                    QMessageBox.information(
                        self._parent_widget,
                        _("No Releases Found"),
                        _("No releases have been published for this application yet."),
                    )
                return

            tag = release["tag_name"]
            if _is_newer(tag, self._version):
                self.update_available.emit(release)
                self._show_update_dialog(release)
            else:
                self.no_update.emit()
                if not getattr(self, "_silent", True):
                    QMessageBox.information(
                        self._parent_widget,
                        _("No Update Available"),
                        _("{app} is up to date (version {version}).").format(
                            app=os.environ.get("APP_NAME", "PlayForm"),
                            version=self._version,
                        ),
                    )
        finally:
            reply.deleteLater()
            self._reply = None

    def _show_update_dialog(self, release: dict):
        dlg = UpdateAvailableDialog(release, self._parent_widget, dev_mode=_is_frozen() is False)
        dlg.download_now.connect(self._start_download)
        dlg.exec()

    @Slot(dict)
    def _start_download(self, release: dict):
        if not _is_frozen():
            return

        assets = release.get("assets", [])
        if not assets:
            QMessageBox.warning(
                self._parent_widget,
                _("Update Error"),
                _("No downloadable assets found in this release."),
            )
            return

        manifest_name = f"{self._platform}-{self._arch}-manifest.json"
        manifest_asset = next((a for a in assets if a["name"] == manifest_name), None)
        if manifest_asset is None:
            QMessageBox.warning(
                self._parent_widget,
                _("Update Error"),
                _("No platform manifest found for '{platform}' in this release.").format(
                    platform=self._platform
                ),
            )
            return

        zip_asset = next(
            (a for a in assets if a["name"].endswith(".zip") and self._platform in a["name"].lower()),
            None,
        )
        if zip_asset is None:
            zip_asset = next((a for a in assets if a["name"].endswith(".zip")), None)
        if zip_asset is None:
            QMessageBox.warning(
                self._parent_widget,
                _("Update Error"),
                _("No zip archive found in this release."),
            )
            return

        temp_dir = Path(_get_app_path()) / "update_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_dir_str = str(temp_dir)

        self._pending_release = release
        self._pending_zip_name = zip_asset["name"]
        self._pending_temp_dir = temp_dir_str
        self._expected_count = 2
        self._finished_count = 0
        self._download_failed = False

        from downloader.downloader import Downloader

        if self._update_downloader is not None:
            try:
                self._update_downloader.deleteLater()
            except Exception:
                pass

        self._update_downloader = Downloader(destination=temp_dir_str, max_concurrent=2)
        self._update_downloader.download_finished.connect(self._on_update_file_finished)
        self._update_downloader.all_finished.connect(self._on_all_update_files_finished)

        self._update_downloader.add_download(
            manifest_asset["browser_download_url"],
            destination=temp_dir_str,
            filename=manifest_name,
        )
        self._update_downloader.add_download(
            zip_asset["browser_download_url"],
            destination=temp_dir_str,
            filename=zip_asset["name"],
        )

        self._progress_dialog = _DownloadProgressDialog(self._parent_widget)
        self._progress_dialog.cancelled.connect(self._cancel_update_download)
        self._progress_dialog.set_message(
            _(
                "Downloading update files...\n"
                "  - {manifest}\n"
                "  - {archive}"
            ).format(manifest=manifest_name, archive=zip_asset["name"])
        )
        self._progress_dialog.show()

    @Slot(object, bool)
    def _on_update_file_finished(self, item, success: bool):
        if not success:
            self._download_failed = True

        self._finished_count += 1
        if self._progress_dialog:
            self._progress_dialog.set_message(
                _("Downloaded {finished} / {expected} files...").format(
                    finished=self._finished_count,
                    expected=self._expected_count,
                )
            )

    @Slot()
    def _on_all_update_files_finished(self):
        if self._progress_dialog:
            self._progress_dialog.accept()
            self._progress_dialog = None

        if self._download_failed:
            QMessageBox.critical(
                self._parent_widget,
                _("Update Failed"),
                _("One or more update files failed to download. Please try again later."),
            )
            return

        app_name = os.environ.get("APP_NAME", "PlayForm")
        reply = QMessageBox.question(
            self._parent_widget,
            _("Update Ready"),
            _(
                "The update has been downloaded.\n\n"
                "{app_name} needs to restart to apply it. Restart now?"
            ).format(app_name=app_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._apply_update_and_restart()

    def _cancel_update_download(self):
        if self._update_downloader:
            all_dl = self._update_downloader.get_all_downloads()
            for item in list(all_dl["active"]):
                self._update_downloader.cancel_download(item)
            for item in list(all_dl["queue"]):
                self._update_downloader.cancel_download(item)

    def _apply_update_and_restart(self):
        app_path = Path(_get_app_path())
        temp_dir = self._pending_temp_dir or str(app_path / "update_temp")
        zip_name = getattr(self, "_pending_zip_name", "update.zip")

        if sys.platform == "win32":
            updater_exe = app_path / "updater.exe"
        else:
            updater_exe = app_path / "updater"

        if not updater_exe.exists():
            QMessageBox.critical(
                self._parent_widget,
                _("Updater Not Found"),
                _(
                    "The updater binary was not found at:\n{path}\n\nPlease update manually."
                ).format(path=updater_exe),
            )
            return

        args = [
            str(updater_exe),
            "--temp",
            temp_dir,
            "--zip",
            zip_name,
            "--install-dir",
            str(app_path),
        ]

        try:
            if sys.platform == "win32":
                subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(args)
        except Exception as e:
            QMessageBox.critical(
                self._parent_widget,
                _("Update Error"),
                _("Failed to launch the updater:\n{error}").format(error=e),
            )
            return

        from PySide6.QtWidgets import QApplication

        QApplication.quit()
