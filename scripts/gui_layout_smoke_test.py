"""Exercise zoom and constrained layouts without touching the user's settings.

Run with the project's Python: python scripts/gui_layout_smoke_test.py
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QDockWidget, QFormLayout, QGroupBox,
                               QLabel, QMainWindow, QScrollArea, QStatusBar,
                               QStyle, QStyleOptionGroupBox, QToolBar, QToolButton, QSizePolicy,
                               QWidget)

from utilities import functions

_test_data = tempfile.TemporaryDirectory(prefix="playform-layout-test-")
_assets = functions.get_assets_dir()
functions.get_app_path = lambda: _test_data.name
functions.get_assets_dir = lambda: _assets

from utilities.i18n import install_translation

install_translation()

from app_init import apply_ui_zoom
from gui.prefs_panels import PreferencesDialog
from gui.main_window import MainWindow
from gui.managers.dock_manager import DockManager
from gui_controls.color_button import ColorButton
from gui_controls.flow_layout import FlowContainer, FlowLayout
from gui_controls.toggle_button import ToggleButton
from player.player_widget import PlayerWidget
from utilities.theme_manager import apply_theme
from app_constance.styles import get_theme_palette
from EXPLORER.explorer_widget import ExplorerWidget
from app_db import user_db, media_db


def settle():
    for _ in range(15):
        QApplication.processEvents()


def luminance(channels):
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        user_db.close_connection()
        media_db.close_connection()
        _test_data.cleanup()

    def setUp(self):
        apply_theme("light", self.app)
        apply_ui_zoom(self.app, 0)
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        settle()

    def keep(self, widget):
        self.widgets.append(widget)
        return widget

    def test_live_zoom_updates_existing_styled_widgets(self):
        label = self.keep(QLabel("Existing label"))
        label.setStyleSheet("font-weight: bold;")
        toggle = self.keep(ToggleButton("Minimize"))
        color = self.keep(ColorButton("Text colour"))
        for theme in ("light", "dark"):
            apply_theme(theme, self.app)
            for level in (10, 0, -4, 10):
                apply_ui_zoom(self.app, level)
                settle()
                for widget in (label, toggle, color):
                    self.assertEqual(widget.font().pointSize(), 9 + level)
                self.assertGreaterEqual(toggle.minimumHeight(), toggle.sizeHint().height())

    def test_group_titles_have_room_at_each_zoom(self):
        group = self.keep(QGroupBox("Transfers"))
        form = QFormLayout(group)
        field = QLabel("Download settings")
        form.addRow(field)
        group.resize(500, 150)
        group.show()
        for theme in ("light", "dark"):
            apply_theme(theme, self.app)
            for level in (-4, 0, 10):
                apply_ui_zoom(self.app, level)
                settle()
                option = QStyleOptionGroupBox()
                group.initStyleOption(option)
                title = group.style().subControlRect(QStyle.ComplexControl.CC_GroupBox, option,
                                                     QStyle.SubControl.SC_GroupBoxLabel, group)
                self.assertGreaterEqual(title.top(), 0)
                self.assertGreaterEqual(title.height(), group.fontMetrics().height())
                self.assertGreater(field.y(), title.bottom())

    def test_dense_preferences_scroll_without_compressing_fields(self):
        for level in (0, 10):
            apply_ui_zoom(self.app, level)
            dialog = self.keep(PreferencesDialog(audio_devices=["Default"]))
            dialog.resize(500, 400)
            dialog.show()
            settle()
            self.assertEqual(dialog.tab_widget.count(), 7)
            for index, last in ((2, dialog.subtitles_panel.ass_override_combo),
                                (6, dialog.downloads_panel.proxy_summary_edit)):
                dialog.tab_widget.setCurrentIndex(index)
                settle()
                scroll = dialog.tab_widget.widget(index)
                self.assertIsInstance(scroll, QScrollArea)
                scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
                settle()
                point = last.mapTo(scroll.viewport(), QPoint(0, 0))
                self.assertGreaterEqual(point.y(), 0)
                self.assertLessEqual(point.y() + last.height(), scroll.viewport().height())
                self.assertGreaterEqual(last.height(), last.minimumSizeHint().height())
                if level == 10:
                    self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
            dialog.subtitles_panel.render_check.setChecked(False)
            self.assertFalse(dialog.subtitles_panel.font_size_spin.isEnabled())
            dialog.subtitles_panel.render_check.setChecked(True)
            self.assertTrue(dialog.subtitles_panel.font_size_spin.isEnabled())

    def test_swatch_text_contrast_and_alpha_round_trip(self):
        button = self.keep(ColorButton("Text colour"))
        for theme in ("light", "dark"):
            apply_theme(theme, self.app)
            background = QColor(get_theme_palette().COLOR_BACKGROUND_1).getRgbF()[:3]
            for value in ("#FFFFFFFF", "#FF000000", "#FF808080", "#AF000000", "#00000000"):
                button.set_color(value)
                settle()
                self.assertEqual(button.color(), value)
                swatch = QColor(value)
                composite = [swatch.alphaF() * c + (1 - swatch.alphaF()) * b
                             for c, b in zip(swatch.getRgbF()[:3], background)]
                text = button.palette().color(button.foregroundRole()).getRgbF()[:3]
                high, low = sorted((luminance(composite), luminance(text)), reverse=True)
                self.assertGreaterEqual((high + 0.05) / (low + 0.05), 4.5)
            transparent_style = button.styleSheet()
            apply_theme("light" if theme == "dark" else "dark", self.app)
            self.assertNotEqual(transparent_style, button.styleSheet())

    def test_flow_measures_unshown_children_and_skips_hidden_items(self):
        container = self.keep(FlowContainer())
        flow = FlowLayout(container)
        flow.addWidget(QLabel("First"))
        second = QLabel("Second")
        flow.addWidget(second)
        before = flow.heightForWidth(70)
        self.assertGreater(before, 0)
        second.hide()
        self.assertLess(flow.heightForWidth(70), before)
        container.show()
        settle()
        shown_height = flow.heightForWidth(70)
        container.hide()
        self.assertEqual(flow.heightForWidth(70), shown_height)

    def test_toggle_cycles_do_not_grow_minimum_size(self):
        button = self.keep(ToggleButton("Minimize"))
        button.show()
        settle()
        before = button.minimumSize()
        for _ in range(3):
            button.setActuated(True)
            QTest.qWait(260)
            button.setActuated(False)
            QTest.qWait(260)
        self.assertEqual(button.minimumSize(), before)

    def test_player_controls_and_status_fit_short_docked_windows(self):
        window = self.keep(QMainWindow())
        area = QRect(0, 0, 1280, 720)
        window.screen = lambda: type("Screen", (), {"availableGeometry": lambda _: area})()
        placeholder = QWidget()
        placeholder.setFixedSize(0, 0)
        window.setCentralWidget(placeholder)
        window.status_bar = QStatusBar()
        window.setStatusBar(window.status_bar)
        window.status_label = QLabel("Ready")
        window.media_info_label = QLabel("")
        window.status_bar.addWidget(window.status_label)
        window.status_bar.addPermanentWidget(window.media_info_label)
        window.dock_manager = DockManager(window)
        window.refresh_ui_layout = lambda: MainWindow.refresh_ui_layout(window)

        # Construct the real player layout, without starting the media backend.
        player = PlayerWidget.__new__(PlayerWidget)
        QWidget.__init__(player, window)
        player._main_window = window
        player.setup_ui()
        player.layout_widgets()
        player.player_controls.time_update_timer.stop()
        player.toggle_accordion_btn.actuated.connect(player._on_accordion_panel_toggled)
        player.toggle_accordion_btn.setActuated(True)
        window.player_widget = player
        window.player_dock = QDockWidget("Player", window)
        window.player_dock.setWidget(player)
        window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, window.player_dock)
        window.dock_manager.player_dock = window.player_dock

        with patch("EXPLORER.explorer_widget.VideoPlayer") as backend:
            backend.return_value.get_devices.return_value = 0
            window.explorer_widget = ExplorerWidget(user_db, parent=window)
        window.explorer_widget._player_state_timer.stop()
        window.explorer_dock = QDockWidget("Explorer", window)
        window.explorer_dock.setWidget(window.explorer_widget)
        window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, window.explorer_dock)
        window.recents_favorites_dock = None
        window.playlists_dock = None
        window.radio_dock = None
        window.podcast_dock = None

        window.menuBar().addMenu("File")
        toolbar = QToolBar("Main")
        for label in ("Open File", "Open Playlist", "Open URL", "Play/Pause", "Batch Converter"):
            toolbar.addAction(label)
        window.addToolBar(toolbar)
        window.addToolBarBreak()
        panels = QToolBar("Panels")
        container = FlowContainer()
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        flow = FlowLayout(container, margin=2)
        for label in ("Player", "Recents/Favorites", "Explorer", "Playlists", "Radio", "Podcasts", "Console"):
            flow.addWidget(QLabel(label))
            for text in ("Show", "Float"):
                button = QToolButton()
                button.setText(text)
                flow.addWidget(button)
        panels.addWidget(container)
        window.addToolBar(panels)
        window.show()

        for level, width, height in ((0, 1280, 720), (10, 1280, 720), (10, 900, 640)):
            area.setSize(QRect(0, 0, width, height).size())
            apply_ui_zoom(self.app, level)
            settle()
            for explorer_visible in (False, True):
                window.explorer_dock.setVisible(explorer_visible)
                window.dock_manager.clamp_to_screen()
                settle()
                self.assertFalse(window.dock_manager._fitting_screen)
                self.assertEqual(window.maximumHeight(), 16777215)
                self.assertLessEqual(window.frameGeometry().bottom(), area.bottom())
                self.assertGreaterEqual(window.status_bar.height(), window.status_label.fontMetrics().height() + 8)
                self.assertLessEqual(window.status_bar.geometry().bottom(), window.height() - 1)
                self.assertLess(window.player_dock.geometry().bottom(), window.status_bar.y())
                for button in (player.player_controls.toggle_controls_btn, player.player_controls.more_btn):
                    scroll = player.controls_scroll
                    scroll.ensureWidgetVisible(button, 0, 0)
                    settle()
                    point = button.mapTo(window, QPoint(0, 0))
                    self.assertTrue(window.rect().contains(QRect(point, button.size())),
                                    f"Control outside window: {level=}, {width=}, {height=}, {explorer_visible=}, "
                                    f"button={button.text()!r} at {QRect(point, button.size())}, window={window.rect()}, "
                                    f"controls={player.player_controls.geometry()}, "
                                    f"control_position={player.player_controls.mapTo(window, QPoint(0, 0))}, "
                                    f"dock={window.player_dock.geometry()}, player={player.geometry()}, "
                                    f"splitter={player.main_splitter.geometry()}, media={player.media_scroll.geometry()}, "
                                    f"status={window.status_bar.geometry()}, "
                                    f"panels={panels.geometry()}, panel_container={container.geometry()}, "
                                    f"panel_hint={container.sizeHint()}, panel_min={container.minimumSizeHint()}, "
                                    f"main_toolbar={toolbar.geometry()}, window_min={window.minimumSizeHint()}, "
                                    f"flow={player.player_controls.buttons_container.geometry()}, "
                                    f"needed={player.player_controls.buttons_flow.heightForWidth(player.player_controls.buttons_container.width())}")
                for minimized in (True, False):
                    player.player_controls.toggle_controls(minimized)
                    settle()
                    self.assertEqual(player.controls_scroll.maximumHeight(), player.player_controls.sizeHint().height())


if __name__ == "__main__":
    unittest.main(verbosity=2)
