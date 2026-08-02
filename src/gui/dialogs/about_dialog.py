"""About dialog – reads all information from environment variables set by app_info."""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{_("About")} {os.environ.get('APP_NAME', 'PlayForm')}")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(520)
        self.ui()


    _DEFAULT_DESCRIPTION = "A modern, accessible media player for audio and video files."

    def ui(self):
        name        = os.environ.get("APP_NAME", "PlayForm")
        version     = os.environ.get("APP_VERSION", "")
        description = os.environ.get("APP_DESCRIPTION", "")
        if description == self._DEFAULT_DESCRIPTION:
            description = _("A modern, accessible media player for audio and video files.")
        publisher   = os.environ.get("APP_PUBLISHER", "")
        copyright_  = os.environ.get("APP_COPYRIGHT", "")
        website     = os.environ.get("APP_WEBSITE", "")
        license_    = os.environ.get("APP_LICENSE", "")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)


        name_label = QLabel(f"<b style='font-size:16pt'>{name}</b>")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        if version:
            ver_label = QLabel(f"{_("Version")} {version}")
            ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(ver_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(desc_label)

        layout.addSpacing(4)


        for label_text, value in [
            (_("Publisher"), publisher),
            (_("License"), license_),
            (_("Copyright"), copyright_),
        ]:
            if value:
                row = QHBoxLayout()
                lbl = QLabel(f"<b>{label_text}:</b>")
                lbl.setFixedWidth(90)
                val = QLabel(value)
                val.setWordWrap(True)
                row.addWidget(lbl)
                row.addWidget(val, 1)
                layout.addLayout(row)

        if website:
            row = QHBoxLayout()
            lbl = QLabel(f"<b>{_("Website")}:</b>")
            lbl.setFixedWidth(90)
            link = QLabel(f'<a href="{website}">{website}</a>')
            link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            link.setOpenExternalLinks(True)
            row.addWidget(lbl)
            row.addWidget(link, 1)
            layout.addLayout(row)

        layout.addSpacing(8)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton(_("Close"))
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
