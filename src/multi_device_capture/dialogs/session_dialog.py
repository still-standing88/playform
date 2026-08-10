from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from ..models import Session, media_type_label, new_id
from ..registries import SourceRegistry


class SessionDialog(QDialog):
    def __init__(self, sources: SourceRegistry, session: Optional[Session] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Edit session") if session else _("Add session"))
        self._sources = sources
        self._session = session

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit(session.name if session else "")
        form.addRow(_("Name"), self.name_edit)

        self.output_edit = QLineEdit(session.output_dir if session else "")
        browse_row = QHBoxLayout()
        browse_row.addWidget(self.output_edit)
        browse_btn = QPushButton(_("Browse"))
        browse_btn.clicked.connect(self._browse_output)
        browse_row.addWidget(browse_btn)
        form.addRow(_("Output directory"), browse_row)

        self.container_combo = QComboBox()
        self.container_combo.addItems(["mkv", "mp4", "mov"])
        if session:
            idx = self.container_combo.findText(session.container_format)
            if idx >= 0:
                self.container_combo.setCurrentIndex(idx)
        form.addRow(_("Container format"), self.container_combo)

        layout.addLayout(form)

        layout.addWidget(QLabel(_("Sources included in this session")))
        self.source_list = QListWidget()
        selected_ids = set(session.source_ids) if session else set()
        for src in sources.all():
            item = QListWidgetItem(f"{src.friendly_name}  ({media_type_label(src.media_type)})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if src.id in selected_ids else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, src.id)
            self.source_list.addItem(item)
        layout.addWidget(self.source_list)

        self.override_check = QCheckBox(_("Use custom audio/video settings for this session"))
        self.override_check.setChecked(session.settings_override is not None if session else False)
        layout.addWidget(self.override_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, _("Select output directory"))
        if path:
            self.output_edit.setText(path)

    def result_session(self) -> Session:
        source_ids = []
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                source_ids.append(item.data(Qt.ItemDataRole.UserRole))

        override = {} if self.override_check.isChecked() else None

        if self._session:
            self._session.name = self.name_edit.text()
            self._session.source_ids = source_ids
            self._session.output_dir = self.output_edit.text()
            self._session.container_format = self.container_combo.currentText()
            self._session.settings_override = override
            return self._session

        return Session(
            id=new_id(),
            name=self.name_edit.text(),
            source_ids=source_ids,
            output_dir=self.output_edit.text(),
            container_format=self.container_combo.currentText(),
            settings_override=override,
        )
