from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal


class CommentsFetchThread(QThread):
    finished_ok = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            from player.url import fetch_video_comments
            comments = fetch_video_comments(self.url)
            self.finished_ok.emit(comments)
        except Exception as e:
            self.error_occurred.emit(str(e))


class YouTubeCommentsDialog(QDialog):
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.comments: List[dict] = []
        self.worker: Optional[CommentsFetchThread] = None

        self.setWindowTitle(_("Video Comments"))
        self.resize(600, 500)

        self.setup_ui()

        self.worker = CommentsFetchThread(url, self)
        self.worker.finished_ok.connect(self.on_comments_loaded)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.status_label = QLabel(_("Fetching comments... this may take a while."), self)
        layout.addWidget(self.status_label)

        self.comments_list = QListWidget(self)
        self.comments_list.setAlternatingRowColors(True)
        self.comments_list.setWordWrap(True)
        layout.addWidget(self.comments_list, 1)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton(_("Save to File..."), self)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_comments)
        button_layout.addWidget(self.save_button)

        button_layout.addStretch()

        self.close_button = QPushButton(_("Close"), self)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    @staticmethod
    def _format_comment(comment: dict) -> str:
        author = comment.get("author") or _("Unknown")
        likes = comment.get("like_count") or 0
        text = (comment.get("text") or "").strip()
        return f"{author} ({likes} likes)\n{text}"

    def on_comments_loaded(self, comments: List[dict]):
        self.comments = comments
        self.status_label.setText(_("{count} comment(s) loaded").format(count=len(comments)))

        self.comments_list.clear()
        for comment in comments:
            item = QListWidgetItem(self._format_comment(comment))
            self.comments_list.addItem(item)

        self.save_button.setEnabled(bool(comments))

    def on_error(self, error_msg: str):
        self.status_label.setText(_("Error fetching comments: {error}").format(error=error_msg))

    def save_comments(self):
        if not self.comments:
            return

        save_path, _filter = QFileDialog.getSaveFileName(self, _("Save Comments"), "comments.txt")
        if not save_path:
            return

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                for comment in self.comments:
                    f.write(self._format_comment(comment) + "\n\n")
            QMessageBox.information(self, _("Saved"), _("Comments saved to {path}").format(path=save_path))
        except Exception as e:
            QMessageBox.warning(self, _("Save Failed"), str(e))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
        super().closeEvent(event)
