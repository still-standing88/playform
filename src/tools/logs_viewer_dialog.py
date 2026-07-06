from __future__ import annotations

from pathlib import Path
from typing import Optional
from gettext import gettext as _

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
	QDialog,
	QHBoxLayout,
	QVBoxLayout,
	QListWidget,
	QListWidgetItem,
	QTextEdit,
	QPushButton,
	QLabel,
	QWidget,
	QMessageBox,
)

from utilities.functions import get_logs_dir


class _TabKeyBlocker(QWidget):
	def eventFilter(self, obj, event):  # type: ignore[override]
		if event.type() == QEvent.Type.KeyPress:
			key = event.key()
			if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
				return True
		return super().eventFilter(obj, event)


class LogsViewerDialog(QDialog):
	def __init__(self, parent=None, logs_dir: Optional[Path] = None):
		super().__init__(parent)
		self.setWindowTitle(_("Logs Viewer"))
		self.resize(900, 600)


		self.logs_dir = logs_dir or Path(get_logs_dir())
		self.logs_dir.mkdir(parents=True, exist_ok=True)

		self._tab_blocker = _TabKeyBlocker()


		root = QVBoxLayout(self)
		content = QHBoxLayout()
		root.addLayout(content, 1)

		left_panel = QVBoxLayout()
		self.info_label = QLabel(_("Logs folder: {path}").format(path=self.logs_dir))
		left_panel.addWidget(self.info_label)

		self.files_list = QListWidget()
		self.files_list.setAccessibleName(_("Logs Files List"))
		self.files_list.setAccessibleDescription(_("List of log files in the application's logs folder"))
		left_panel.addWidget(self.files_list, 1)
		content.addLayout(left_panel, 1)


		right_panel = QVBoxLayout()
		self.viewer = QTextEdit()
		self.viewer.setReadOnly(True)
		self.viewer.setTabChangesFocus(True)
		self.viewer.setTextInteractionFlags(
			Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse
		)
		self.viewer.setAccessibleName(_("Log File Viewer"))
		self.viewer.setAccessibleDescription(_("Displays the contents of the selected log file"))
		self.viewer.installEventFilter(self._tab_blocker)
		right_panel.addWidget(self.viewer, 1)

		buttons_row = QHBoxLayout()
		buttons_row.addStretch(1)
		self.close_btn = QPushButton(_("Close"))
		self.close_btn.clicked.connect(self.accept)
		buttons_row.addWidget(self.close_btn)
		right_panel.addLayout(buttons_row)

		content.addLayout(right_panel, 2)


		self.populate_files()
		self.files_list.currentItemChanged.connect(self.on_file_changed)

	def populate_files(self):
		self.files_list.clear()
		log_files = []
		try:
			for p in sorted(self.logs_dir.glob("*")):
				if p.is_file():
					log_files.append(p)
		except Exception:
			log_files = []

		if not log_files:

			self.viewer.setPlainText(_("There aren't any log files yet."))
			no_item = QListWidgetItem(_("(no log files)"))
			no_item.setFlags(no_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
			self.files_list.addItem(no_item)
			return

		for p in log_files:
			item = QListWidgetItem(p.name)
			item.setData(Qt.ItemDataRole.UserRole, p)
			self.files_list.addItem(item)


		if self.files_list.count() > 0:
			self.files_list.setCurrentRow(0)

	def on_file_changed(self, current: QListWidgetItem, previous: Optional[QListWidgetItem]):
		path: Optional[Path] = current.data(Qt.ItemDataRole.UserRole) if current else None
		if not path:
			return
		try:
			
			text = path.read_text(encoding="utf-8", errors="replace")
		except Exception as e:
			text = _("Failed to read file: {path}\nError: {error}").format(path=path, error=e)
		self.viewer.setPlainText(text)

