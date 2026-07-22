import sys

import av_play

from app_config import prefs
from app_constance.vlc_args import log_args
from utilities.functions import get_debug_level, get_vlclog_file, parse_vlc_args


def init_vlc_player(widget):
    """Initialize widget.player (a LazyPlaylistPlayer) with VLC args, the
    configured audio output device, and persisted repeat/shuffle prefs.
    Extracted out of PlayerWidget._init_player; widget is the owning
    PlayerWidget instance."""
    vlc_args = list(log_args)
    if prefs.prefs.get("vlc_logging", True):
        vlc_args.extend([
            "--file-logging",
            "--logmode", "text",
            "--logfile", get_vlclog_file(),
            "--verbose", str(int(get_debug_level()))
        ])

    try:
        device_name = prefs.prefs.get("device_name", "")
        device_id = None
        if device_name and sys.platform.startswith("win"):
            try:
                import vlc as _vlc
                tmp = _vlc.Instance(["--intf", "dummy"])
                head = tmp.audio_output_device_list_get("mmdevice")
                if head:
                    cur = head
                    while cur:
                        cur = cur.contents
                        if cur.description.decode('utf-8', errors='ignore') == device_name:
                            device_id = cur.device.decode('utf-8', errors='ignore')
                            break
                        cur = cur.next
                    _vlc.libvlc_audio_output_device_list_release(head)
                tmp.release()
            except Exception:
                pass

        try:
            extra_args = parse_vlc_args(prefs.prefs.get("vlc_args", ""))
            widget.player.init(vlc_args=vlc_args+extra_args, device_id=device_id)
        except:
            widget.player.init(vlc_args=vlc_args, device_id=device_id)
        widget.player.set_window(widget.video_display.winId())
        widget.player.set_auto_play(prefs.prefs["autoplay"])
        widget.player.set_track_end_callback(widget._update_current_track)
        widget.filters_widget.set_player(widget.player)
        widget.equalizer_widget.set_player(widget.player)
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
