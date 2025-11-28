import os
import time
import av_play

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QLabel, QListWidget, QListWidgetItem, QMessageBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, Signal, QTimer, QSize

from app_config import prefs
from .player_controls import PlayerControls
from .filters_widget import FiltersWidget

from gui_controls.toggle_button import ToggleButton
from .subtitles import SubtitleManager
from utilities.functions import get_app_path, get_parent_dir
from utilities.media_utils import format_time, seconds_to_microseconds, get_media_files_from_directory


class SubtitlesWidget(QWidget):
    subtitlesToggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Subtitles", self)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setAccessibleName("Subtitles section")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.toggle_btn = ToggleButton("Hide", self)
        self.toggle_btn.setFixedSize(60, 25)
        header_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(header_layout)
        
        self.subtitles_list = QListWidget(self)
        self.subtitles_list.setAccessibleName("Subtitles display")
        self.subtitles_list.setAccessibleDescription("Current video subtitles")
        self.subtitles_list.setAlternatingRowColors(True)
        self.subtitles_list.setMaximumHeight(150)
        
        self.subtitles_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
        """)
        
        layout.addWidget(self.subtitles_list)
        
    def connect_signals(self):
        self.toggle_btn.actuated.connect(self.toggle_subtitles)
        
    def toggle_subtitles(self, hidden):
        self.subtitles_list.setVisible(not hidden)
        
        if hidden:
            self.toggle_btn.setText("Show")
        else:
            self.toggle_btn.setText("Hide")
            
        self.subtitlesToggled.emit(not hidden)
        
    def add_subtitle_line(self, text, timestamp=None):
        item = QListWidgetItem(text)
        if timestamp:
            item.setData(Qt.ItemDataRole.UserRole, timestamp)

        self.subtitles_list.addItem(item)
        
    def clear_subtitles(self):
        self.subtitles_list.clear()
        
    def highlight_subtitle_at_time(self, timestamp):
        for i in range(self.subtitles_list.count()):
            item = self.subtitles_list.item(i)
            item_timestamp = item.data(Qt.ItemDataRole.UserRole)
            if item_timestamp and item_timestamp <= timestamp:
                self.subtitles_list.setCurrentItem(item)
            else:
                break

class VideoDisplayWidget(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.placeholder_label = QLabel("Video Display Area", self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border: 2px dashed #34495e;
            }
        """)
        self.placeholder_label.setMinimumSize(640, 360)
        self.placeholder_label.setAccessibleName("Video display area")
        self.placeholder_label.setAccessibleDescription("Main video playback area")
        
        layout.addWidget(self.placeholder_label)

class PlayerWidget(QWidget):


    def _on_fullscreen_toggled(self, enabled):

        self.player.set_fullscreen(enabled)

    def _on_speed_changed(self, speed):

        self.player.set_playback_speed(speed)

    def _on_resolution_changed(self, resolution):

        if resolution:
            self.player.set_resolution(*resolution)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_seeking = False
        self._last_known_state = av_play.AVPlaybackState.AV_STATE_NOTHING
        self._active_filters = {}
        self._session_filters = {}

        self.setup_ui()
        self.layout_widgets()

        self.player:av_play.MPVVideoPlayer = av_play.MPVVideoPlayer()
        self.subtitle_manager = SubtitleManager()
        self.loading = False

        self._init_player()
        self._populate_filters()

        self.connect_signals()
        self.apply_styles()
        
    def setup_ui(self):
        self.video_display = VideoDisplayWidget(self)
        self.player_controls = PlayerControls(self)
        self.filters_widget = FiltersWidget(self)
        self.subtitles_widget = SubtitlesWidget(self)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        
    def layout_widgets(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        left_layout.addWidget(self.video_display, 1)
        left_layout.addWidget(self.player_controls)
        left_layout.addWidget(self.subtitles_widget)
        
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(self.filters_widget)
        self.main_splitter.setSizes([800, 300])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        
        self.main_layout.addWidget(self.main_splitter)

    def _init_player(self):
        yt_dlp_path = os.path.join(get_parent_dir(), "bin", "yt-dlp.exe" if os.name == 'nt' else "yt-dlp")
        try:
            self.player.init(window=self.video_display.winId(), ytdl_path = yt_dlp_path)
            self.player.set_auto_play(prefs.prefs["autoplay"]) 
            self.player.set_start_file_callback(self.seek_to_last_pos)
        except av_play.AVError as e:
            self.player_controls.set_controls_enabled(False)

    def _populate_filters(self):
        self.available_filters = {
            "Echo": av_play.MPVEchoFilter,
            "Low Pass": av_play.MPVLowPassFilter, "High Pass": av_play.MPVHighPassFilter,
            "Compressor": av_play.MPVCompressorFilter, "Flanger": av_play.MPVFlangerFilter,
            "Chorus": av_play.MPVChorusFilter, "Pitch Shift": av_play.MPVPitchShiftFilter,
            "Band Pass": av_play.MPVBandPassFilter, "Gate": av_play.MPVGateFilter
        }
        for name, filter_class in self.available_filters.items():
            try:
                instance = filter_class()
                params = instance.get_parameters()
                config = {}
                for param_name, default_value in params.items():
                    param_info = instance.info.get("mpv_param_map", {}).get(param_name)
                    if param_info:
                        _, p_type, p_range = param_info
                        if p_type == str and len(p_range) > 0:
                            config[param_name] = ('str', p_range)
                        elif p_type in (int, float) and len(p_range) > 0:
                            config[param_name] = (p_type.__name__, p_range)
                self.filters_widget.add_filter(name, config)
            except Exception:
                continue

    def connect_signals(self):
        self.player_controls.playPauseClicked.connect(self._on_play_pause_clicked)
        self.player_controls.muteUnmuteClicked.connect(self._on_mute_unmute_clicked)
        self.player_controls.forwardClicked.connect(self._on_forward_clicked)
        self.player_controls.backwardClicked.connect(self._on_backward_clicked)
        self.player_controls.previousClicked.connect(self._on_previous_clicked)
        self.player_controls.nextClicked.connect(self._on_next_clicked)
        self.player_controls.repeatClicked.connect(self._on_repeat_clicked)
        self.player_controls.shuffleClicked.connect(self._on_shuffle_clicked)
        
        self.player_controls.seekChanged.connect(self._on_seek_changed)
        self.player_controls.seekPressed.connect(self._on_seek_pressed)
        self.player_controls.seekReleased.connect(self._on_seek_released)
        self.player_controls.volumeChanged.connect(self._on_volume_changed)
        
        self.player_controls.volumeUpRequested.connect(self._on_volume_up)
        self.player_controls.volumeDownRequested.connect(self._on_volume_down)
        self.player_controls.jumpToBeginningRequested.connect(self._on_jump_to_beginning)
        self.player_controls.jumpToEndRequested.connect(self._on_jump_to_end)
        self.player_controls.stopRequested.connect(self._on_stop)
        
        self.player_controls.speedChanged.connect(self._on_speed_changed)
        self.player_controls.resolutionChanged.connect(self._on_resolution_changed)
        self.player_controls.fullscreenToggled.connect(self._on_fullscreen_toggled)

        self.player_controls.timeUpdateRequested.connect(self._update_player_state)
        
        self.filters_widget.filterActivated.connect(self._on_filter_activated)
        self.filters_widget.parameterChanged.connect(self._on_filter_parameter_changed)
        
        self.player_controls.install_shortcuts()

    def apply_styles(self):
        self.setStyleSheet("""
            PlayerWidget { background-color: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 8px; }
        """)

    def _on_play_pause_clicked(self):
        instance = self.player.primary_instance
        if not instance:
            QMessageBox.warning(self, "Playback Error", "No media instance available.")
            return
        try:
            state = instance.get_playback_state()
            if state == av_play.AVPlaybackState.AV_STATE_PLAYING:
                instance.pause()
                self.player_controls.save_last_position()
            else:
                if state == av_play.AVPlaybackState.AV_STATE_STOPPED or av_play.AVPlaybackState.AV_STATE_PAUSED:
                    instance.play()
        except av_play.AVError as e:
            msg = f"Playback error: {getattr(e, 'message', str(e))}"
            QMessageBox.critical(self, "Playback Error", msg)
        
    def _on_mute_unmute_clicked(self):
        instance = self.player.primary_instance
        if not instance:
            QMessageBox.warning(self, "Mute Error", "No media instance available.")
            return
        try:
            state = instance.get_mute_state()
            if state == av_play.AVMuteState.AV_AUDIO_MUTED:
                instance.unmute()
            else:
                instance.mute()
        except av_play.AVError as e:
            msg = f"Mute error: {getattr(e, 'message', str(e))}"
            QMessageBox.critical(self, "Mute Error", msg)
        
    def _on_forward_clicked(self):
        if self.player: self.player.forward(prefs.prefs["offset"]["seek"])
        
    def _on_backward_clicked(self):
        if self.player: self.player.backward(prefs.prefs["offset"]["seek"])
        
    def _on_previous_clicked(self):
        if self.player: self.player.previous()
        
    def _on_next_clicked(self):
        if self.player: self.player.next()
        
    def _on_repeat_clicked(self):
        current_mode = self.player.get_playlist_mode()
        is_shuffle_mode = current_mode == av_play.AVPlaylistMode.SHUFFLE
        
        if current_mode == av_play.AVPlaylistMode.REPEAT_ALL:
            new_mode = av_play.AVPlaylistMode.REPEAT_ONE
            self.player_controls.set_repeat_state(True)
        elif current_mode == av_play.AVPlaylistMode.REPEAT_ONE:
            if is_shuffle_mode:
                new_mode = av_play.AVPlaylistMode.SHUFFLE
            else:
                new_mode = av_play.AVPlaylistMode.SEQUENTIAL
            self.player_controls.set_repeat_state(False)
        else:
            if is_shuffle_mode:
                new_mode = av_play.AVPlaylistMode.SHUFFLE
            else:
                new_mode = av_play.AVPlaylistMode.REPEAT_ALL
            self.player_controls.set_repeat_state(True)
        self.player.set_playlist_mode(new_mode)
        
    def _on_shuffle_clicked(self):
        current_mode = self.player.get_playlist_mode()
        if current_mode == av_play.AVPlaylistMode.SHUFFLE:
            if self.player_controls.is_repeat_on:
                new_mode = av_play.AVPlaylistMode.REPEAT_ALL
            else:
                new_mode = av_play.AVPlaylistMode.SEQUENTIAL
            self.player_controls.set_shuffle_state(False)
        else:
            new_mode = av_play.AVPlaylistMode.SHUFFLE
            self.player_controls.set_shuffle_state(True)
        self.player.set_playlist_mode(new_mode)
        
    def _on_seek_changed(self, position):
        if self.player.primary_instance is not None:
            self.player_controls.set_time_text(f"{format_time(position)} / {format_time(self.player.primary_instance.get_length())}")
            self.is_seeking = True
            self.set_position()
            self.is_seeking = False

    def _on_seek_pressed(self):
        self.is_seeking = True
        
    def _on_seek_released(self):
        self.is_seeking = False
        self.set_position()

    def set_position(self):
        instance = self.player.primary_instance
        if instance:
            try:
                position = self.player_controls.get_seek_position()
                instance.set_position(position)
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Seek Error", msg)
        
    def _on_volume_changed(self, volume):
        instance = self.player.primary_instance
        if instance:
            try:
                instance.set_volume(float(volume))
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Volume Error", msg)

    def _on_volume_up(self):
        instance = self.player.primary_instance
        if instance:
            try:
                current_volume = instance.get_volume()
                new_volume = min(100, current_volume + prefs.prefs["offset"]["volume"])
                instance.set_volume(new_volume)
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Volume Error", msg)
    
    def _on_volume_down(self):
        instance = self.player.primary_instance
        if instance:
            try:
                current_volume = instance.get_volume()
                new_volume = max(0, current_volume - prefs.prefs["offset"]["volume"])
                instance.set_volume(new_volume)
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Volume Error", msg)
    
    def _on_jump_to_beginning(self):
        instance = self.player.primary_instance
        if instance:
            try:
                instance.set_position(0)
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Seek Error", msg)
    
    def _on_jump_to_end(self):
        instance = self.player.primary_instance
        if instance:
            try:
                length = instance.get_length()
                instance.set_position(length -1)
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Seek Error", msg)
    
    def _on_stop(self):
        instance = self.player.primary_instance
        if instance:
            try:
                self.player_controls.save_last_position()
                instance.stop()
            except av_play.AVError as e:
                msg = f"Stop error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Stop Error", msg)

    def _on_filter_activated(self, filter_name, activated):
        instance = self.player.primary_instance
        if not instance:
            return
        try:
            if activated:
                if filter_name in self.available_filters and filter_name not in self._active_filters:
                    filter_class = self.available_filters[filter_name]
                    filter_instance = filter_class()
                    gui_params = self.filters_widget.get_filter_parameters(filter_name)
                    filter_instance.set_parameters(gui_params)
                    filter_id = instance.apply_filter(filter_instance)
                    self._active_filters[filter_name] = filter_id
                    self._session_filters[filter_name] = gui_params.copy()
            else:
                if filter_name in self._active_filters:
                    filter_id = self._active_filters.pop(filter_name)
                    instance.remove_filter(filter_id)
                    if filter_name in self._session_filters:
                        del self._session_filters[filter_name]
        except av_play.AVError:
            pass

    def _on_filter_parameter_changed(self, filter_name, param_name, value):
        instance = self.player.primary_instance
        if not instance or filter_name not in self._active_filters:
            return
        
        try:
            filter_id = self._active_filters[filter_name]
            instance.set_parameter(filter_id, param_name, value)
        except av_play.AVError:
            pass

    def _update_player_state(self):
        instance = self.player.primary_instance
        if not instance:
            self._reset_ui_to_default()
            return
        
        try:
            state = instance.get_playback_state()
            pos = instance.get_position()
            length = instance.get_length()
            
            if state == av_play.AVPlaybackState.AV_STATE_NOTHING and self._last_known_state == av_play.AVPlaybackState.AV_STATE_PLAYING:
                self._last_known_state = state
                self.player.next()
                self._load_subtitles_for_current_track()
                self._update_current_file()
                return

            self._last_known_state = state
            
            self.player_controls.set_play_pause_state(state == av_play.AVPlaybackState.AV_STATE_PLAYING)
            self.player_controls.set_mute_state(instance.get_mute_state() == av_play.AVMuteState.AV_AUDIO_MUTED)
            self.player_controls.set_volume(int(instance.get_volume()))
            self.player_controls.set_current_track(os.path.basename(instance.file_path))
            
            if length > 0:
                self.player_controls.set_controls_enabled(True)
                self.player_controls.set_seek_range(0, length)
                
                if not self.is_seeking:
                    self.player_controls.set_seek_position(pos)
                    self.player_controls.check_loop_position(pos)
                
                self.player_controls.set_time_text(f"{format_time(pos)} / {format_time(length)}")
            
            current_subtitle = self.subtitle_manager.get_subtitle_at(seconds_to_microseconds(pos))
            if current_subtitle:
                self.subtitles_widget.subtitles_list.clear()
                self.subtitles_widget.subtitles_list.addItem(QListWidgetItem(current_subtitle))

        except (av_play.AVError, Exception):
            pass

    def _update_current_file(self):
        instance = self.player.primary_instance
        if instance:
            self.player_controls.set_current_file(instance.file_path)

    def seek_to_last_pos(self, event:object):
        self.seek_to_last()
        #QTimer.singleShot(1, self.seek_to_last)

    def seek_to_last(self):
        instance = self.player.primary_instance
        if not instance:
            return

        try:
            self.player_controls.load_last_position()
            self.loading = False
            if self.player_controls.last_position and self.player_controls.last_position > 0:
                #length = instance.get_length()
                #if length > 0 and self.player_controls.last_position <= length:

                #self.player_controls.seek_slider.blockSignals(True)
                #self.is_seeking = True
                instance.set_position(self.player_controls.last_position)
                #self.player_controls.seek_slider.blockSignals(False)
                #self.is_seeking = False
        except av_play.AVError:
            pass

    def _load_subtitles_for_current_track(self):
        self.subtitles_widget.clear_subtitles()
        instance = self.player.primary_instance
        if instance and av_play.is_path(instance.file_path):
            self.subtitle_manager.load_for_video(instance.file_path)

    def _reset_ui_to_default(self):
        self.player_controls.set_current_track("No media loaded")
        self.player_controls.set_time_text("00:00 / 00:00")
        self.player_controls.set_seek_range(0, 100)
        self.player_controls.set_seek_position(0)
        self.player_controls.set_play_pause_state(False)
        self.player_controls.set_controls_enabled(False)
        self.subtitles_widget.clear_subtitles()

    def load_file(self, file_path: str):
        if self.loading: return
        self.loading = True
        try:
            if self.player:
                self.player.stop_playlist()
                instance = self.player.primary_instance
                if instance:
                    instance.stop()
                    instance.release()
            self.player_controls.set_current_file(file_path)
            dir_path = os.path.dirname(file_path)
            media_files = get_media_files_from_directory(dir_path, av_play.formats["audio"], av_play.formats["video"])
            
            playlist = av_play.Playlist(title=os.path.basename(dir_path))
            start_index = 0
            for i, media_file in enumerate(media_files):
                playlist.add_entry(av_play.PlaylistEntry(location=media_file, title=os.path.basename(media_file)))
                if media_file == file_path:
                    start_index = i

            self.load_playlist(playlist, start_index=start_index)
            #self.player_controls.load_last_position()
        except Exception:
            self._reset_ui_to_default()

    def load_url(self, url: str):
        try:
            playlist = av_play.Playlist(title=url)
            playlist.add_entry(av_play.PlaylistEntry(location=url, title="Streaming URL"))
            self.load_playlist(playlist)
        except Exception:
            self._reset_ui_to_default()

    def load_playlist(self, playlist: av_play.Playlist, start_index: int = 0, auto_play: bool = True):
        try:
            if self.player.primary_instance is not None:
                try:
                    self.player.primary_instance.release()
                    self.player._primary_instance = None
                except Exception:
                    pass
            self.player.stop_playlist()
            self.player.load_playlist(playlist, auto_play=auto_play)
            self._active_filters.clear()
            instance = self.player.primary_instance
            if instance and self._session_filters:
                for filter_name, params in self._session_filters.items():
                    if filter_name in self.available_filters:
                        filter_class = self.available_filters[filter_name]
                        filter_instance = filter_class()
                        filter_instance.set_parameters(params)
                        filter_id = instance.apply_filter(filter_instance)
                        self._active_filters[filter_name] = filter_id
            if 0 <= start_index < len(playlist) and start_index != 0:
                try:
                    jump_method = getattr(self.player, 'jump_to_track', None)
                    if jump_method and callable(jump_method):
                        jump_method(start_index)
                    else:
                        self.player._current_playlist_index = start_index
                        if auto_play:
                            self.player._play_playlist_track()
                except Exception:
                    self.player._current_playlist_index = start_index
                    if auto_play:
                        self.player._play_playlist_track()

            self._load_subtitles_for_current_track()
            self._update_current_file()
            self._update_player_state()
        except Exception as e:
            self._reset_ui_to_default()

    def change_path(self, path: str):
        if not path: return
        try:
            if av_play.is_url(path):
                self.load_url(path)
            elif os.path.isfile(path):
                ext = path.split('.')[-1].lower()
                if ext in ['m3u', 'm3u8', 'pls', 'xspf', 'json']:
                    playlist = av_play.Playlist().load(path)
                    self.load_playlist(playlist)
                else:
                    self.load_file(path)
        except Exception:
            self._reset_ui_to_default()
            
    def sizeHint(self):
        return QSize(1200, 800)
        
    def minimumSizeHint(self):
        return QSize(800, 600)

    def closeEvent(self, event):
        try:
            self.player_controls.save_last_position()
            
            self.player_controls.uninstall_shortcuts()
            if self.player.primary_instance is not None:
                try:
                    self.player.primary_instance.release()
                except Exception:
                    pass
            self.player.release()
        except Exception:
            pass
        super().closeEvent(event)