from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QTextEdit, QPushButton, QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot

from downloader.downloader import Downloader
from utilities.functions import get_parent_dir
from .tool_registry import ALL_TOOLS, ToolDef
from .tool_fetcher import ToolFetcher
from .install_manager import install_tool


class UtilityDownloadDialog(QDialog):

    def __init__(self, downloader: Optional[Downloader] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Utilities")
        self.setModal(True)
        self.setMinimumSize(520, 420)
        self.resize(600, 480)

        self._shared_downloader    = downloader
        self._local_downloader: Optional[Downloader] = None
        self._fetcher              = ToolFetcher(self)
        self._pending_errors: list[str] = []
        self._completed            = 0
        self._expected             = 0
        self._temp_dir             = ""

        self._build_ui()
        self._populate_list()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(QLabel("<b>Select utilities to download:</b>"))

        self._list = QListWidget()
        self._list.setMinimumHeight(130)
        layout.addWidget(self._list)

        layout.addWidget(QLabel("<b>Description:</b>"))

        self._desc = QTextEdit()
        self._desc.setReadOnly(True)
        self._desc.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._desc.setTabChangesFocus(True)
        self._desc.setMinimumHeight(100)
        layout.addWidget(self._desc, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._close_btn = QPushButton("Close")
        self._close_btn.setFixedWidth(90)
        self._close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._close_btn)

        self._download_btn = QPushButton("Download")
        self._download_btn.setFixedWidth(90)
        self._download_btn.setEnabled(False)
        self._download_btn.clicked.connect(self._on_download)
        btn_row.addWidget(self._download_btn)

        layout.addLayout(btn_row)

    def _populate_list(self):
        for tool in ALL_TOOLS:
            item = QListWidgetItem(tool.label)
            item.setData(Qt.ItemDataRole.UserRole, tool)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(Qt.CheckState.Unchecked)
            self._list.addItem(item)

    def _connect_signals(self):
        self._list.currentItemChanged.connect(self._on_selection_changed)
        self._list.itemChanged.connect(self._on_check_changed)
        self._fetcher.fetch_error.connect(self._on_fetch_error)
        self._fetcher.all_done.connect(self._on_links_resolved)

    @Slot()
    def _on_selection_changed(self, current, _prev):
        if current is None:
            self._desc.clear()
            return
        tool: ToolDef = current.data(Qt.ItemDataRole.UserRole)
        if tool:
            self._desc.setPlainText(tool.description)

    @Slot()
    def _on_check_changed(self, _item):
        checked_count = sum(
            1 for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        )
        self._download_btn.setEnabled(checked_count > 0)

    def _checked_tools(self) -> list[ToolDef]:
        result = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result

    @Slot()
    def _on_download(self):
        tools = self._checked_tools()
        if not tools:
            return
        self._pending_errors = []
        self._download_btn.setEnabled(False)
        self._close_btn.setEnabled(False)
        self._desc.setPlainText("Fetching download links from GitHub…")
        self._fetcher.fetch(tools)

    @Slot(str, str)
    def _on_fetch_error(self, tool_name: str, err: str):
        self._pending_errors.append(f"{tool_name}: {err}")

    @Slot(list)
    def _on_links_resolved(self, results: list):
        if self._pending_errors:
            QMessageBox.warning(
                self,
                "Link Fetch Errors",
                "Could not resolve links for the following utilities:\n\n"
                + "\n".join(self._pending_errors),
            )

        if not results:
            self._desc.setPlainText("No links could be resolved.")
            self._close_btn.setEnabled(True)
            self._download_btn.setEnabled(True)
            return

        self._temp_dir = str(Path(get_parent_dir()) / "bin" / "_tmp_util")
        Path(self._temp_dir).mkdir(parents=True, exist_ok=True)

        dl = self._shared_downloader
        if dl is None:
            self._local_downloader = Downloader(
                destination=self._temp_dir, max_concurrent=2
            )
            dl = self._local_downloader

        self._expected  = len(results)
        self._completed = 0

        self._desc.setPlainText(
            f"Downloading {self._expected} file(s), please wait…"
        )

        for r in results:
            def make_cb(entry):
                def cb(success: bool):
                    self._on_file_finished(success, entry)
                return cb

            dl.add_download(
                r["url"],
                destination=self._temp_dir,
                filename=r["filename"],
                finished_callback=make_cb(r),
            )

    def _on_file_finished(self, success: bool, result: dict):
        self._completed += 1
        tool: ToolDef = result["tool"]
        filepath = str(Path(self._temp_dir) / result["filename"])

        if success:
            ok, msg = install_tool(
                filepath,
                tool.name,
                tool.is_zip,
                tool.binary_name_win,
                tool.binary_name_posix,
            )
            if not ok:
                QMessageBox.warning(
                    self,
                    "Install Error",
                    f"Failed to install {tool.label}:\n{msg}",
                )
        else:
            QMessageBox.warning(
                self,
                "Download Error",
                f"Failed to download {tool.label}.",
            )

        if self._completed >= self._expected:
            self._finalize()

    def _finalize(self):
        import shutil
        shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._desc.setPlainText(
            "Done. All selected utilities have been processed.\n"
            "You may close this dialog."
        )
        self._close_btn.setEnabled(True)
        self._download_btn.setEnabled(True)
