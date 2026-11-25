import logging
import time

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QMenu

from app_config.touch_config import touch_config
from app_constance.touch_gestures import ACTION_LABELS
from gui_controls.touch_gesture_controller import TouchGestureController
from gui_controls.native_video_input import NativeVideoInput
from utilities.media_utils import format_time
from .playback_options_menu import build_more_options_menu


logger = logging.getLogger(__name__)


class PlayerTouchActions(QObject):
    def __init__(self, widget, config=None):
        super().__init__(widget)
        self.widget = widget
        self.config = config or touch_config
        self._session = None
        self._last_feedback = 0.0
        self.controller = TouchGestureController(widget.video_display, self.config.snapshot(), self._can_interact)
        self.native_input = NativeVideoInput(widget.video_display, self.controller.settings["enabled"])
        self.controller.attach(widget.video_display.placeholder_label)
        self.controller.attach(widget.video_display.loading_label)
        self.controller.triggered.connect(self.trigger)
        self.controller.started.connect(self.start)
        self.controller.updated.connect(self.update)
        self.controller.finished.connect(self.finish)
        self.config.changed.connect(self.reload_settings)
        widget.mediaAvailable.connect(lambda available: self.cancel() if not available else None)
        widget.currentTrackIndexChanged.connect(lambda index: self.cancel())
        widget._fileLoadedFromMpv.connect(self.native_input.refresh)
        widget.video_display.create_touch_controls({
            "backward": lambda: self.run_action("seek_backward"),
            "play_pause": lambda: self.run_action("play_pause"),
            "forward": lambda: self.run_action("seek_forward"),
            "menu": lambda: self.show_menu(widget.video_display.touch_controls.pos()),
            "fullscreen": lambda: self.run_action("fullscreen"),
        })

    def reload_settings(self):
        self.controller.set_settings(self.config.snapshot())
        self.native_input.set_enabled(self.controller.settings["enabled"])
        if not self.controller.settings["enabled"]:
            self.widget.video_display.touch_controls.hide()

    def cancel(self):
        self.controller.cancel()

    def is_seeking(self):
        return self._session is not None and self._session["action"] == "seek"

    def _can_interact(self):
        return (QApplication.activeModalWidget() is None
                and not self.widget._loading
                and (not self.controller.settings["fullscreen_only"] or self.widget.video_display._fullscreen))

    def _has_media(self):
        return self.widget.player_controls.has_loaded_media()

    def feedback(self, text, force=False):
        if not self.controller.settings["feedback"]:
            return
        now = time.monotonic()
        if not force and now - self._last_feedback < 0.08:
            return
        self._last_feedback = now
        if self.widget.player.primary_instance is not None:
            self.widget.player.show_osd_text(text, 1000)

    def trigger(self, gesture, point):
        self.run_action(self.controller.settings["bindings"][gesture], point)

    def run_action(self, action, point=None):
        if action == "disabled":
            return
        w, c = self.widget, self.widget.player_controls
        if action == "toggle_controls":
            if w.video_display._fullscreen:
                w.video_display.toggle_touch_controls()
            else:
                c.toggle_controls_btn.click()
            return
        if action == "fullscreen":
            c.fullscreenToggled.emit(not w.video_display._fullscreen)
            return
        if not self._has_media():
            return
        try:
            if action in ("seek_backward", "seek_forward"):
                instance = w.player.primary_instance
                if not w.player.can_seek():
                    self.feedback(_("Seeking unavailable"), True)
                    return
                key = action + "_seconds"
                amount = self.controller.settings[key] * (-1 if action == "seek_backward" else 1)
                length = float(instance.get_length())
                if length <= 0:
                    self.feedback(_("Seeking unavailable"), True)
                    return
                position = self._clamp(float(instance.get_position()) + amount, 0, max(0, length - 0.1))
                instance.set_position(position)
                c.set_seek_position(int(position))
                self.feedback(_("{offset:+d} seconds").format(offset=amount), True)
                return
            if action == "menu":
                self.show_menu(point or w.video_display.rect().center())
                return
            callbacks = {
                "play_pause": c.playPauseClicked.emit, "mute": c.muteUnmuteClicked.emit,
                "previous": c.previousClicked.emit, "next": c.nextClicked.emit,
                "bookmark": c.add_bookmark_at_current_position,
                "loop_start": c.set_loop_start, "loop_end": c.set_loop_end,
                "clear_loop": c.clear_repeat_loop, "screenshot": c.screenshotRequested.emit,
                "playlist": w.show_playlist_dialog, "queue": w.show_queue_dialog,
                "subtitles": lambda: w.subtitles_widget.visibilityToggled.emit(not w.player.get_subtitle_visibility()),
            }
            if action in ("subtitles", "screenshot") and not c.is_video_available:
                return
            callback = callbacks.get(action)
            if callback:
                callback()
                self.feedback(_(ACTION_LABELS[action]), True)
        except Exception:
            logger.exception("Touch action %s failed", action)

    def show_menu(self, point):
        c = self.widget.player_controls
        menu = QMenu(self.widget.video_display)
        menu.setStyleSheet("QMenu::item { padding: 10px 24px; }")
        for action in ("play_pause", "seek_backward", "seek_forward", "bookmark", "loop_start", "loop_end", "subtitles", "fullscreen"):
            item = menu.addAction(_(ACTION_LABELS[action]))
            item.setEnabled(action == "fullscreen" or self._has_media())
            if action == "subtitles":
                item.setEnabled(c.is_video_available)
            item.triggered.connect(lambda checked=False, a=action: self.run_action(a))
        more = menu.addAction(_("More playback options..."))
        more.setEnabled(self._has_media())
        def show_more():
            self._more_menu = build_more_options_menu(c)
            self._more_menu.aboutToHide.connect(self._more_menu.deleteLater)
            self._more_menu.popup(self.widget.video_display.mapToGlobal(point.toPoint() if hasattr(point, "toPoint") else point))
        more.triggered.connect(show_more)
        self._menu = menu
        menu.aboutToHide.connect(menu.deleteLater)
        menu.popup(self.widget.video_display.mapToGlobal(point.toPoint() if hasattr(point, "toPoint") else point))

    def start(self, gesture):
        action = self.controller.settings["bindings"][gesture]
        if action == "disabled" or not self._has_media():
            return
        w, c = self.widget, self.widget.player_controls
        instance = w.player.primary_instance
        if action in ("brightness", "zoom", "pan") and not c.is_video_available:
            return
        session = {"gesture": gesture, "action": action, "instance": instance}
        try:
            if action == "seek":
                if not w.player.can_seek():
                    self.feedback(_("Seeking unavailable"), True)
                    return
                session.update(base=float(instance.get_position()), length=float(instance.get_length()))
                if session["length"] <= 0:
                    self.feedback(_("Seeking unavailable"), True)
                    return
                session["value"] = session["base"]
                c._is_user_seeking = True
                w.is_seeking = True
            elif action == "volume":
                session["base"] = float(instance.get_volume())
            elif action == "brightness":
                session["base"] = w.filters_widget.brightness_spin.value()
            elif action == "zoom":
                session["base"] = float(w.player.get_scale())
            elif action == "pan":
                session["base"] = (c.pan_x, c.pan_y)
            elif action == "temporary_speed":
                session["base"] = c.current_speed
                c.speedChanged.emit(self.controller.settings["hold_speed"])
                self.feedback(_("{speed:g}x while held").format(speed=self.controller.settings["hold_speed"]), True)
            else:
                return
            self._session = session
        except Exception:
            logger.exception("Could not start touch action %s", action)

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    def update(self, gesture, delta):
        s = self._session
        if s is None or s["gesture"] != gesture or s["instance"] is not self.widget.player.primary_instance:
            return
        w, c = self.widget, self.widget.player_controls
        action, base = s["action"], s["base"]
        sensitivity = self.controller.settings["sensitivity"]
        try:
            if action == "seek":
                precision = 1 / (1 + abs(delta["y"]) * 8)
                s["value"] = self._clamp(s["value"] + delta["dx"] * self.controller.settings["scrub_seconds"] * sensitivity * precision,
                                         0, max(0, s["length"] - 0.1))
                c.set_seek_position(int(s["value"]))
                self.feedback(_("Seek: {time}").format(time=format_time(int(s["value"]))))
            elif action == "volume":
                value = self._clamp(base - delta["y"] * 100 * sensitivity, 0, self.controller.settings["volume_limit"])
                s["instance"].set_volume(value)
                c.set_volume(round(value))
                s["value"] = value
                self.feedback(_("Volume: {volume}%").format(volume=round(value)))
            elif action == "brightness":
                value = self._clamp(base - delta["y"] * 2 * sensitivity, 0, 2)
                w.filters_widget.brightness_spin.setValue(value)
                self.feedback(_("Brightness: {value}%").format(value=round(value * 100)))
            elif action == "zoom":
                value = self._clamp(base * delta["scale"] ** sensitivity, 0.25, 5)
                c.scaleChanged.emit(value)
                self.feedback(_("Zoom: {value}%").format(value=round(value * 100)))
            elif action == "pan":
                c.pan_x = self._clamp(base[0] + delta["x"] * sensitivity, -1, 1)
                c.pan_y = self._clamp(base[1] + delta["y"] * sensitivity, -1, 1)
                c.panChanged.emit(c.pan_x, c.pan_y)
                self.feedback(_("Pan: {x:+.2f}, {y:+.2f}").format(x=c.pan_x, y=c.pan_y))
        except Exception:
            logger.exception("Touch adjustment %s failed", action)
            self.cancel()

    def finish(self, gesture, cancelled):
        s = self._session
        if s is None or s["gesture"] != gesture:
            return
        self._session = None
        w, c = self.widget, self.widget.player_controls
        action, base = s["action"], s["base"]
        if action == "seek":
            c._is_user_seeking = False
            w.is_seeking = False
        if s["instance"] is not w.player.primary_instance:
            return
        try:
            if action == "temporary_speed":
                c.speedChanged.emit(base)
                self.feedback(_("Speed: {speed:g}x").format(speed=base), True)
            elif action == "seek":
                value = base if cancelled else s["value"]
                c.set_seek_position(int(value))
                if not cancelled:
                    s["instance"].set_position(value)
            elif action == "volume":
                value = base if cancelled else s.get("value", base)
                s["instance"].set_volume(value)
                c.set_volume(round(value))
                if not cancelled:
                    from app_config import prefs
                    prefs.prefs["player_volume"] = value
                    prefs.save()
            elif cancelled and action == "brightness":
                w.filters_widget.brightness_spin.setValue(base)
            elif cancelled and action == "zoom":
                c.scaleChanged.emit(base)
            elif cancelled and action == "pan":
                c.pan_x, c.pan_y = base
                c.panChanged.emit(*base)
            if cancelled:
                self.feedback(_("Gesture cancelled"), True)
        except Exception:
            logger.exception("Could not finish touch action %s", action)
