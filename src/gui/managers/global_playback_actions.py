import av_play
from utilities import signal_manager


class GlobalPlaybackActions:
    """Global playback hotkey/menu actions that operate on
    MainWindow.player_widget, extracted out of MainWindow."""

    def __init__(self, main_window):
        self.main_window = main_window

    def toggle_play_pause(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            try:
                if mw.player_widget.player.primary_instance:
                    state = mw.player_widget.player.primary_instance.get_playback_state()
                    if state == av_play.AVPlaybackState.AV_STATE_PLAYING:
                        mw.player_widget.player.primary_instance.pause()
                        signal_manager.statusbar_message.emit(_("Paused"))
                    else:
                        mw.player_widget.player.primary_instance.play()
                        signal_manager.statusbar_message.emit(_("Playing"))
            except Exception as e:
                signal_manager.statusbar_message.emit(_("No media loaded"))

    def stop_playback(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            try:
                if mw.player_widget.player.primary_instance:
                    mw.player_widget.player.primary_instance.stop()
                    signal_manager.statusbar_message.emit(_("Stopped"))
            except Exception as e:
                signal_manager.statusbar_message.emit(_("No media loaded"))

    def toggle_mute(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            try:
                if mw.player_widget.player.primary_instance:
                    instance = mw.player_widget.player.primary_instance
                    if instance.get_mute_state() == av_play.AVMuteState.AV_AUDIO_UNMUTED:
                        instance.mute()
                    else:
                        instance.unmute()
                    signal_manager.statusbar_message.emit(_("Mute toggled"))
            except Exception as e:
                signal_manager.statusbar_message.emit(_("No media loaded"))

    def seek_forward(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            try:
                if mw.player_widget.player.primary_instance:
                    current_pos = mw.player_widget.player.primary_instance.get_position()
                    mw.player_widget.player.primary_instance.set_position(current_pos + 10)
            except Exception as e:
                pass

    def seek_backward(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            try:
                if mw.player_widget.player.primary_instance:
                    current_pos = mw.player_widget.player.primary_instance.get_position()
                    mw.player_widget.player.primary_instance.set_position(max(0, current_pos - 10))
            except Exception as e:
                pass

    def previous_track(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            try:
                if mw.player_widget.player.primary_instance:
                    mw.player_widget.player.previous()
                    signal_manager.statusbar_message.emit(_("Previous track"))
            except Exception:
                signal_manager.statusbar_message.emit(_("No media loaded"))

    def next_track(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            try:
                if mw.player_widget.player.primary_instance:
                    mw.player_widget.player.next()
                    signal_manager.statusbar_message.emit(_("Next track"))
            except Exception:
                signal_manager.statusbar_message.emit(_("No media loaded"))

    def volume_down(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            instance = mw.player_widget.player.primary_instance
            if instance and hasattr(instance, "get_volume") and hasattr(instance, "set_volume"):
                current_volume = instance.get_volume()
                instance.set_volume(max(0, current_volume - 5))

    def volume_up(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player') and mw.player_widget.player:
            instance = mw.player_widget.player.primary_instance
            if instance and hasattr(instance, "get_volume") and hasattr(instance, "set_volume"):
                current_volume = instance.get_volume()
                instance.set_volume(min(100, current_volume + 5))

    def toggle_repeat(self):
        mw = self.main_window
        if hasattr(mw.player_widget, '_on_repeat_clicked'):
            mw.player_widget._on_repeat_clicked()

    def open_bookmarks_dialog(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player_controls'):
            mw.player_widget.player_controls.show_bookmarks_dialog()

    def open_goto_dialog(self):
        mw = self.main_window
        if hasattr(mw.player_widget, 'player_controls'):
            mw.player_widget.player_controls.show_goto_dialog()
