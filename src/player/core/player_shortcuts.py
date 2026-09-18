from typing import Callable, Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut

from app_config import key_config
from app_constance.misc import video_rotations


class PlayerShortcuts:
    """Hotkey wiring and widget-guarded dispatch for PlayerWidget, extracted
    out of PlayerWidget.set_shortcuts/_install_event_filters. widget is the
    owning PlayerWidget instance."""

    def __init__(self, widget):
        self._widget = widget

    def _has_active_media_instance(self) -> bool:
        widget = self._widget
        try:
            return bool(getattr(widget, 'player', None) and widget.player.primary_instance is not None)
        except Exception:
            return False

    def _call_if_enabled(self, control, callback: Callable[[], None]):
        try:
            if control is not None and not control.isEnabled():
                return
        except Exception:
            return
        try:
            callback()
        except Exception:
            pass

    def _call_if_media(self, callback: Callable[[], None]):
        if not self._has_active_media_instance():
            return
        try:
            callback()
        except Exception:
            pass

    def _call_if_video(self, callback: Callable[[], None]):
        if not self._widget.player_controls.is_video_available:
            return
        try:
            callback()
        except Exception:
            pass

    def _call_if_reverse_available(self, callback: Callable[[], None]):
        if not self._widget.player_controls.is_reverse_available:
            return
        try:
            callback()
        except Exception:
            pass

    def setup(self):
        widget = self._widget

        shortcuts: Dict[str, Callable] = {
            "Play/Pause": lambda: self._call_if_enabled(widget.player_controls.play_pause_btn, widget.player_controls.playPauseClicked.emit),
            "Backward": lambda: self._call_if_enabled(widget.player_controls.backward_btn, widget.player_controls.backwardClicked.emit),
            "Forward": lambda: self._call_if_enabled(widget.player_controls.forward_btn, widget.player_controls.forwardClicked.emit),
            "Stop": lambda: self._call_if_media(widget.player_controls.stopRequested.emit),
            "Mute/Unmute": lambda: self._call_if_enabled(widget.player_controls.mute_btn, widget.player_controls.muteUnmuteClicked.emit),
            "Previous": lambda: self._call_if_enabled(widget.player_controls.previous_btn, widget.player_controls.previousClicked.emit),
            "Next": lambda: self._call_if_enabled(widget.player_controls.next_btn, widget.player_controls.nextClicked.emit),
            "Jump to beginning": lambda: self._call_if_enabled(widget.player_controls.seek_slider, widget.player_controls.jumpToBeginningRequested.emit),
            "Jump to the end": lambda: self._call_if_enabled(widget.player_controls.seek_slider, widget.player_controls.jumpToEndRequested.emit),
            "Jump to 10%": lambda: self._call_if_media(lambda: widget._seek_to_percent(10)),
            "Jump to 30%": lambda: self._call_if_media(lambda: widget._seek_to_percent(30)),
            "Jump to 50%": lambda: self._call_if_media(lambda: widget._seek_to_percent(50)),
            "Jump to 70%": lambda: self._call_if_media(lambda: widget._seek_to_percent(70)),
            "Jump to 90%": lambda: self._call_if_media(lambda: widget._seek_to_percent(90)),
            "Show playlist dialog": lambda: self._call_if_media(widget.show_playlist_dialog),
            "Show queue dialog": lambda: self._call_if_media(widget.show_queue_dialog),
            "Toggle repeat": lambda: self._call_if_enabled(widget.player_controls.repeat_btn, widget.player_controls.repeatClicked.emit),
            "Volume up": lambda: self._call_if_enabled(widget.player_controls.volume_slider, widget.player_controls.volume_up),
            "Volume down": lambda: self._call_if_enabled(widget.player_controls.volume_slider, widget.player_controls.volume_down),
            "Bookmarks list": lambda: widget.player_controls.show_bookmarks_dialog(),
            "Go to time": lambda: widget.player_controls.show_goto_dialog(),
            "New mark at current position": lambda: widget.player_controls.add_bookmark_at_current_position(),
            "Repeat loop start": lambda: self._on_repeat_start_shortcut(),
            "Repeat loop end": lambda: self._on_repeat_end_shortcut(),
            "Clear repeat loop": lambda: widget.player_controls.clear_repeat_loop(),
            "Take snapshot": lambda: self._call_if_media(widget.player_controls.screenshotRequested.emit),
            "Delete current bookmark": lambda: widget.player_controls.delete_current_bookmark(),
            "Fullscreen": lambda: widget.player_controls.fullscreenToggled.emit(True),
            "Exit fullscreen": lambda: widget.player_controls.fullscreenToggled.emit(False),
            "Previous bookmark": lambda: widget.player_controls.jump_to_previous_bookmark(),
            "Next bookmark": lambda: widget.player_controls.jump_to_next_bookmark(),
            "Previous repeat loop": lambda: widget.player_controls.jump_to_previous_loop(),
            "Next repeat loop": lambda: widget.player_controls.jump_to_next_loop(),
            "Mark1 position": lambda: widget.player_controls.jump_to_mark(0),
            "Mark2 position": lambda: widget.player_controls.jump_to_mark(1),
            "Mark3 position": lambda: widget.player_controls.jump_to_mark(2),
            "Mark4 position": lambda: widget.player_controls.jump_to_mark(3),
            "Mark5 position": lambda: widget.player_controls.jump_to_mark(4),
            "Mark6 position": lambda: widget.player_controls.jump_to_mark(5),
            "Mark7 position": lambda: widget.player_controls.jump_to_mark(6),
            "Mark8 position": lambda: widget.player_controls.jump_to_mark(7),
            "Mark9 position": lambda: widget.player_controls.jump_to_mark(8),
            "Mark10 position": lambda: widget.player_controls.jump_to_mark(9),
            "Pan up": lambda: self._call_if_video(lambda: widget.player_controls.pan_by(0.0, -widget.player_controls.PAN_STEP)),
            "Pan down": lambda: self._call_if_video(lambda: widget.player_controls.pan_by(0.0, widget.player_controls.PAN_STEP)),
            "Pan left": lambda: self._call_if_video(lambda: widget.player_controls.pan_by(-widget.player_controls.PAN_STEP, 0.0)),
            "Pan right": lambda: self._call_if_video(lambda: widget.player_controls.pan_by(widget.player_controls.PAN_STEP, 0.0)),
            "Rotate video": lambda: self._call_if_video(self._on_rotate_shortcut),
            "Flip horizontal": lambda: self._call_if_video(lambda: widget.player_controls._on_flip_horizontal_action_toggled(not widget.player_controls.is_flip_horizontal)),
            "Flip vertical": lambda: self._call_if_video(lambda: widget.player_controls._on_flip_vertical_action_toggled(not widget.player_controls.is_flip_vertical)),
            "Speed up": lambda: widget.player_controls.step_speed(1),
            "Speed down": lambda: widget.player_controls.step_speed(-1),
            "Reverse playback": lambda: self._call_if_reverse_available(lambda: widget.player_controls._on_reverse_action_toggled(not widget.player_controls.is_reverse_active)),
            "Previous subtitle line": lambda: self._call_if_media(lambda: widget.subtitles_widget.seekRequested.emit(-1)),
            "Next subtitle line": lambda: self._call_if_media(lambda: widget.subtitles_widget.seekRequested.emit(1)),
        }

        for shortcut in widget._shortcuts.values():
            shortcut.activated.disconnect()
            shortcut.setParent(None)
        widget._shortcuts.clear()

        for action, callback in shortcuts.items():
            sequence = key_config.get_active_hotkey_sequence("Player", action)
            if not sequence:
                continue
            sh = QShortcut(sequence, widget)
            sh.activated.connect(callback)
            sh.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            # QShortcut defaults to autoRepeat=True -- holding a key even
            # slightly past the OS repeat-delay threshold (or the event loop
            # hiccuping under load, e.g. during audio device negotiation)
            # re-fires activated repeatedly. Confirmed via mpv's own log: a
            # single "Jump to the end" press produced repeated
            # time-pos=<duration> seeks across multiple, unrelated
            # already-loaded tracks seconds apart, each one immediately
            # re-triggering EOF and advancing the playlist -- looking
            # exactly like tracks getting skipped. None of these transport
            # controls (seek/skip/next/previous/etc.) should ever fire more
            # than once per physical press.
            sh.setAutoRepeat(False)
            widget._shortcuts[action] = sh

    def _on_rotate_shortcut(self):
        controls = self._widget.player_controls
        try:
            idx = video_rotations.index(controls.video_rotate)
        except ValueError:
            idx = -1
        next_degrees = video_rotations[(idx + 1) % len(video_rotations)]
        controls._on_rotate_action_triggered(next_degrees)

    def _on_repeat_start_shortcut(self):
        widget = self._widget
        try:
            pos = None
            if hasattr(widget, 'player') and widget.player and widget.player.primary_instance is not None:
                try:
                    pos = float(widget.player.primary_instance.get_position())
                except Exception:
                    pos = None
            if pos is None:
                pos = float(widget.player_controls.get_seek_position())
            widget.player_controls.set_loop_start_precise(pos)
        except Exception:
            pass

    def _on_repeat_end_shortcut(self):
        widget = self._widget
        try:
            pos = None
            if hasattr(widget, 'player') and widget.player and widget.player.primary_instance is not None:
                try:
                    pos = float(widget.player.primary_instance.get_position())
                except Exception:
                    pos = None
            if pos is None:
                pos = float(widget.player_controls.get_seek_position())
            widget.player_controls.set_loop_end_precise(pos)
        except Exception:
            pass

    def install_event_filters(self):
        widget = self._widget
        widgets = [
            widget.player_controls.previous_btn, widget.player_controls.backward_btn, widget.player_controls.play_pause_btn,
            widget.player_controls.forward_btn, widget.player_controls.next_btn, widget.player_controls.repeat_btn, widget.player_controls.shuffle_btn,
            widget.player_controls.bookmarks_btn, widget.player_controls.goto_btn, widget.player_controls.screenshot_btn,
            widget.player_controls.seek_slider, widget.player_controls.mute_btn, widget.player_controls.volume_slider,
            widget.player_controls.time_label, widget.player_controls.current_track_label, widget.player_controls.more_btn,
            widget.player_controls.playlist_view_btn, widget.player_controls.queue_view_btn,
            widget.player_controls.toggle_controls_btn, widget.toggle_accordion_btn
        ]
        widget._key_event_filter.install_on_widgets(widgets)
