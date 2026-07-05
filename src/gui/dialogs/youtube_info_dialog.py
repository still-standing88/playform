import json
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton, 
    QLabel, QProgressBar, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QMutex, QWaitCondition
from PySide6.QtGui import QFont, QTextCursor


class YtDlpWorker(QThread):

    finished = Signal(str)
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

            json_str = json.dumps(info, indent=2, ensure_ascii=False)
            self.finished.emit(json_str)
        except Exception as e:
            self.error.emit(str(e))


class YouTubeInfoDialog(QDialog):


    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.worker: Optional[YtDlpWorker] = None
        self.cached_result: Optional[str] = None
        
        self.setWindowTitle(_("YouTube Video Information"))
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(700, 500)
        
        self.setup_ui()
        self.start_loading()
    
    def setup_ui(self):

        layout = QVBoxLayout(self)
        
        # Loading widget (initially visible)
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        
        self.loading_label = QLabel(_("Fetching video information..."))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        loading_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.loading_widget)
        
        # Result widget (initially hidden)
        self.result_widget = QWidget()
        result_layout = QVBoxLayout(self.result_widget)
        
        self.info_label = QLabel(_("Video Information:"))
        result_layout.addWidget(self.info_label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text_edit.setTabChangesFocus(True)
        self.text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        
        # Monospace font for better JSON readability
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.text_edit.setFont(font)
        
        result_layout.addWidget(self.text_edit)
        
        self.result_widget.hide()
        layout.addWidget(self.result_widget)
        
        self.close_button = QPushButton(_("Close"))
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button)
    
    def start_loading(self):
        self.worker = YtDlpWorker(self.url)
        self.worker.finished.connect(self.on_info_loaded)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_info_loaded(self, json_str: str):
        self.cached_result = json_str
        self.loading_widget.hide()
        self.result_widget.show()
        self.text_edit.setPlainText(json_str)
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text_edit.setTextCursor(cursor)
    
    def on_error(self, error_msg: str):
        self.loading_widget.hide()
        self.result_widget.show()
        self.text_edit.setPlainText(f"{_("Error fetching video information:")}\n\n{error_msg}")
    
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.abort()
            self.worker.quit()
            self.worker.wait(3000)
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
        super().closeEvent(event)
