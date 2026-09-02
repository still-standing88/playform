"""Review-before-download dialog for playlist/channel/link-file sources.

Tab 1 lists the videos (fetched off-thread via --flat-playlist) in a
checkbox tree with select/deselect-all and a retrieval-progress label;
tab 2 holds format/destination/start-now options; tab 3 mirrors the
yt-dlp log. OK enqueues the checked entries through the engine.
"""

import logging
import threading

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QRadioButton, QCheckBox, QPlainTextEdit,
    QTabWidget, QFileDialog, QMenu, QDialogButtonBox, QMessageBox, QWidget,
)

from media_core.ytdlp_download.engine import fetch_flat_entries

logger = logging.getLogger(__name__)


class _FlatFetchThread(QThread):
    entry_found = Signal(object)
    finished_ok = Signal(int)
    failed = Signal(str)
    log_line = Signal(str)

    def __init__(self, urls: list, parent=None):
        super().__init__(parent)
        self._urls = urls
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def stop_and_wait(self, timeout_ms: int = 5000):
        """Cancel and join. Signals are blocked first so nothing is delivered
        to a caller that is already tearing itself down."""
        self.blockSignals(True)
        self._cancel.set()
        if self.isRunning():
            self.wait(timeout_ms)

    def run(self):
        total = 0
        try:
            def _on_entry(entry):
                nonlocal total
                total += 1
                self.entry_found.emit(entry)

            fetch_flat_entries(
                self._urls,
                on_log=lambda line: self.log_line.emit(line),
                on_entry=_on_entry,
                cancel_event=self._cancel,
            )
        except InterruptedError:
            return
        except Exception as exc:
            logger.warning("Flat listing failed", exc_info=True)
            self.failed.emit(str(exc))
            return
        self.finished_ok.emit(total)


class YtDlpReviewDialog(QDialog):
    def __init__(self, url, kind: str, parent=None):
        super().__init__(parent)
        self._urls = [url] if isinstance(url, str) else list(url)
        self._url = self._urls[0] if self._urls else ""
        self._kind = kind
        self._entries: list = []
        self._thread: _FlatFetchThread | None = None
        self._all_selected = True
        self._source_title = ""

        titles = {
            "playlist": _("Download Playlist"),
            "channel_videos": _("Download Channel Videos"),
            "channel_shorts": _("Download Channel Shorts"),
            "channel_all": _("Download Channel"),
            "link_file": _("Download Links From File"),
        }
        self.setWindowTitle(titles.get(kind, _("Download Videos")))
        self.resize(640, 520)
        self.setMinimumSize(520, 420)
        self._build_ui()
        self._start_fetch()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs, 1)

        # --- Tab 1: video selection -----------------------------------
        selection_tab = QWidget(self)
        selection_layout = QVBoxLayout(selection_tab)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels([_("Videos")])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setAccessibleName(_("Videos to download"))
        self.tree.setAccessibleDescription(
            _("Check the videos to download. Right-click for sorting; use "
              "Select All to toggle every checkbox.")
        )
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_tree_menu)
        selection_layout.addWidget(self.tree, 1)

        controls_row = QHBoxLayout()
        self.toggle_all_button = QPushButton(_("Deselect All"), self)
        self.toggle_all_button.clicked.connect(self._toggle_all)
        controls_row.addWidget(self.toggle_all_button)
        controls_row.addStretch()

        self.progress_label = QLabel(_("Retrieving video list..."), self)
        self.progress_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.progress_label.setAccessibleName(_("Retrieval progress"))
        controls_row.addWidget(self.progress_label)
        selection_layout.addLayout(controls_row)

        self.tabs.addTab(selection_tab, _("Videos"))

        # --- Tab 2: options -------------------------------------------
        options_tab = QWidget(self)
        form = QFormLayout(options_tab)

        self.original_radio = QRadioButton(_("Original format"), self)
        self.audio_radio = QRadioButton(_("Audio only"), self)
        self.video_radio = QRadioButton(_("Video only"), self)
        self.original_radio.setChecked(True)
        form.addRow(QLabel(_("Format:"), self))
        form.addRow(self.original_radio)
        form.addRow(self.audio_radio)
        form.addRow(self.video_radio)

        location_row = QHBoxLayout()
        self.location_edit = QLineEdit(self)
        self.location_edit.setAccessibleName(_("Save location"))
        browse_button = QPushButton(_("Browse..."), self)
        browse_button.clicked.connect(self._browse_location)
        location_row.addWidget(self.location_edit)
        location_row.addWidget(browse_button)
        form.addRow(_("Location:"), location_row)

        self.start_now_check = QCheckBox(_("Start download immediately"), self)
        self.start_now_check.setChecked(True)
        form.addRow(self.start_now_check)

        self.tabs.addTab(options_tab, _("Options"))

        # --- Tab 3: log ------------------------------------------------
        self.log_edit = QPlainTextEdit(self)
        self.log_edit.setReadOnly(True)
        self.log_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.log_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.log_edit.setAccessibleName(_("yt-dlp log"))
        self.tabs.addTab(self.log_edit, _("Log"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)
        layout.addWidget(buttons)

    def set_default_location(self, path: str):
        self.location_edit.setText(path)

    def source_title(self) -> str:
        """Playlist/channel title as reported by yt-dlp, or "" if the
        listing carried none."""
        return self._source_title

    def _start_fetch(self):
        urls = list(self._urls)
        if self._kind == "channel_shorts":
            urls = [self._url.rstrip("/") + "/shorts"]
        elif self._kind == "channel_all":
            urls = [self._url, self._url.rstrip("/") + "/shorts"]

        self._thread = _FlatFetchThread(urls, self)
        self._thread.entry_found.connect(self._on_entry_found)
        self._thread.finished_ok.connect(self._on_fetch_done)
        self._thread.failed.connect(self._on_fetch_failed)
        self._thread.log_line.connect(self.log_edit.appendPlainText)
        self._thread.start()

    def _on_entry_found(self, entry):
        self._entries.append(entry)
        if not self._source_title and entry.get("playlist_title"):
            self._source_title = entry["playlist_title"]
        item = QTreeWidgetItem([entry["title"]])
        item.setData(0, Qt.ItemDataRole.UserRole, entry)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setToolTip(0, entry.get("url", ""))
        self.tree.addTopLevelItem(item)
        self.progress_label.setText(
            _("Retrieved {count} videos...").format(count=len(self._entries))
        )

    def _on_fetch_done(self, count: int):
        self.progress_label.setText(
            _("Retrieval complete: {count} video(s) found").format(count=count)
        )
        self.ok_button.setEnabled(count > 0)

    def _on_fetch_failed(self, message: str):
        self.progress_label.setText(_("Retrieval failed: {error}").format(error=message))

    def done(self, result: int):
        # Single choke point for OK/Cancel/close: the listing thread must be
        # joined before Qt destroys this dialog (its parent), or libQt aborts
        # with "QThread: Destroyed while thread is still running".
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.stop_and_wait()
        super().done(result)

    def _show_tree_menu(self, position):
        menu = QMenu(self)
        date_action = menu.addAction(_("Sort by Date (newest first)"))
        date_action.triggered.connect(lambda: self._sort_by("date"))
        title_action = menu.addAction(_("Sort by Title"))
        title_action.triggered.connect(lambda: self._sort_by("title"))
        duration_action = menu.addAction(_("Sort by Duration"))
        duration_action.triggered.connect(lambda: self._sort_by("duration"))
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _sort_by(self, key: str):
        def sort_key(entry):
            value = entry.get(key) or ""
            if key == "date":
                return str(value)
            if key == "duration":
                try:
                    return float(value or 0)
                except (TypeError, ValueError):
                    return 0.0
            return str(value).lower()

        reverse = key == "date"
        self._entries.sort(key=sort_key, reverse=reverse)
        checked_urls = {e["url"] for e in self._checked_entries()}
        self.tree.clear()
        for entry in self._entries:
            item = QTreeWidgetItem([entry["title"]])
            item.setData(0, Qt.ItemDataRole.UserRole, entry)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked if entry["url"] in checked_urls else Qt.CheckState.Unchecked)
            self.tree.addTopLevelItem(item)

    def _toggle_all(self):
        self._all_selected = not self._all_selected
        state = Qt.CheckState.Checked if self._all_selected else Qt.CheckState.Unchecked
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(0, state)
        self.toggle_all_button.setText(_("Deselect All") if self._all_selected else _("Select All"))

    def _checked_entries(self) -> list:
        selected = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                selected.append(item.data(0, Qt.ItemDataRole.UserRole))
        return selected

    def _browse_location(self):
        directory = QFileDialog.getExistingDirectory(
            self, _("Select Save Location"), self.location_edit.text())
        if directory:
            self.location_edit.setText(directory)

    def _format_mode(self) -> str:
        if self.audio_radio.isChecked():
            return "audio"
        if self.video_radio.isChecked():
            return "video"
        return "original"

    def _on_accept(self):
        if not self._checked_entries():
            QMessageBox.information(self, _("No Selection"),
                                    _("Check at least one video to download."))
            return
        if not self.location_edit.text().strip():
            QMessageBox.information(self, _("No Location"),
                                    _("Choose a save location first."))
            return
        self.accept()

    def selected_entries(self) -> list:
        return self._checked_entries()

    def options(self) -> dict:
        return {
            "format_mode": self._format_mode(),
            "destination": self.location_edit.text().strip(),
            "start_now": self.start_now_check.isChecked(),
        }
