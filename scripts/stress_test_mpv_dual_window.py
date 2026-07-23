"""Reproduction harness for the real-GUI crash report: a video loaded in
Explorer's preview player while the main Player is also running, crashing on
seek. Unlike stress_test_mpv.py (headless, vo=null, single instance), this
creates two REAL native windows and two independent MPVVideoPlayer instances
embedded into them with real GPU rendering, then hammers loads/seeks on both
concurrently while pumping a real Qt event loop.

Usage:
    vnv\\Scripts\\python.exe scripts\\stress_test_mpv_dual_window.py --seconds 30
"""
import argparse
import os
import random
import sys
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "src")
sys.path.insert(0, SRC_DIR)

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QTimer

import utilities.mpv_bootstrap  # noqa: F401
from utilities.crash_handler import install_crash_handler
import av_play

VIDEO_EXTS = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv")


def collect_videos(root: str) -> list:
    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(VIDEO_EXTS):
                files.append(os.path.join(dirpath, name))
    return files


def make_window(title: str) -> QWidget:
    w = QWidget()
    w.setWindowTitle(title)
    w.resize(480, 320)
    w.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
    w.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
    w.show()
    return w


class PlayerWorker:
    """Owns one MPVVideoPlayer embedded in one real window, hammered by its
    own thread -- mirrors "Explorer preview" vs "main Player" both alive."""

    def __init__(self, name: str, window: QWidget, files: list):
        self.name = name
        self.files = files
        self.player = av_play.VideoPlayer()
        self.player.init(config={})
        self.player.set_window(window.winId())
        self.stop_event = threading.Event()
        self.ops = 0
        self.errors = 0
        self.exceptions = []
        self.thread = threading.Thread(target=self._run, daemon=True, name=f"stress-{name}")

    def _run(self):
        inst = None
        try:
            inst = self.player.create_file_instance(random.choice(self.files))
            inst.play()
            time.sleep(0.6)
            while not self.stop_event.is_set():
                try:
                    action = random.choice(["seek", "seek", "seek", "load", "toggle"])
                    if action == "seek":
                        length = inst.get_length() or 30
                        inst.set_position(random.randint(0, max(1, length - 1)))
                    elif action == "load":
                        inst.load_file(random.choice(self.files))
                        inst.play()
                    else:
                        inst.pause()
                        inst.play()
                    self.ops += 1
                except Exception as e:
                    self.errors += 1
                    if len(self.exceptions) < 10:
                        self.exceptions.append(f"{type(e).__name__}: {e}")
                time.sleep(0.01)
        finally:
            try:
                self.player.release()
            except Exception as e:
                self.errors += 1
                self.exceptions.append(f"release: {type(e).__name__}: {e}")

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"F:\videoes")
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--dump-dir", default=os.path.join(SCRIPT_DIR, "mpv_stress", "crashes"))
    args = parser.parse_args()

    install_crash_handler(args.dump_dir)

    files = collect_videos(args.root)
    if not files:
        print(f"no video files found under {args.root}")
        sys.exit(2)

    app = QApplication(sys.argv)

    win_a = make_window("stress-explorer-preview")
    win_b = make_window("stress-main-player")

    worker_a = PlayerWorker("explorer", win_a, files)
    worker_b = PlayerWorker("player", win_b, files)

    worker_a.start()
    worker_b.start()

    def finish():
        worker_a.stop()
        worker_b.stop()
        total_ops = worker_a.ops + worker_b.ops
        total_errors = worker_a.errors + worker_b.errors
        print(f"RESULT: explorer ops={worker_a.ops} errors={worker_a.errors} exceptions={worker_a.exceptions}")
        print(f"RESULT: player   ops={worker_b.ops} errors={worker_b.errors} exceptions={worker_b.exceptions}")
        print(f"RESULT: total ops={total_ops} total_errors={total_errors}")
        app.quit()

    QTimer.singleShot(args.seconds * 1000, finish)
    app.exec()


if __name__ == "__main__":
    main()
