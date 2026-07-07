from gettext import gettext as _
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton, 
    QLabel, QProgressBar, QWidget, QListWidget, QListWidgetItem,
    QSplitter, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QMutex, QWaitCondition, QTimer
from PySide6.QtGui import QFont


class YtDlpWorker(QThread):

    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self._mutex = QMutex()
        self._cond = QWaitCondition()
        self._abort = False
    
    def abort(self):
        self._mutex.lock()
        self._abort = True
        self._mutex.unlock()
        self._cond.wakeAll()
    
    def run(self):
        try:
            from player.url import fetch_full_info
            info = fetch_full_info(self.url)

            self._mutex.lock()
            cancelled = self._abort
            self._mutex.unlock()
            if cancelled:
                return

            self.finished.emit(info)
        except Exception as e:
            self.error.emit(str(e))


class YouTubeInfoDialog(QDialog):

    STAT_FIELDS = [
        ("title",         "Title"),
        ("uploader",      "Channel"),
        ("channel",       "Channel name"),
        ("upload_date",   "Uploaded"),
        ("duration",      "Duration"),
        ("view_count",    "Views"),
        ("like_count",    "Likes"),
        ("comment_count", "Comments"),
        ("age_limit",     "Age limit"),
        ("availability",  "Availability"),
        ("live_status",   "Live status"),
        ("categories",    "Categories"),
        ("tags",          "Tags"),
        ("webpage_url",   "URL"),
    ]

    def __init__(self, url: str, parent=None, cached_info: Optional[dict] = None):
        super().__init__(parent)
        self.url = url
        self.worker: Optional[YtDlpWorker] = None
        self.cached_info = cached_info
        self._loading_started = False
        
        self.setWindowTitle(_("Video Information"))
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(680, 600)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.loading_label = QLabel(_("Fetching video information..."))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMaximumWidth(300)
        loading_layout.addWidget(self.progress_bar, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.loading_widget)
        
        self.result_widget = QWidget()
        result_layout = QVBoxLayout(self.result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(6)
        
        self.stats_label = QLabel(_("Video Stats"))
        stats_font = QFont()
        stats_font.setBold(True)
        stats_font.setPointSize(11)
        self.stats_label.setFont(stats_font)
        result_layout.addWidget(self.stats_label)
        
        self.stats_list = QListWidget()
        self.stats_list.setAlternatingRowColors(True)
        self.stats_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.stats_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stats_list.setTabChangesFocus(True)
        self.stats_list.setFixedHeight(200)
        result_layout.addWidget(self.stats_list)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        result_layout.addWidget(sep)
        
        self.desc_label = QLabel(_("Description"))
        desc_font = QFont()
        desc_font.setBold(True)
        desc_font.setPointSize(11)
        self.desc_label.setFont(desc_font)
        result_layout.addWidget(self.desc_label)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setReadOnly(True)
        self.desc_edit.setTabChangesFocus(True)
        self.desc_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        result_layout.addWidget(self.desc_edit, 1)
        
        self.result_widget.hide()
        layout.addWidget(self.result_widget, 1)
        
        button_layout = __import__("PySide6.QtWidgets", fromlist=["QHBoxLayout"]).QHBoxLayout()
        button_layout.addStretch()
        self.close_button = QPushButton(_("Close"))
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
    
    def showEvent(self, event):
        super().showEvent(event)
        if not self._loading_started:
            self._loading_started = True
            if self.cached_info:
                self.on_info_loaded(self.cached_info)
            else:
                QTimer.singleShot(100, self.start_loading)
    
    def start_loading(self):
        self.worker = YtDlpWorker(self.url)
        self.worker.finished.connect(self.on_info_loaded)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def _format_value(self, key: str, value) -> str:
        if value is None or value == "":
            return "-"
        if key == "upload_date" and isinstance(value, str) and len(value) == 8:
            try:
                y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
                from datetime import date
                return date(y, m, d).strftime("%d %B %Y")
            except Exception:
                return value
        if key == "duration" and isinstance(value, (int, float)):
            seconds = int(value)
            h, remainder = divmod(seconds, 3600)
            m, s = divmod(remainder, 60)
            if h > 0:
                return f"{h}:{m:02d}:{s:02d}"
            return f"{m}:{s:02d}"
        if isinstance(value, float):
            return f"{value:.0f}" if value == int(value) else f"{value:.2f}"
        if isinstance(value, int):
            if key in ("view_count", "like_count", "comment_count"):
                return f"{value:,}"
            return str(value)
        if isinstance(value, list):
            return ", ".join(str(v) for v in value[:10])
        return str(value)
    
    def on_info_loaded(self, info: dict):
        self.cached_info = info
        self.loading_widget.hide()
        self.result_widget.show()

        self.stats_list.clear()
        for key, label_text in self.STAT_FIELDS:
            value = info.get(key)
            if value is None or value == "" or value == [] or value == 0:
                continue
            if key == "uploader" and info.get("channel") == value:
                continue
            formatted = self._format_value(key, value)
            item = QListWidgetItem(f"{_(label_text)}:  {formatted}")
            item.setToolTip(formatted)
            self.stats_list.addItem(item)

        description = info.get("description") or ""
        self.desc_edit.setPlainText(description)
    
    def on_error(self, error_msg: str):
        self.loading_widget.hide()
        self.result_widget.show()
        self.stats_list.clear()
        self.desc_edit.setPlainText(f"{_('Error fetching video information:')}\n\n{error_msg}")
    
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.abort()
            self.worker.quit()
            self.worker.wait(3000)
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
        super().closeEvent(event)
