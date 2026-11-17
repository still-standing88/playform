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

from media_core.av_capture.models import (
    AUDIO_CONTAINERS, VIDEO_CONTAINERS, DEFAULT_AUDIO_FORMAT, DEFAULT_VIDEO_FORMAT,
)

from ..models import Session, default_capture_directory, new_id


class SessionDialog(QDialog):
    def __init__(self, session: Optional[Session] = None, default_output_dir: str = "",
                 *, audio_format: str = DEFAULT_AUDIO_FORMAT, video_format: str = DEFAULT_VIDEO_FORMAT, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Edit session") if session else _("New session"))
        self._session = session

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(session.name if session else "")
        form.addRow(_("Name"), self.name_edit)

        self._default_output_dir = default_output_dir or default_capture_directory()
        self.output_edit = QLineEdit(session.output_dir if session else self._default_output_dir)
        self.output_edit.setPlaceholderText(self._default_output_dir)
        browse_row = QHBoxLayout()
        browse_row.addWidget(self.output_edit)
        browse_btn = QPushButton(_("Browse"))
        browse_btn.clicked.connect(self._browse_output)
        browse_row.addWidget(browse_btn)
        form.addRow(_("Output directory"), browse_row)

        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(AUDIO_CONTAINERS)
        self.audio_format_combo.setCurrentText(session.audio_format if session else audio_format)
        form.addRow(_("Audio-only format"), self.audio_format_combo)

        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(VIDEO_CONTAINERS)
        self.video_format_combo.setCurrentText(session.video_format if session else video_format)
        self.video_format_combo.setToolTip(_("Used for the session when an enabled video source is available."))
        form.addRow(_("Video format"), self.video_format_combo)

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
        path = QFileDialog.getExistingDirectory(
            self, _("Select output directory"), self.output_edit.text().strip() or self._default_output_dir
        )
        if path:
            self.output_edit.setText(path)

    def result_session(self) -> Session:
        name = self.name_edit.text().strip()
        output_dir = self.output_edit.text().strip() or self._default_output_dir
        audio_format = self.audio_format_combo.currentText()
        video_format = self.video_format_combo.currentText()

        if self._session:
            self._session.name = name
            self._session.output_dir = output_dir
            self._session.audio_format = audio_format
            self._session.video_format = video_format
            return self._session

        return Session(id=new_id(), name=name, output_dir=output_dir, audio_format=audio_format, video_format=video_format)
