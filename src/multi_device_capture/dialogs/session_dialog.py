"""Session editor: name, output directory, container format only.

The source checklist the previous version of this dialog had is gone -
sources are now managed directly from the (session-scoped) source list in
views/configure_view.py, "Add source" attaches straight to whichever
session is selected rather than going through a separate assign-to-session
step here. The "use custom audio/video settings for this session" checkbox
is gone too: it toggled Session.settings_override between {} and None, but
nothing ever read that field to actually override anything - dropped rather
than kept as a control with no effect. The field itself is still accepted
on load for old sessions.json files, just not exposed here.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ..models import Session, new_id


class SessionDialog(QDialog):
    def __init__(self, session: Optional[Session] = None, default_output_dir: str = "",
                 default_container: str = "mkv", parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Edit session") if session else _("New session"))
        self._session = session

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(session.name if session else "")
        form.addRow(_("Name"), self.name_edit)

        self.output_edit = QLineEdit(session.output_dir if session else default_output_dir)
        browse_row = QHBoxLayout()
        browse_row.addWidget(self.output_edit)
        browse_btn = QPushButton(_("Browse"))
        browse_btn.clicked.connect(self._browse_output)
        browse_row.addWidget(browse_btn)
        form.addRow(_("Output directory"), browse_row)

        self.container_combo = QComboBox()
        self.container_combo.addItems(["mkv", "mp4", "mov"])
        self.container_combo.setCurrentText(session.container_format if session else default_container)
        form.addRow(_("Container format"), self.container_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(bool(self.name_edit.text().strip()))
        self.name_edit.textChanged.connect(lambda text: self._ok_button.setEnabled(bool(text.strip())))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, _("Select output directory"))
        if path:
            self.output_edit.setText(path)

    def result_session(self) -> Session:
        name = self.name_edit.text().strip()
        output_dir = self.output_edit.text()
        container = self.container_combo.currentText()

        if self._session:
            self._session.name = name
            self._session.output_dir = output_dir
            self._session.container_format = container
            return self._session

        return Session(id=new_id(), name=name, source_ids=[], output_dir=output_dir, container_format=container)
