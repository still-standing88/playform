"""Stress-test harness for the rewritten MPV backend in src/av_play.

Runs one phase per invocation, always as its own child process (see
run_stress_tests.py) so a genuine native crash doesn't take the supervisor
down with it. Installs mpv_crash_handler so a real access violation leaves a
text summary (exception code, access type, faulting address/module) behind.

Usage:
    python stress_test_mpv.py --phase load_spam --root "F:\\music\\music collection" --iterations 200
"""
import argparse
import json
import os
import random
import sys
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "src")
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, SCRIPT_DIR)

import mpv_crash_handler  # noqa: E402

AUDIO_EXTS = (".mp3", ".flac", ".m4a", ".wav", ".ogg", ".wma", ".aac")
VIDEO_EXTS = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv")


def collect_files(root: str, exts: tuple) -> list:
    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(exts):
                files.append(os.path.join(dirpath, name))
    return files


def make_player(video: bool):
    import utilities.mpv_bootstrap  # noqa: F401
    import av_play
    player = av_play.VideoPlayer()
    config = {"vo": "null"} if video else {}
    player.init(config=config)
    return player, av_play


class Result:
    def __init__(self):
        self.ops = 0
        self.errors = 0
        self.exceptions = []
        self.started_at = time.time()

    def finish(self):
        return {
            "ops": self.ops,
            "errors": self.errors,
            "exceptions": self.exceptions[:20],
            "duration_s": round(time.time() - self.started_at, 2),
        }


def phase_load_spam(files: list, iterations: int, video: bool) -> dict:
    """Rapidly create -> play -> stop -> release across many different files
    back-to-back, no pacing. Simulates double-click/track-switch spam."""
    result = Result()
    player, av_play = make_player(video)
    try:
        for i in range(iterations):
            path = files[i % len(files)]
            try:
                inst = player.create_file_instance(path)
                inst.play()
                inst.stop()
                inst.release()
                result.ops += 1
            except Exception as e:
                result.errors += 1
                result.exceptions.append(f"{type(e).__name__}: {e}")
    finally:
        player.release()
    return result.finish()


def phase_seek_spam(files: list, iterations: int, video: bool) -> dict:
    """Load one file, then hammer set_position with rapid random offsets and
    no waiting -- simulates dragging the seek slider fast."""
    result = Result()
    player, av_play = make_player(video)
    try:
        inst = player.create_file_instance(files[0])
        inst.play()
        time.sleep(0.5)
        length = inst.get_length() or 60
        for _ in range(iterations):
            try:
                inst.set_position(random.randint(0, max(1, length - 1)))
                result.ops += 1
            except Exception as e:
                result.errors += 1
                result.exceptions.append(f"{type(e).__name__}: {e}")
        inst.stop()
    finally:
        player.release()
    return result.finish()


def phase_toggle_spam(files: list, iterations: int, video: bool) -> dict:
    """Rapid play/pause/mute/unmute/volume toggling with no pacing."""
    result = Result()
    player, av_play = make_player(video)
    try:
        inst = player.create_file_instance(files[0])
        inst.play()
        time.sleep(0.3)
        for i in range(iterations):
            try:
                op = i % 6
                if op == 0:
                    inst.pause()
                elif op == 1:
                    inst.play()
                elif op == 2:
                    inst.mute()
                elif op == 3:
                    inst.unmute()
                elif op == 4:
                    inst.set_volume(random.uniform(0, 100))
                else:
                    inst.get_playback_state()
                result.ops += 1
            except Exception as e:
                result.errors += 1
                result.exceptions.append(f"{type(e).__name__}: {e}")
        inst.stop()
    finally:
        player.release()
    return result.finish()


def phase_concurrent(files: list, iterations: int, video: bool) -> dict:
    """Multiple threads hammering the same player instance concurrently with
    different operation types -- simulates the GUI thread + AVPlayer monitor
    thread racing against each other that the old adapter couldn't survive."""
    result = Result()
    lock = threading.Lock()
    player, av_play = make_player(video)
    stop_event = threading.Event()

    try:
        inst = player.create_file_instance(files[0])
        inst.play()
        time.sleep(0.3)

        def record_ok():
            with lock:
                result.ops += 1

        def record_err(e):
            with lock:
                result.errors += 1
                if len(result.exceptions) < 20:
                    result.exceptions.append(f"{type(e).__name__}: {e}")

        def loader_thread():
            i = 0
            while not stop_event.is_set():
                path = files[i % len(files)]
                i += 1
                try:
                    inst.load_file(path)
                    inst.play()
                    record_ok()
                except Exception as e:
                    record_err(e)

        def seeker_thread():
            while not stop_event.is_set():
                try:
                    inst.set_position(random.randint(0, 60))
                    record_ok()
                except Exception as e:
                    record_err(e)

        def state_thread():
            while not stop_event.is_set():
                try:
                    inst.get_playback_state()
                    inst.get_position()
                    inst.get_length()
                    record_ok()
                except Exception as e:
                    record_err(e)

        def toggle_thread():
            while not stop_event.is_set():
                try:
                    inst.pause()
                    inst.play()
                    inst.set_volume(random.uniform(0, 100))
                    record_ok()
                except Exception as e:
                    record_err(e)

        threads = [
            threading.Thread(target=loader_thread, daemon=True),
            threading.Thread(target=seeker_thread, daemon=True),
            threading.Thread(target=state_thread, daemon=True),
            threading.Thread(target=toggle_thread, daemon=True),
        ]
        for t in threads:
            t.start()

        deadline = time.time() + iterations / 50.0  # iterations used as a duration knob here
        while time.time() < deadline:
            time.sleep(0.1)
        stop_event.set()
        for t in threads:
            t.join(timeout=3.0)

        inst.stop()
    finally:
        player.release()
    return result.finish()


def phase_playlist_cycle(files: list, iterations: int, video: bool) -> dict:
    """Repeated init -> load_playlist -> next/previous -> stop_playlist ->
    release cycles -- the exact teardown-during-monitor-activity race the old
    adapter was most likely to crash on."""
    result = Result()
    import utilities.mpv_bootstrap  # noqa: F401
    import av_play

    playlist_files = files[: min(10, len(files))]
    for cycle in range(iterations):
        player = av_play.VideoPlayer()
        try:
            player.init(config={"vo": "null"} if video else {})
            playlist = av_play.Playlist(title="stress")
            for f in playlist_files:
                playlist.add_entry(av_play.PlaylistEntry(location=f))
            player.load_playlist(playlist, auto_play=True, start_index=0)
            time.sleep(0.05)
            player.next()
            time.sleep(0.02)
            player.previous()
            time.sleep(0.02)
            player.stop_playlist()
            result.ops += 1
        except Exception as e:
            result.errors += 1
            result.exceptions.append(f"{type(e).__name__}: {e}")
        finally:
            try:
                player.release()
            except Exception as e:
                result.errors += 1
                result.exceptions.append(f"release: {type(e).__name__}: {e}")
    return result.finish()


PHASES = {
    "load_spam": phase_load_spam,
    "seek_spam": phase_seek_spam,
    "toggle_spam": phase_toggle_spam,
    "concurrent": phase_concurrent,
    "playlist_cycle": phase_playlist_cycle,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=list(PHASES.keys()))
    parser.add_argument("--root", required=True)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--video", action="store_true")
    parser.add_argument("--dump-dir", default=os.path.join(SCRIPT_DIR, "mpv_stress", "crashes"))
    args = parser.parse_args()

    mpv_crash_handler.install_crash_handler(args.dump_dir)

    exts = VIDEO_EXTS if args.video else AUDIO_EXTS
    files = collect_files(args.root, exts)
    if not files:
        print(json.dumps({"error": f"no files found under {args.root}"}))
        sys.exit(2)
    random.shuffle(files)

    result = PHASES[args.phase](files, args.iterations, args.video)
    result["phase"] = args.phase
    result["kind"] = "video" if args.video else "audio"
    result["file_count"] = len(files)
    print("RESULT_JSON:" + json.dumps(result))


if __name__ == "__main__":
    main()
