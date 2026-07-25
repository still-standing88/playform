import av_play

from app_config import prefs
from utilities.functions import get_debug_level, get_mpvlog_file, parse_mpv_options


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
        widget.player.set_window(widget.video_display.winId())
        widget.player.set_auto_play(prefs.prefs["autoplay"])
        widget.player.set_track_end_callback(lambda index: widget._trackEndedFromMonitor.emit(index))
        widget.filters_widget.set_player(widget.player)
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
