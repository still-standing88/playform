from typing import Callable, Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut

from app_config import key_config


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

    def setup(self):
        widget = self._widget
        hotkeys = key_config.key_config["Player"]

        shortcuts: Dict[str, Callable] = {
            hotkeys["Play/Pause"]: lambda: self._call_if_enabled(widget.player_controls.play_pause_btn, widget.player_controls.playPauseClicked.emit),
            hotkeys["Backward"]: lambda: self._call_if_enabled(widget.player_controls.backward_btn, widget.player_controls.backwardClicked.emit),
            hotkeys["Forward"]: lambda: self._call_if_enabled(widget.player_controls.forward_btn, widget.player_controls.forwardClicked.emit),
            hotkeys["Stop"]: lambda: self._call_if_media(widget.player_controls.stopRequested.emit),
            hotkeys["Mute/Unmute"]: lambda: self._call_if_enabled(widget.player_controls.mute_btn, widget.player_controls.muteUnmuteClicked.emit),
            hotkeys["Previous"]: lambda: self._call_if_enabled(widget.player_controls.previous_btn, widget.player_controls.previousClicked.emit),
            hotkeys["Next"]: lambda: self._call_if_enabled(widget.player_controls.next_btn, widget.player_controls.nextClicked.emit),
            hotkeys["Jump to beginning"]: lambda: self._call_if_enabled(widget.player_controls.seek_slider, widget.player_controls.jumpToBeginningRequested.emit),
            hotkeys["Jump to the end"]: lambda: self._call_if_enabled(widget.player_controls.seek_slider, widget.player_controls.jumpToEndRequested.emit),
            hotkeys["Toggle repeat"]: lambda: self._call_if_enabled(widget.player_controls.repeat_btn, widget.player_controls.repeatClicked.emit),
            hotkeys["Volume up"]: lambda: self._call_if_enabled(widget.player_controls.volume_slider, widget.player_controls.volume_up),
            hotkeys["Volume down"]: lambda: self._call_if_enabled(widget.player_controls.volume_slider, widget.player_controls.volume_down),
            hotkeys["Bookmarks list"]: lambda: widget.player_controls.show_bookmarks_dialog(),
            hotkeys["Go to time"]: lambda: widget.player_controls.show_goto_dialog(),
            hotkeys["New mark at current position"]: lambda: widget.player_controls.add_bookmark_at_current_position(),
            hotkeys["Repeat loop start"]: lambda: self._on_repeat_start_shortcut(),
            hotkeys["Repeat loop end"]: lambda: self._on_repeat_end_shortcut(),
            hotkeys["Clear repeat loop"]: lambda: widget.player_controls.clear_repeat_loop(),
            hotkeys["Take snapshot"]: lambda: self._call_if_media(widget.player_controls.screenshotRequested.emit),
            hotkeys["Delete current bookmark"]: lambda: widget.player_controls.delete_current_bookmark(),
            hotkeys["Fullscreen"]: lambda: widget.player_controls.fullscreenToggled.emit(True),
            hotkeys["Exit fullscreen"]: lambda: widget.player_controls.fullscreenToggled.emit(False),
            hotkeys["Previous bookmark"]: lambda: widget.player_controls.jump_to_previous_bookmark(),
            hotkeys["Next bookmark"]: lambda: widget.player_controls.jump_to_next_bookmark(),
            hotkeys["Previous repeat loop"]: lambda: widget.player_controls.jump_to_previous_loop(),
            hotkeys["Next repeat loop"]: lambda: widget.player_controls.jump_to_next_loop(),
            hotkeys["Mark1 position"]: lambda: widget.player_controls.jump_to_mark(0),
            hotkeys["Mark2 position"]: lambda: widget.player_controls.jump_to_mark(1),
            hotkeys["Mark3 position"]: lambda: widget.player_controls.jump_to_mark(2),
            hotkeys["Mark4 position"]: lambda: widget.player_controls.jump_to_mark(3),
            hotkeys["Mark5 position"]: lambda: widget.player_controls.jump_to_mark(4),
            hotkeys["Mark6 position"]: lambda: widget.player_controls.jump_to_mark(5),
            hotkeys["Mark7 position"]: lambda: widget.player_controls.jump_to_mark(6),
            hotkeys["Mark8 position"]: lambda: widget.player_controls.jump_to_mark(7),
            hotkeys["Mark9 position"]: lambda: widget.player_controls.jump_to_mark(8),
            hotkeys["Mark10 position"]: lambda: widget.player_controls.jump_to_mark(9),
            hotkeys["close media"]: lambda: widget.close_current_media()
        }

        for shortcut in widget._shortcuts.values():
            shortcut.activated.disconnect()
            shortcut.setParent(None)
        widget._shortcuts.clear()

        for shortcut, callback in shortcuts.items():
            sh = QShortcut(shortcut, widget)
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
            widget._shortcuts[shortcut] = sh

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
            widget.player_controls.toggle_controls_btn, widget.toggle_accordion_btn
        ]
        widget._key_event_filter.install_on_widgets(widgets)
