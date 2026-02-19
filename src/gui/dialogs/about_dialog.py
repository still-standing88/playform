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
        self.setWindowTitle(f"About {os.environ.get('APP_NAME', 'PlayForm')}")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(520)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        name        = os.environ.get("APP_NAME", "PlayForm")
        version     = os.environ.get("APP_VERSION", "")
        description = os.environ.get("APP_DESCRIPTION", "")
        publisher   = os.environ.get("APP_PUBLISHER", "")
        copyright_  = os.environ.get("APP_COPYRIGHT", "")
        website     = os.environ.get("APP_WEBSITE", "")
        license_    = os.environ.get("APP_LICENSE", "")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)

        # ── App name + version ──────────────────────────────────────
        name_label = QLabel(f"<b style='font-size:16pt'>{name}</b>")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        if version:
            ver_label = QLabel(f"Version {version}")
            ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(ver_label)

        # ── Separator ───────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # ── Description ─────────────────────────────────────────────
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(desc_label)

        layout.addSpacing(4)

        # ── Info rows ───────────────────────────────────────────────
        for label_text, value in [
            ("Publisher", publisher),
            ("License", license_),
            ("Copyright", copyright_),
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

        # ── Website link ────────────────────────────────────────────
        if website:
            row = QHBoxLayout()
            lbl = QLabel("<b>Website:</b>")
            lbl.setFixedWidth(90)
            link = QLabel(f'<a href="{website}">{website}</a>')
            link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            link.setOpenExternalLinks(True)
            row.addWidget(lbl)
            row.addWidget(link, 1)
            layout.addLayout(row)

        layout.addSpacing(8)

        # ── Close button ─────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
