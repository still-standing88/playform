"""Reproduction for the "spam file open using Explorer" crash report.

Mirrors EXPLORER.explorer_view.ExplorerView._delayed_media_load() exactly:
one AVMediaInstance, reused across selections, hammered with
load_file(path) -> stop() back-to-back with zero pacing (no sleep at all --
onItemChange has no debounce, it calls straight through). Real window, real
GPU vo (not vo=null), single thread -- this isn't about concurrency, it's
about flooding libmpv's core with rapid load/stop churn.

Usage:
    vnv\\Scripts\\python.exe scripts\\stress_test_mpv_explorer_spam.py --iterations 500
"""
import argparse
import os
import random
import sys
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"F:\videoes")
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--dump-dir", default=os.path.join(SCRIPT_DIR, "mpv_stress", "crashes"))
    args = parser.parse_args()

    install_crash_handler(args.dump_dir)

    files = collect_videos(args.root)
    if not files:
        print(f"no video files found under {args.root}")
        sys.exit(2)

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("stress-explorer-spam")
    win.resize(480, 320)
    win.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
    win.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
    win.show()

    player = av_play.VideoPlayer()
    player.init(config={})
    player.set_window(win.winId())

    instance = None
    ops = 0
    errors = 0
    exceptions = []

    def step():
        nonlocal instance, ops, errors
        for _ in range(5):  # a few loads per timer tick, driven by the real Qt event loop
            path = random.choice(files)
            try:
                if instance is None:
                    instance = player.create_file_instance(path)
                else:
                    instance.load_file(path)
                instance.stop()
                ops += 1
            except Exception as e:
                errors += 1
                if len(exceptions) < 10:
                    exceptions.append(f"{type(e).__name__}: {e}")

        if ops >= args.iterations:
            timer.stop()
            print(f"RESULT: ops={ops} errors={errors} exceptions={exceptions}")
            try:
                player.release()
            except Exception as e:
                print(f"release error: {type(e).__name__}: {e}")
            app.quit()

    timer = QTimer()
    timer.timeout.connect(step)
    timer.start(0)  # fire as fast as the event loop allows, exactly like rapid arrow-key/click spam

    app.exec()


if __name__ == "__main__":
    main()
