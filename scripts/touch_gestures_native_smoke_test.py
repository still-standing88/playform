"""Check actual embedded mpv windows with a hidden Windows Qt surface.

Run: set QT_QPA_PLATFORM=windows, then use the project's Python.
This creates its own test video and uses isolated settings.
"""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import unittest

import touch_gestures_test as base
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from gui_controls.native_video_input import NativeVideoInput
from gui_controls.touch_gesture_controller import TouchGestureController
from app_constance.touch_gestures import default_settings
from media_core.av_play import VideoPlayer
from player.widgets.video_display_widget import VideoDisplayWidget


@unittest.skipUnless(sys.platform == "win32" and os.environ.get("QT_QPA_PLATFORM") == "windows", "Requires the Windows Qt platform")
class NativeTouchSmokeTest(unittest.TestCase):
    def test_embedded_window_passthrough_rendering_and_qt_touch_delivery(self):
        base.TouchTests.setUpClass()
        app = QApplication.instance()
        video = Path(base._test_data.name) / "touch-test.mp4"
        ffmpeg = Path(__file__).resolve().parents[1] / "bin" / "ffmpeg.exe"
        subprocess.run([str(ffmpeg), "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=10",
                        "-t", "30", "-an", "-c:v", "mpeg4", str(video)],
                       check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        container.resize(640, 360)
        layout = QVBoxLayout(container)
        surface = VideoDisplayWidget(container)
        surface.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        layout.addWidget(surface)
        surface.set_position_info(layout, 0)
        container.show()
        app.processEvents()
        backend = VideoPlayer()
        adapter = NativeVideoInput(surface)
        try:
            backend.init(config={"vo": "gpu", "ao": "null", "hwdec": "no"}, window=int(surface.winId()))
            instance = backend.create_file_instance(str(video))
            instance.play()
            for attempt in range(100):
                QTest.qWait(50)
                if backend.primary_instance.get_length() > 0 and backend.can_seek():
                    break
            self.assertGreater(backend.primary_instance.get_length(), 0)
            backend.primary_instance.pause()
            adapter._refresh()
            self.assertTrue(adapter._windows, "No mpv child window was found")
            api = adapter._api()
            for handle in adapter._windows:
                self.assertEqual(api.GetWindowLongPtrW(handle, -20) & (0x80000 | 0x20), 0x80000 | 0x20)
            self.assertTrue(backend.can_seek())
            backend.show_osd_text("Touch test", 1000)
            image = Path(base._test_data.name) / "touch-frame.png"
            self.assertTrue(backend.take_screenshot(str(image)))
            self.assertGreater(image.stat().st_size, 1000)

            controller = TouchGestureController(surface, default_settings())
            gestures = []
            controller.triggered.connect(lambda key, point: gestures.append(key))
            device = QTest.createTouchDevice()
            for tap in range(2):
                QTest.touchEvent(surface, device).press(0, QPoint(320, 100), surface).commit()
                QTest.touchEvent(surface, device).release(0, QPoint(320, 100), surface).commit()
            self.assertEqual(gestures, ["double_tap_center"])
            for fullscreen in (True, False):
                old_window = int(surface.winId())
                surface.set_fullscreen(fullscreen)
                if int(surface.winId()) != old_window:
                    backend.set_window(int(surface.winId()))
                backend.set_fullscreen(fullscreen)
                adapter.refresh()
                QTest.qWait(300)
                adapter._refresh()
                self.assertTrue(any(parent == int(surface.winId()) for parent, added in adapter._windows.values()))
                self.assertTrue(backend.take_screenshot(str(image)))
            windows = list(adapter._windows)
            adapter.set_enabled(False)
            for handle in windows:
                self.assertEqual(api.GetWindowLongPtrW(handle, -20) & (0x80000 | 0x20), 0)
        finally:
            adapter.set_enabled(False)
            backend.release()
            surface.close()
            container.close()


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        base.user_db.close_connection()
        base.media_db.close_connection()
        base._test_data.cleanup()
