"""Exercise touch input and playback wiring without changing user settings."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QTouchEvent, QFont, QFontDatabase, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMenu, QWidget

from utilities import functions

_test_data = tempfile.TemporaryDirectory(prefix="playform-touch-test-")
_assets = functions.get_assets_dir()
functions.get_app_path = lambda: _test_data.name
functions.get_assets_dir = lambda: _assets

from utilities.i18n import install_translation

install_translation()

from app_config.touch_config import TouchConfig
from app_constance.touch_gestures import default_settings, normalize_settings
from app_db import app_settings, user_db, media_db
from gui.dialogs.touch_gestures_dialog import TouchGesturesDialog
from gui.managers.menu_manager import MenuManager
from gui_controls.touch_gesture_controller import TouchGestureController
from media_core.av_play import AVMediaInstance, AVPlaybackState
from player.player_widget import PlayerWidget
from utilities.theme_manager import apply_theme


class MemoryStore:
    def __init__(self):
        self.data = {}
        self.fail = False

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        if self.fail:
            return False
        self.data[key] = value
        return True


class MouseSurface(QWidget):
    def __init__(self):
        super().__init__()
        self.mouse_presses = 0

    def mousePressEvent(self, event):
        self.mouse_presses += 1
        event.accept()


class TouchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        if Path("C:/Windows/Fonts/segoeui.ttf").exists():
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
            cls.app.setFont(QFont("Segoe UI", 10))

    def setUp(self):
        self.device = QTest.createTouchDevice()
        self.widgets = []
        self.surface = self.keep(MouseSurface())
        self.surface.resize(600, 360)
        self.controller = TouchGestureController(self.surface, default_settings())
        self.triggered, self.started, self.updates, self.finished = [], [], [], []
        self.controller.triggered.connect(lambda key, point: self.triggered.append(key))
        self.controller.started.connect(self.started.append)
        self.controller.updated.connect(lambda key, delta: self.updates.append((key, delta)))
        self.controller.finished.connect(lambda key, cancelled: self.finished.append((key, cancelled)))
        self.surface.show()
        QApplication.processEvents()

    def tearDown(self):
        self.controller.cancel()
        for widget in reversed(self.widgets):
            widget.close()
            widget.deleteLater()
        QApplication.processEvents()

    def keep(self, widget):
        self.widgets.append(widget)
        return widget

    def touch(self):
        return QTest.touchEvent(self.surface, self.device)

    def tap(self, x=300, y=120):
        self.touch().press(0, QPoint(x, y), self.surface).commit()
        self.touch().release(0, QPoint(x, y), self.surface).commit()

    def cancel_touch(self):
        QApplication.sendEvent(self.surface, QTouchEvent(QEvent.Type.TouchCancel, self.device))

    def test_single_tap_is_delayed_and_double_tap_is_exclusive(self):
        self.tap()
        self.assertEqual(self.triggered, [])
        self.tap()
        QTest.qWait(350)
        self.assertEqual(self.triggered, ["double_tap_center"])
        self.tap(50)
        QTest.qWait(350)
        self.assertEqual(self.triggered[-1], "tap")

    def test_double_tap_uses_starting_region(self):
        for x, region in ((50, "left"), (300, "center"), (550, "right")):
            self.tap(x)
            self.tap(x)
            self.assertEqual(self.triggered[-1], "double_tap_" + region)

    def test_horizontal_drag_does_not_also_tap(self):
        self.touch().press(0, QPoint(200, 120), self.surface).commit()
        self.touch().move(0, QPoint(320, 120), self.surface).commit()
        self.touch().release(0, QPoint(320, 120), self.surface).commit()
        QTest.qWait(350)
        self.assertEqual(self.started, ["horizontal_drag"])
        self.assertEqual(self.finished, [("horizontal_drag", False)])
        self.assertEqual(self.triggered, [])
        self.assertAlmostEqual(self.updates[0][1]["x"], 0.2)

    def test_vertical_side_is_locked_at_press(self):
        self.touch().press(0, QPoint(100, 220), self.surface).commit()
        self.touch().move(0, QPoint(120, 100), self.surface).commit()
        self.touch().move(0, QPoint(400, 80), self.surface).commit()
        self.touch().release(0, QPoint(400, 80), self.surface).commit()
        self.assertEqual(self.started, ["vertical_drag_left"])

    def test_diagonal_movement_cannot_turn_into_a_tap(self):
        self.touch().press(0, QPoint(200, 120), self.surface).commit()
        self.touch().move(0, QPoint(250, 170), self.surface).commit()
        self.touch().release(0, QPoint(250, 170), self.surface).commit()
        QTest.qWait(350)
        self.assertEqual(self.triggered, [])

    def test_long_press_and_cancel_do_not_generate_a_tap(self):
        self.touch().press(0, QPoint(300, 120), self.surface).commit()
        QTest.qWait(650)
        self.assertEqual(self.triggered, ["long_press"])
        self.cancel_touch()
        QTest.qWait(350)
        self.assertEqual(self.triggered, ["long_press"])

    def test_movement_cancels_long_press(self):
        self.touch().press(0, QPoint(300, 120), self.surface).commit()
        self.touch().move(0, QPoint(340, 120), self.surface).commit()
        QTest.qWait(650)
        self.touch().release(0, QPoint(340, 120), self.surface).commit()
        self.assertNotIn("long_press", self.triggered)

    def test_pinch_finishes_when_fingers_lift_separately(self):
        self.touch().press(0, QPoint(200, 160), self.surface).press(1, QPoint(400, 160), self.surface).commit()
        self.touch().move(0, QPoint(150, 160), self.surface).move(1, QPoint(450, 160), self.surface).commit()
        self.touch().release(0, QPoint(150, 160), self.surface).stationary(1).commit()
        self.touch().release(1, QPoint(450, 160), self.surface).commit()
        self.assertEqual(self.started, ["pinch"])
        self.assertEqual(self.finished, [("pinch", False)])
        self.assertAlmostEqual(self.updates[-1][1]["scale"], 1.5)
        self.assertEqual(self.triggered, [])

    def test_two_finger_drag_and_three_finger_cancel(self):
        self.touch().press(0, QPoint(200, 160), self.surface).press(1, QPoint(400, 160), self.surface).commit()
        self.touch().move(0, QPoint(250, 160), self.surface).move(1, QPoint(450, 160), self.surface).commit()
        self.assertEqual(self.started, ["two_finger_drag"])
        self.touch().stationary(0).stationary(1).press(2, QPoint(300, 100), self.surface).commit()
        self.assertEqual(self.finished, [("two_finger_drag", True)])
        self.cancel_touch()

    def test_two_finger_tap_is_not_a_single_tap(self):
        self.touch().press(0, QPoint(200, 160), self.surface).press(1, QPoint(400, 160), self.surface).commit()
        self.touch().release(0, QPoint(200, 160), self.surface).release(1, QPoint(400, 160), self.surface).commit()
        QTest.qWait(350)
        self.assertEqual(self.triggered, [])

    def test_disable_cancels_pending_taps(self):
        self.tap()
        settings = default_settings()
        settings["enabled"] = False
        self.controller.set_settings(settings)
        self.tap()
        QTest.qWait(350)
        self.assertEqual(self.triggered, [])

    def test_touch_mouse_duplicates_are_suppressed_but_real_mouse_still_works(self):
        self.tap()
        point = QPoint(300, 120)
        event = QMouseEvent(QEvent.Type.MouseButtonPress, point, point, self.surface.mapToGlobal(point),
                            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier, Qt.MouseEventSource.MouseEventSynthesizedByQt)
        QApplication.sendEvent(self.surface, event)
        self.assertEqual(self.surface.mouse_presses, 0)
        QTest.mouseClick(self.surface, Qt.MouseButton.LeftButton, pos=point)
        self.assertEqual(self.surface.mouse_presses, 1)

    def test_cancelled_drag_does_not_finish_successfully(self):
        self.touch().press(0, QPoint(200, 120), self.surface).commit()
        self.touch().move(0, QPoint(320, 120), self.surface).commit()
        self.cancel_touch()
        self.assertEqual(self.finished, [("horizontal_drag", True)])

    def test_dialog_cancel_and_apply_have_distinct_persistence(self):
        store = MemoryStore()
        config = TouchConfig(store)
        dialog = self.keep(TouchGesturesDialog(config=config))
        dialog.tree.setCurrentItem(dialog.rows["double_tap_left"])
        dialog.action_combo.setCurrentIndex(dialog.action_combo.findData("bookmark"))
        dialog.option_fields["seek_forward_seconds"].setValue(30)
        self.assertEqual(config.snapshot()["bindings"]["double_tap_left"], "seek_backward")
        self.assertTrue(dialog.apply_changes())
        self.assertEqual(config.snapshot()["bindings"]["double_tap_left"], "bookmark")
        dialog.action_combo.setCurrentIndex(dialog.action_combo.findData("disabled"))
        dialog.reject()
        self.assertEqual(TouchConfig(store).snapshot()["bindings"]["double_tap_left"], "bookmark")

    def test_sqlite_settings_round_trip_and_invalid_values(self):
        config = TouchConfig(app_settings)
        settings = default_settings("audio")
        settings["sensitivity"] = 2.5
        self.assertTrue(config.save(settings))
        self.assertEqual(TouchConfig(app_settings).snapshot(), settings)
        normalized = normalize_settings({"sensitivity": float("nan"), "volume_limit": 900,
                                         "bindings": {"pinch": "seek_forward", "tap": "disabled"}})
        self.assertEqual(normalized["sensitivity"], 1)
        self.assertEqual(normalized["volume_limit"], 300)
        self.assertEqual(normalized["bindings"]["pinch"], "zoom")
        self.assertEqual(normalized["bindings"]["tap"], "disabled")

    def test_failed_save_keeps_active_settings_and_dialog_open(self):
        store = MemoryStore()
        config = TouchConfig(store)
        dialog = self.keep(TouchGesturesDialog(config=config))
        dialog.option_fields["seek_forward_seconds"].setValue(30)
        store.fail = True
        with patch("gui.dialogs.touch_gestures_dialog.QMessageBox.warning") as warning:
            dialog.accept()
        warning.assert_called_once()
        self.assertEqual(config.snapshot()["seek_forward_seconds"], 10)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

    def test_options_menu_places_touch_gestures_below_hotkeys(self):
        window = self.keep(QMainWindow())
        window.options_menu = QMenu(window)
        for name in ("open_preferences", "open_manage_database", "open_hotkeys", "open_touch_gestures",
                     "open_about_dialog", "check_for_updates", "open_utility_download_dialog", "open_documentation"):
            setattr(window, name, Mock())
        window.toolbar_manager = SimpleNamespace(open_toolbar_customize_dialog=Mock())
        MenuManager(window).setup_options_menu()
        actions = window.options_menu.actions()
        self.assertEqual(actions.index(window.touch_gestures_action), actions.index(window.hotkeys_action) + 1)
        window.touch_gestures_action.trigger()
        window.open_touch_gestures.assert_called_once()

    def player(self):
        with patch.object(PlayerWidget, "_init_player", lambda self: None):
            widget = self.keep(PlayerWidget())
        widget.player_controls.time_update_timer.stop()
        instance = create_autospec(AVMediaInstance, instance=True)
        instance.get_length.return_value = 600
        instance.get_position.return_value = 100
        instance.get_volume.return_value = 120
        instance.get_playback_state.return_value = AVPlaybackState.AV_STATE_PAUSED
        widget.player._primary_instance = instance
        widget.player.can_seek = Mock(return_value=True)
        widget.player.get_scale = Mock(return_value=1.0)
        widget.player.show_osd_text = Mock()
        widget.player.set_playback_speed = Mock()
        widget.player.set_scale = Mock()
        widget.player.set_video_pan = Mock()
        widget.player_controls._current_file = "test.mp4"
        widget.player_controls.is_video_available = True
        widget.player_controls.set_seek_range(0, 600)
        widget.player_controls.set_seek_position(100)
        widget._touch_actions.controller.set_settings(default_settings())
        return widget, instance, widget._touch_actions

    def test_player_seek_previews_then_commits_once_and_cancel_does_not_seek(self):
        widget, instance, touch = self.player()
        touch.start("horizontal_drag")
        touch.update("horizontal_drag", {"dx": 0.25, "y": 0.0})
        self.assertTrue(touch.is_seeking())
        instance.set_position.assert_not_called()
        self.assertEqual(widget.player_controls.get_seek_position(), 130)
        touch.finish("horizontal_drag", False)
        instance.set_position.assert_called_once_with(130)
        self.assertFalse(widget.is_seeking)
        instance.set_position.reset_mock()
        touch.start("horizontal_drag")
        touch.update("horizontal_drag", {"dx": 0.25, "y": 0.0})
        touch.finish("horizontal_drag", True)
        instance.set_position.assert_not_called()
        self.assertEqual(widget.player_controls.get_seek_position(), 100)

    def test_live_stream_cannot_seek_and_double_tap_uses_configured_skip(self):
        widget, instance, touch = self.player()
        widget.player.can_seek.return_value = False
        touch.start("horizontal_drag")
        touch.run_action("seek_forward")
        instance.set_position.assert_not_called()
        self.assertFalse(touch.is_seeking())
        widget.player.can_seek.return_value = True
        settings = default_settings("audio")
        touch.controller.set_settings(settings)
        touch.run_action("seek_forward")
        instance.set_position.assert_called_once_with(130)

    def test_hold_speed_restores_on_release_cancel_and_config_change(self):
        widget, instance, touch = self.player()
        settings = default_settings()
        settings["bindings"]["long_press"] = "temporary_speed"
        for cancelled in (False, True):
            touch.controller.set_settings(settings)
            widget.player_controls.speedChanged.emit(1.25)
            touch.start("long_press")
            self.assertEqual(widget.player_controls.current_speed, 2)
            touch.finish("long_press", cancelled)
            self.assertEqual(widget.player_controls.current_speed, 1.25)
        touch.controller.set_settings(settings)
        touch.controller._start("long_press")
        touch.controller.set_settings(default_settings())
        self.assertEqual(widget.player_controls.current_speed, 1.25)

    def test_volume_is_bounded_and_saved_only_on_release(self):
        widget, instance, touch = self.player()
        with patch("app_config.prefs.save") as save:
            touch.start("vertical_drag_right")
            touch.update("vertical_drag_right", {"y": -0.8})
            instance.set_volume.assert_called_with(150)
            save.assert_not_called()
            touch.finish("vertical_drag_right", False)
            save.assert_called_once()

    def test_pinch_pan_and_cancel_use_player_controls(self):
        widget, instance, touch = self.player()
        touch.start("pinch")
        touch.update("pinch", {"scale": 1.5})
        widget.player.set_scale.assert_called_with(1.5)
        touch.finish("pinch", True)
        widget.player.set_scale.assert_called_with(1.0)
        touch.start("two_finger_drag")
        touch.update("two_finger_drag", {"x": 0.2, "y": -0.1})
        widget.player.set_video_pan.assert_called_with(0.2, -0.1)
        touch.finish("two_finger_drag", True)
        widget.player.set_video_pan.assert_called_with(0.0, 0.0)

    def test_fullscreen_controls_and_gestures_survive_reparenting(self):
        widget, instance, touch = self.player()
        widget.resize(800, 600)
        widget.show()
        QApplication.processEvents()
        surface = widget.video_display
        touch.run_action("toggle_controls")
        self.assertTrue(widget.player_controls.is_minimized)
        touch.run_action("toggle_controls")
        self.assertFalse(widget.player_controls.is_minimized)
        with patch.object(widget.player, "set_fullscreen"):
            touch.run_action("fullscreen")
            QApplication.processEvents()
            touch.run_action("toggle_controls")
            self.assertTrue(surface.touch_controls.isVisible())
            self.assertTrue(widget.player_controls.is_fullscreen)
            touch.run_action("fullscreen")
            QApplication.processEvents()
            self.assertFalse(surface.touch_controls.isVisible())
            self.assertFalse(widget.player_controls.is_fullscreen)
        self.assertTrue(surface.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents))

    def test_dialog_layout_and_draft_practice(self):
        dialog = self.keep(TouchGesturesDialog(config=TouchConfig(MemoryStore())))
        dialog.resize(480, 420)
        dialog.show()
        QApplication.processEvents()
        self.assertGreater(dialog.tree.height(), 80)
        dialog.search_edit.setText("pinch")
        self.assertFalse(dialog.rows["pinch"].isHidden())
        self.assertTrue(dialog.rows["tap"].isHidden())
        dialog.search_edit.clear()
        dialog.tree.setCurrentItem(dialog.rows["tap"])
        dialog.action_combo.setCurrentIndex(dialog.action_combo.findData("bookmark"))
        dialog._practice_result("tap")
        self.assertIn("bookmark", dialog.practice_result.text().lower())
        preview = os.environ.get("PLAYFORM_TOUCH_PREVIEW")
        if preview:
            apply_theme("dark", self.app)
            dialog.resize(720, 580)
            QApplication.processEvents()
            dialog.grab().save(preview)


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        user_db.close_connection()
        media_db.close_connection()
        _test_data.cleanup()
