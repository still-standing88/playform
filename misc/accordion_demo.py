"""
Demo: Accordion used as the contents of a narrow media-player side panel
(chapters / subtitles / filters / EQ) - the scenario this was built for.

Run:
    python3 demo.py
"""
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QListWidget, QCheckBox, QSlider, QComboBox
)
from PySide6.QtCore import Qt
from accordion import Accordion


def chapters_panel():
    w = QListWidget()
    w.addItems([f"Chapter {i}" for i in range(1, 6)])
    return w


def subtitles_panel():
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.addWidget(QCheckBox("Show subtitles"))
    combo = QComboBox()
    combo.addItems(["English", "Spanish", "French", "Off"])
    layout.addWidget(combo)
    return w


def filters_panel():
    w = QWidget()
    layout = QVBoxLayout(w)
    for name in ["Sharpen", "Denoise", "Deinterlace"]:
        layout.addWidget(QCheckBox(name))
    return w


def eq_panel():
    w = QWidget()
    layout = QVBoxLayout(w)
    for band in ["60Hz", "250Hz", "1kHz", "4kHz", "12kHz"]:
        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.addWidget(QLabel(band))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(-12, 12)
        row_layout.addWidget(slider)
        layout.addWidget(row)
    return w


class SidePanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Player Side Panel (Accordion demo)")
        accordion = Accordion()
        accordion.add_section("Chapters", chapters_panel())
        accordion.add_section("Subtitles", subtitles_panel())
        accordion.add_section("Filters", filters_panel())
        accordion.add_section("Equalizer", eq_panel())
        self.setCentralWidget(accordion)
        self.resize(260, 480)  # narrow, like a dock panel


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SidePanel()
    win.show()
    sys.exit(app.exec())
