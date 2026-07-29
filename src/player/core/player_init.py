import os
import threading
import time

import av_play

from app_config import prefs
from utilities.functions import get_debug_level, get_logs_dir, get_mpvlog_file, parse_mpv_options


_TRACE_REASON_NAMES = {0: "EOF", 1: "RESTARTED", 2: "ABORTED/STOP", 3: "QUIT", 4: "ERROR", 5: "REDIRECT"}
_trace_start = time.monotonic()
_trace_lock = threading.Lock()


def _trace(msg):
    # TEMPORARY diagnostic instrumentation for the playlist auto-advance
    # skip investigation -- pure logging, no behavior change. Safe to
    # delete once that investigation is closed.
    line = f"[{time.monotonic() - _trace_start:9.3f}s] {msg} (thread={threading.current_thread().name})\n"
    try:
        with _trace_lock:
            with open(os.path.join(get_logs_dir(), "playback-trace.log"), "a", encoding="utf-8") as f:
                f.write(line)
    except OSError:
        pass


def _install_playback_trace(widget):
    # set_end_file_callback/set_start_file_callback register additional,
    # independent listeners (python-mpv appends rather than replaces) --
    # this doesn't disturb the app's own existing file-loaded listener
    # (resume-last-position) registered further down in init_mpv_player.
    def on_end_file(event):
        reason = event.data.reason
        _trace(f"RAW end-file reason={reason} ({_TRACE_REASON_NAMES.get(reason, '?')})  "
               f"index={widget.player.get_current_track_index()}")

    def on_file_loaded(event):
        _trace(f"RAW file-loaded  index={widget.player.get_current_track_index()}")

    try:
        widget.player.set_end_file_callback(on_end_file)
        widget.player.set_start_file_callback(on_file_loaded)
    except av_play.AVError:
        pass


def init_mpv_player(widget):
    """Initialize widget.player (a LazyPlaylistPlayer) with MPV config, the
    configured audio output device, and persisted repeat/shuffle prefs.
    Extracted out of PlayerWidget._init_player; widget is the owning
    PlayerWidget instance."""
    config: dict = {}
    # mpv's own volume ceiling defaults far lower than the UI's; without
    # raising it here, set_volume() calls above mpv's default volume-max
    # get silently clamped back down regardless of what the slider shows.
    config["volume"] = prefs.prefs.get("player_volume", 120)
    config["volume_max"] = 300

    if prefs.prefs.get("mpv_logging", True):
        level_map = {0: "error", 1: "info", 2: "debug"}
        config["log_file"] = get_mpvlog_file()
        config["msg_level"] = f"all={level_map.get(get_debug_level(), 'info')}"

    extra_options = prefs.prefs.get("mpv_extra_options", "")
    if extra_options:
        try:
            config.update(parse_mpv_options(extra_options))
        except Exception:
            pass

    try:
        widget.player.init(config=config)
        _install_playback_trace(widget)
        widget.player.set_window(widget.video_display.winId())
        widget.player.set_auto_play(prefs.prefs["autoplay"])

        def _on_track_ended_from_monitor(index):
            _trace(f"APP monitor advanced -> index={index}  "
                   f"repeat={widget.player.get_playlist_repeat_mode()}  "
                   f"shuffle={widget.player.get_playlist_shuffle_mode()}")
            widget._trackEndedFromMonitor.emit(index)

        widget.player.set_track_end_callback(_on_track_ended_from_monitor)

        def _on_reverse_stopped_from_monitor():
            _trace("APP reverse-stopped")
            widget._reverseStoppedFromMonitor.emit()

        widget.player.set_reverse_stopped_callback(_on_reverse_stopped_from_monitor)
        # loadfile is fire-and-forget (see mpv_video_player.py's set_position
        # comment) -- seeking to a saved position right after issuing it, with
        # no delay, races mpv actually opening the file and can get silently
        # dropped. file-loaded is mpv's own signal that the file is truly
        # ready to seek in, so resume-last-position is driven off that event
        # instead of off load_file()'s call site.
        widget.player.set_start_file_callback(lambda event: widget._fileLoadedFromMpv.emit())
        widget.filters_widget.set_player(widget.player)
        widget.video_effects_widget.set_player(widget.player)
        widget.equalizer_widget.set_player(widget.player)
        widget.audio_filters_widget.set_player(widget.player)

        device_name = prefs.prefs.get("device_name", "")
        if device_name:
            device_count = widget.player.get_devices()
            for i in range(device_count):
                device_info = widget.player.get_device(i)
                if device_info and device_info.name == device_name:
                    widget.player.set_device(i)
                    break
        else:
            device = prefs.prefs.get("device", 0)
            if device < widget.player.get_devices():
                widget.player.set_device(device)

        rm = prefs.prefs.get("repeat_mode", 0)
        if rm == 2:
            widget.player.set_playlist_repeat_mode(av_play.AVPlaylistRepeatMode.REPEAT_ONE)
            widget.player_controls.set_repeat_mode("one")
        elif rm == 1:
            widget.player.set_playlist_repeat_mode(av_play.AVPlaylistRepeatMode.REPEAT_ALL)
            widget.player_controls.set_repeat_mode("all")
        else:
            widget.player.set_playlist_repeat_mode(av_play.AVPlaylistRepeatMode.REPEAT_OFF)
            widget.player_controls.set_repeat_mode("off")

        sh = bool(prefs.prefs.get("shuffle", False))
        if sh:
            widget.player.set_playlist_shuffle_mode(av_play.AVPlaylistShuffleMode.SHUFFLE)
            widget.player_controls.set_shuffle_state(True)
        else:
            widget.player.set_playlist_shuffle_mode(av_play.AVPlaylistShuffleMode.SEQUENTIAL)
            widget.player_controls.set_shuffle_state(False)

    except av_play.AVError as e:
        widget.player_controls.set_controls_enabled(False)
