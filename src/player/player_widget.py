import os
import sys
import datetime as dt
import time
import logging
from typing import Callable, Optional, Dict
import utilities.vlc_bootstrap
import av_play

from PySide6.QtWidgets import (QWidget, QLayout, QVBoxLayout, QHBoxLayout, QSplitter,
                               QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSlider, QSpinBox)
from PySide6.QtGui import QCloseEvent, QFont, QPalette, QColor, QShortcut
from PySide6.QtCore import Qt, Signal, QTimer, QSize, Slot

from app_config import prefs, key_config
from app_constance.vlc_args import log_args
from .player_controls import PlayerControls
from .subtitles_widget import SubtitlesWidget
from .video_display_widget import VideoDisplayWidget
from .timeline import SegmentTimelineWidget
from gui_controls.player_key_event_filter import KeyEventFilter
from gui_controls.toggle_button import ToggleButton
from gui_controls.accordion import Accordion
from .subtitles import SubtitleManager
from .filters_widget import FiltersWidget
from .lazy_player import LazyPlaylistPlayer
from app_constance.styles import PLAYER_WIDGET_STYLE

from utilities.functions import get_app_path, get_debug_level, get_parent_dir, get_vlclog_file, parse_vlc_args
from utilities.functions import is_youtube_url, is_local_file, open_file_location
from utilities.media_utils import format_time, seconds_to_microseconds, get_media_files_from_directory
from utilities.formats import formats as media_formats
from utilities import signal_manager


LayoutType = QVBoxLayout | QHBoxLayout 

logger = logging.getLogger(__name__)


class PlayerWidget(QWidget):

    playbackStateChanged = Signal(bool)
    muteStateChanged = Signal(bool)
    mediaAvailable = Signal(bool)
    repeatModeChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_seeking = False
        self._last_known_state = av_play.AVPlaybackState.AV_STATE_NOTHING
        self._last_muted: Optional[bool] = None
        self._had_media = False
        self._shortcuts:Dict[str, QShortcut] = {}
        self._key_event_filter = KeyEventFilter(self)
        self._youtube_info_cache: Dict[str, dict] = {}
        self._last_subtitle_text: Optional[str] = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.setup_ui()
        self.layout_widgets()

        self.player:LazyPlaylistPlayer = LazyPlaylistPlayer()
        self.subtitle_manager = SubtitleManager()
        self._loading = False
        

        self._init_player()
        self.connect_signals()
        self.apply_styles()
        self.set_shortcuts()
        self._install_event_filters()
        
    def setup_ui(self):
        self.player_controls = PlayerControls(self)
        self.video_display = VideoDisplayWidget(parent = self, on_close_callback=self._update_fullscreen_state)
        self.timeline = SegmentTimelineWidget(self)
        self.timeline.setAccessibleDescription(_("Segment Timeline Widget"))

        self.subtitles_widget = SubtitlesWidget(self)
        self.filters_widget = FiltersWidget(self)
        self.side_accordion = Accordion(self)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_path_context_menu)
        
    def layout_widgets(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        left_layout.addWidget(self.video_display, 1)
        left_layout.addWidget(self.timeline)
        left_layout.addWidget(self.player_controls)
        self.video_display.set_position_info(left_layout, 0)

        self.side_accordion.add_section(_("Subtitles"), self.subtitles_widget)
        self.side_accordion.add_section(_("Video Filters"), self.filters_widget)

        self.side_accordion.setMinimumWidth(300)

        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(self.side_accordion)

        self.main_splitter.setSizes([800, 300])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        
        self.main_layout.addWidget(self.main_splitter)

    def _init_player(self):
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
                self.player.init(vlc_args=vlc_args+extra_args, device_id=device_id)
            except:
                self.player.init(vlc_args=vlc_args, device_id=device_id)
            self.player.set_window(self.video_display.winId())
            self.player.set_auto_play(prefs.prefs["autoplay"]) 
            self.player.set_track_end_callback(self._update_current_track)
            self.filters_widget.set_player(self.player)
            device_name = prefs.prefs.get("device_name", "")
            if device_name:
                device_count = self.player.get_devices()
                for i in range(device_count):
                    device_info = self.player.get_device(i)
                    if device_info and device_info.name == device_name:
                        self.player.set_device(i)
                        break
            else:
                device = prefs.prefs.get("device", 0)
                if device < self.player.get_devices():
                    self.player.set_device(device)


            rm = prefs.prefs.get("repeat_mode", 0)
            if rm == 2:
                self.player.set_playlist_repeat_mode(av_play.AVPlaylistRepeatMode.REPEAT_ONE)
                self.player_controls.set_repeat_mode("one")
            elif rm == 1:
                self.player.set_playlist_repeat_mode(av_play.AVPlaylistRepeatMode.REPEAT_ALL)
                self.player_controls.set_repeat_mode("all")
            else:
                self.player.set_playlist_repeat_mode(av_play.AVPlaylistRepeatMode.REPEAT_OFF)
                self.player_controls.set_repeat_mode("off")

            sh = bool(prefs.prefs.get("shuffle", False))
            if sh:
                self.player.set_playlist_shuffle_mode(av_play.AVPlaylistShuffleMode.SHUFFLE)
                self.player_controls.set_shuffle_state(True)
            else:
                self.player.set_playlist_shuffle_mode(av_play.AVPlaylistShuffleMode.SEQUENTIAL)
                self.player_controls.set_shuffle_state(False)

        except av_play.AVError as e:
            self.player_controls.set_controls_enabled(False)


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
        self.player_controls.fullscreenToggled.connect(self._on_fullscreen_toggled)
        self.player_controls.timeUpdateRequested.connect(self._update_player_state)
        self.timeline.segmentAdded.connect(self._on_timeline_segment_added)
        self.timeline.segmentUpdated.connect(self._on_timeline_segment_updated)
        self.timeline.segmentRemoved.connect(self._on_timeline_segment_removed)
        self.timeline.segmentSelected.connect(self._on_timeline_segment_selected)
        self.timeline.markerAdded.connect(self._on_timeline_marker_added)
        self.timeline.markerMoved.connect(self._on_timeline_marker_moved)
        self.timeline.markerRemoved.connect(self._on_timeline_marker_removed)
        self.timeline.markerSelected.connect(self._on_timeline_marker_selected)
        self.player_controls.aspectRatioChanged.connect(self._on_aspect_ratio_changed)
        self.player_controls.scaleChanged.connect(self._on_scale_changed)
        self.player_controls.screenshotRequested.connect(self._on_screenshot)
        self.player.signals.extraction_started.connect(self._on_url_extraction_started)
        self.player.signals.extraction_complete.connect(self._on_url_extraction_complete)
        self.player.signals.extraction_failed.connect(self._on_url_extraction_failed)

    def apply_styles(self):
        self.setStyleSheet(PLAYER_WIDGET_STYLE)

    @Slot()
    def _on_play_pause_clicked(self):
        instance = self.player.primary_instance
        if not instance:
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
            QMessageBox.critical(self, _("Playback Error"), msg)
        
    @Slot()
    def _on_mute_unmute_clicked(self):
        instance = self.player.primary_instance
        if not instance:
            return
        try:
            state = instance.get_mute_state()
            if state == av_play.AVMuteState.AV_AUDIO_MUTED:
                instance.unmute()
            else:
                instance.mute()
        except av_play.AVError as e:
            msg = f"Mute error: {getattr(e, 'message', str(e))}"
            QMessageBox.critical(self, _("Mute Error"), msg)

    def _has_active_media_instance(self) -> bool:
        try:
            return bool(getattr(self, 'player', None) and self.player.primary_instance is not None)
        except Exception:
            return False

    def _call_if_enabled(self, widget, callback: Callable[[], None]):
        try:
            if widget is not None and not widget.isEnabled():
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
        
    @Slot()
    def _on_forward_clicked(self):
        if self.player:
            self.player_controls._is_user_seeking = True
            self.player.forward(prefs.prefs["offset"]["seek"])
            self.player_controls._is_user_seeking = False
        
    @Slot()
    def _on_backward_clicked(self):
        if self.player:
            self.player_controls._is_user_seeking = True
            self.player.backward(prefs.prefs["offset"]["seek"])
            self.player_controls._is_user_seeking = False
        
    @Slot()
    def _on_previous_clicked(self):
        if self.player:
            self.player.previous()
            self.filters_widget.reset_filters()
        
    @Slot()
    def _on_next_clicked(self):
        if self.player:
            self.player.next()
            self.filters_widget.reset_filters()
        
    @Slot()
    def _on_repeat_clicked(self):
        current_mode = self.player.get_playlist_repeat_mode()

        if current_mode == av_play.AVPlaylistRepeatMode.REPEAT_ONE:
            new_mode = av_play.AVPlaylistRepeatMode.REPEAT_ALL
            self.player_controls.set_repeat_mode("all")
            prefs.prefs["repeat_mode"] = 1
        elif current_mode == av_play.AVPlaylistRepeatMode.REPEAT_ALL:
            new_mode = av_play.AVPlaylistRepeatMode.REPEAT_OFF
            self.player_controls.set_repeat_mode("off")
            prefs.prefs["repeat_mode"] = 0
        else:
            new_mode = av_play.AVPlaylistRepeatMode.REPEAT_ONE
            self.player_controls.set_repeat_mode("one")
            prefs.prefs["repeat_mode"] = 2
        self.player.set_playlist_repeat_mode(new_mode)
        self.repeatModeChanged.emit(prefs.prefs["repeat_mode"])
        try:
            prefs.save()
        except Exception:
            pass
        
    @Slot()
    def _on_shuffle_clicked(self):
        current_mode = self.player.get_playlist_shuffle_mode()

        if current_mode == av_play.AVPlaylistShuffleMode.SHUFFLE:
            new_mode = av_play.AVPlaylistShuffleMode.SEQUENTIAL
            self.player_controls.set_shuffle_state(False)
            prefs.prefs["shuffle"] = False
        else:
            new_mode = av_play.AVPlaylistShuffleMode.SHUFFLE
            self.player_controls.set_shuffle_state(True)
            prefs.prefs["shuffle"] = True
        self.player.set_playlist_shuffle_mode(new_mode)
        try:
            prefs.save()
        except Exception:
            pass
        
    @Slot(int)
    def _on_seek_changed(self, position):
        if self.player.primary_instance is not None:
            self.player_controls.set_time_text(f"{format_time(position)} / {format_time(self.player.primary_instance.get_length())}")
            self.is_seeking = True
            self.set_position()
            self.is_seeking = False

    def _on_seek_pressed(self):
        self.is_seeking = True
        self.player_controls._is_user_seeking = True
        
    def _on_seek_released(self):
        self.is_seeking = False
        self.player_controls._is_user_seeking = False
        self.set_position()

    def set_position(self):
        instance = self.player.primary_instance
        if instance:
            try:
                position = self.player_controls.get_seek_position()
                instance.set_position(position)
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, _("Seek Error"), msg)
        
    @Slot(int)
    def _on_volume_changed(self, volume):
        instance = self.player.primary_instance
        if instance:
            try:
                instance.set_volume(float(volume))
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, _("Volume Error"), msg)

    @Slot()
    def _on_volume_up(self):
        instance = self.player.primary_instance
        if instance:
            try:
                current_volume = instance.get_volume()
                new_volume = min(200, current_volume + prefs.prefs["offset"]["volume"])
                instance.set_volume(new_volume)
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, _("Volume Error"), msg)
    
    def _on_volume_down(self):
        instance = self.player.primary_instance
        if instance:
            try:
                current_volume = instance.get_volume()
                new_volume = max(0, current_volume - prefs.prefs["offset"]["volume"])
                instance.set_volume(new_volume)
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, _("Volume Error"), msg)
    
    @Slot()
    def _on_jump_to_beginning(self):
        instance = self.player.primary_instance
        if instance:
            try:
                instance.set_position(0)
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, _("Seek Error"), msg)
    
    @Slot()
    def _on_jump_to_end(self):
        instance = self.player.primary_instance
        if instance:
            try:
                length = instance.get_length()
                instance.set_position(length )
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, _("Seek Error"), msg)
    
    @Slot()
    def _on_stop(self):
        instance = self.player.primary_instance
        if instance:
            try:
                self.player_controls.save_last_position()
                instance.stop()
            except av_play.AVError as e:
                msg = f"Stop error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, _("Stop Error"), msg)

    @Slot(float)
    def _on_speed_changed(self, speed):
        self.player.set_playback_speed(speed)

    @Slot(str)
    def _on_aspect_ratio_changed(self, ratio: str):
        self.player.set_aspect_ratio(ratio)

    @Slot(float)
    def _on_scale_changed(self, scale: float):
        self.player.set_scale(scale)

    @Slot(bool)
    def _on_fullscreen_toggled(self, enabled):
        self.video_display.set_fullscreen(enabled)
        try:
            self.player.set_fullscreen(enabled)
        except Exception:
            pass

    def _on_screenshot(self):
        try:
            image_format = prefs.prefs.get("image_format", "png")
            file_date = str(dt.datetime.now().strftime("%y-%d-%m-%I-%M-%S%p"))
            image_path = os.path.join(get_app_path(), "Screenshots", f"screenshot-{file_date}.{image_format}")
            self.player.take_screenshot(image_path)
            signal_manager.statusbar_message.emit(
                _("Screenshot saved: {filename}").format(
                    filename=os.path.basename(image_path)
                )
            )
        except Exception:
            signal_manager.statusbar_message.emit(_("Failed to take screenshot"))
    
    def close_current_media(self):
        try:
            if self.player.primary_instance is not None:
                self.player_controls.save_last_position()
                self.player.stop_playlist()
                self.player.release()
                self._init_player()
                self._reset_ui_to_default()
                self._had_media = False
                self.player_controls._source_url = None
                self.mediaAvailable.emit(False)
        except Exception as e:
            pass


    def show_path_context_menu(self, position):

        from PySide6.QtWidgets import QMenu, QApplication
        
        current_file = self.player_controls._current_file
        if not current_file:
            return
        
        menu = QMenu(self)
        

        copy_action = menu.addAction(_("Copy Path"))
        copy_action.triggered.connect(lambda: self._copy_path_to_clipboard(current_file))
        

        if is_local_file(current_file):
            import sys
            if sys.platform == "win32":
                explorer_action = menu.addAction(_("Open in Explorer"))
                explorer_action.triggered.connect(lambda: open_file_location(current_file))

        source = self.player_controls._source_url or current_file
        if is_youtube_url(source):
            menu.addSeparator()
            yt_info_action = menu.addAction(_("Show YouTube Info"))
            yt_info_action.triggered.connect(self.show_youtube_info_dialog)
        
        menu.exec(self.mapToGlobal(position))
    
    def _copy_path_to_clipboard(self, path: str):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(path)

    def _update_media_player_data(self):
        self.player_controls.load_bookmarks()
        self.player_controls.load_last_positions()
        self.player_controls.load_repeat_loops()
        try:
            self._update_timeline_from_data()
        except Exception:
            pass

    def _update_timeline_from_data(self):
        length = None
        try:
            if self.player and self.player.primary_instance is not None:
                length = float(self.player.primary_instance.get_length())
        except Exception:
            length = None

        if not length or length <= 0:

            length = float(self.player_controls.seek_slider.maximum() or 0)

        loops = self.player_controls.get_current_loops()
        segments_norm = []
        for start, end in loops:
            if start is None or end is None:
                continue
            if length > 0:
                segments_norm.append((start / length, end / length))

        self.timeline.setSegments(segments_norm)

        self._timeline_seg_map = {}
        for idx, seg in enumerate(self.timeline.segments):
            self._timeline_seg_map[seg['id']] = idx

        bookmarks = self.player_controls.get_bookmarks()
        markers_norm = []
        for pos in bookmarks:
            if length > 0:
                markers_norm.append(pos / length)

        self.timeline.setMarkers(markers_norm)
        self._timeline_marker_map = {}
        for idx, m in enumerate(self.timeline.markers):
            self._timeline_marker_map[m['id']] = idx

    def _norm_to_seconds(self, norm:float) -> float:
        try:
            if self.player and self.player.primary_instance is not None:
                length = float(self.player.primary_instance.get_length())
                return norm * length
        except Exception:
            pass
        return norm * float(self.player_controls.seek_slider.maximum() or 0)

    def _seconds_to_norm(self, sec:float) -> float:
        try:
            if self.player and self.player.primary_instance is not None:
                length = float(self.player.primary_instance.get_length())
                if length > 0:
                    return sec / length
        except Exception:
            pass
        maxv = float(self.player_controls.seek_slider.maximum() or 1)
        if maxv <= 0:
            return 0.0
        return sec / maxv

    def _on_timeline_segment_added(self, start_norm:float, end_norm:float):
        start_sec = self._norm_to_seconds(start_norm)
        end_sec = self._norm_to_seconds(end_norm)
        try:
            self.player_controls.set_loop_start_precise(start_sec)
            self.player_controls.set_loop_end_precise(end_sec)
        except Exception:
            pass
        self._update_timeline_from_data()

    @Slot(int, float, float)
    def _on_timeline_segment_updated(self, seg_id:int, start_norm:float, end_norm:float):
        if seg_id in self._timeline_seg_map:
            loop_index = self._timeline_seg_map[seg_id]
            start_sec = self._norm_to_seconds(start_norm)
            end_sec = self._norm_to_seconds(end_norm)
            self.player_controls.update_loop_by_index(loop_index, start_sec, end_sec)
            self._update_timeline_from_data()

    @Slot(int)
    def _on_timeline_segment_removed(self, seg_id:int):
        if seg_id in self._timeline_seg_map:
            loop_index = self._timeline_seg_map[seg_id]
            self.player_controls.delete_loop_by_index(loop_index)
            self._update_timeline_from_data()

    @Slot(int)
    def _on_timeline_segment_selected(self, seg_id:int):
        if seg_id in self._timeline_seg_map:
            self.player_controls._current_loop_index = self._timeline_seg_map[seg_id]

    @Slot(float)
    def _on_timeline_marker_added(self, pos_norm:float):
        pos_sec = self._norm_to_seconds(pos_norm)
        self.player_controls.add_bookmark_at_position(pos_sec)
        self._update_timeline_from_data()

    @Slot(int, float)
    def _on_timeline_marker_moved(self, marker_id:int, pos_norm:float):
        if marker_id in self._timeline_marker_map:
            bm_index = self._timeline_marker_map[marker_id]
            pos_sec = self._norm_to_seconds(pos_norm)
            self.player_controls.update_bookmark_at_index(bm_index, pos_sec)
            self._update_timeline_from_data()

    @Slot(int)
    def _on_timeline_marker_removed(self, marker_id:int):
        if marker_id in self._timeline_marker_map:
            bm_index = self._timeline_marker_map[marker_id]
            self.player_controls.delete_bookmark_at(bm_index)
            self._update_timeline_from_data()

    @Slot(int)
    def _on_timeline_marker_selected(self, marker_id:int):
        if marker_id in self._timeline_marker_map:
            self.player_controls._current_bookmark_index = self._timeline_marker_map[marker_id]

    def _update_fullscreen_state(self, state:bool):
        self.player_controls.set_fullscreen_state(state)
        self.player_controls.fullscreenToggled.emit(state)

    def _update_current_track(self, index):
        if self.player is not None and self.player.primary_instance is not None and self.player.current_playlist is not None:
            try:
                entry = self.player.current_playlist.get_entry(index)
                if entry:
                    track_name = entry.title or os.path.basename(entry.location)
                    self.player_controls.set_current_track(track_name)
                    self._load_subtitles_for_current_track()
                    self.filters_widget.reset_filters()
            except av_play.AVError:
                pass

    @Slot()
    def _update_player_state(self):
        instance = self.player.primary_instance
        if not instance:
            if self._had_media:
                self._had_media = False
                self.mediaAvailable.emit(False)
            self._reset_ui_to_default()
            return
        
        try:
            state = instance.get_playback_state()
            pos = instance.get_position()
            length = instance.get_length()

            if not self._had_media:
                self._had_media = True
                self.mediaAvailable.emit(True)
            
            if state == av_play.AVPlaybackState.AV_STATE_NOTHING and self._last_known_state == av_play.AVPlaybackState.AV_STATE_PLAYING:
                self._last_known_state = state
                if not self._loading:
                    pass #self.player.next()
                self._load_subtitles_for_current_track()
                self.filters_widget.reset_filters()
                self._update_current_file()
                return

            self._last_known_state = state

            is_playing = state == av_play.AVPlaybackState.AV_STATE_PLAYING
            is_muted = instance.get_mute_state() == av_play.AVMuteState.AV_AUDIO_MUTED
            
            self.playbackStateChanged.emit(is_playing)
            if is_muted != self._last_muted:
                self._last_muted = is_muted
                self.muteStateChanged.emit(is_muted)
            
            self.player_controls.set_play_pause_state(is_playing)
            self.player_controls.set_mute_state(is_muted)
            self.player_controls.set_volume(int(instance.get_volume()))
            track_name = os.path.basename(instance.file_path)
            if self.player.current_playlist is not None:
                try:
                    entry = self.player.current_playlist.get_entry(self.player._current_playlist_index)
                    if entry and entry.title:
                        track_name = entry.title
                except Exception:
                    pass
            self.player_controls.set_current_track(track_name)
            
            if length > 0:
                self.player_controls.set_controls_enabled(True)
                self.player_controls.set_seek_range(0, length)
                
                if not self.is_seeking:
                    self.player_controls.set_seek_position(pos)
                    self.player_controls.check_loop_position(pos)
                
                self.player_controls.set_time_text(f"{format_time(pos)} / {format_time(length)}")
            
            current_subtitle = self.subtitle_manager.get_subtitle_at(seconds_to_microseconds(pos))
            
            self.subtitles_widget.highlight_subtitle_at_time(seconds_to_microseconds(pos))
            
            if current_subtitle:

                from app_config import prefs
                if prefs.prefs.get("enable_speech", False) and current_subtitle != self._last_subtitle_text:
                    from utilities.speech import speech_manager
                    speech_manager.output(current_subtitle, interrupt=False)
                    self._last_subtitle_text = current_subtitle
            elif self._last_subtitle_text is not None:

                self._last_subtitle_text = None

        except (av_play.AVError, Exception):
            pass

    def _update_current_file(self):
        instance = self.player.primary_instance
        if instance:
            self.player_controls.set_current_file(instance.file_path)
            self._update_media_player_data()

    def seek_to_last_pos(self, event:object):
        self.seek_to_last()
        #QTimer.singleShot(1, self.seek_to_last)

    def seek_to_last(self):
        instance = self.player.primary_instance
        if not instance:
            return

        try:
            self.player_controls.load_last_position()
            #self.loading = False
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
        self._last_subtitle_text = None
        instance = self.player.primary_instance
        if instance and av_play.is_path(instance.file_path):
            if self.subtitle_manager.load_for_video(instance.file_path):

                self.subtitles_widget.load_all_subtitles(self.subtitle_manager)
        self.filters_widget.reset_filters()

    def _reset_ui_to_default(self):
        self.player_controls.set_current_track(_("No media loaded"))
        self.player_controls.set_time_text("00:00 / 00:00")
        self.player_controls.set_seek_range(0, 100)
        self.player_controls.set_seek_position(0)
        self.player_controls.set_play_pause_state(False)
        self.player_controls.set_controls_enabled(False)
        self.subtitles_widget.clear_subtitles()
        self.filters_widget.reset_filters()

    def load_file(self, file_path: str):
        signal_manager.statusbar_message.emit(
            _("Loading: {filename}").format(filename=os.path.basename(file_path))
        )
        self.player_controls._source_url = None
        #if self.loading: return
        #self.loading = True
        try:
            if self.player:
                self.player.stop_playlist()
                instance = self.player.primary_instance
                if instance:
                    instance.stop()
                    instance.release()
            self.player_controls.set_current_file(file_path)
            dir_path = os.path.dirname(file_path)
            media_files = get_media_files_from_directory(dir_path, media_formats["audio"], media_formats["video"])
            
            playlist = av_play.Playlist(title=os.path.basename(dir_path))
            start_index = 0
            norm_file_path = os.path.normpath(file_path)
            for i, media_file in enumerate(media_files):
                playlist.add_entry(av_play.PlaylistEntry(location=media_file, title=os.path.basename(media_file)))
                if os.path.normpath(media_file) == norm_file_path:
                    start_index = i

            self.load_playlist(playlist, start_index=start_index)
            self.player_controls.set_current_track(os.path.basename(file_path))
            self.player_controls.load_last_position()
            self.seek_to_last()
            self._update_media_player_data()
        except Exception:
            self._reset_ui_to_default()

    def load_url(self, url: str):
        signal_manager.statusbar_message.emit(_("Loading URL: {url}").format(url=url))
        self.player_controls._source_url = url
        try:
            self.player.load_url(url)
        except Exception as e:
            logger.error(f"Failed to start URL extraction: {e}")
            self._reset_ui_to_default()

    def load_playlist(self, playlist: av_play.Playlist, start_index: int = 0, auto_play: bool = True):
        if playlist is None or len(playlist) == 0:
            self._reset_ui_to_default()
            return
        signal_manager.statusbar_message.emit(
            _("Loading playlist: {title}").format(
                title=playlist.title or _("Untitled")
            )
        )
        try:
            if self.player.primary_instance is not None:
                try:
                    self.player.primary_instance.release()
                    self.player._primary_instance = None
                except Exception as e:
                    pass
            self.player.stop_playlist()
            self._loading = True
            self.player.load_playlist(playlist, auto_play=True, start_index = start_index)
            #self.player._play_playlist_track()
            self._load_subtitles_for_current_track()
            self._update_current_file()
            self._update_player_state()
        except Exception as e:
            self._reset_ui_to_default()
        finally:
            self._loading = False

    def change_path(self, path: str):
        if not path: return

        try:
            if av_play.is_url(path):
                self.player_controls._source_url = path
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
        
    @Slot()
    def _on_url_extraction_started(self):
        self.video_display.show_loading(_("Extracting URL..."))
        self.player_controls.set_controls_enabled(False)
        signal_manager.statusbar_message.emit(_("Extracting URL..."))

    @Slot(object)
    def _on_url_extraction_complete(self, _result):
        self.video_display.hide_loading()
        self.player_controls.set_controls_enabled(True)
        self._load_subtitles_for_current_track()
        self._update_current_file()
        self._update_player_state()

    @Slot(str)
    def _on_url_extraction_failed(self, error_msg):
        logger.error(f"URL extraction failed: {error_msg}")
        self.video_display.hide_loading()
        self.player_controls.set_controls_enabled(True)
        self._reset_ui_to_default()
        signal_manager.statusbar_message.emit(_("URL extraction failed"))

        msg = QMessageBox(self)
        msg.setWindowTitle(_("URL Extraction Failed"))
        msg.setText(_("Failed to extract URL:\n{error}").format(error=error_msg))
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.exec()

    def set_shortcuts(self):
        hotkeys = key_config.key_config["Player"]
        
        shortcuts: Dict[str, Callable] = {
            hotkeys["Play/Pause"]: lambda: self._call_if_enabled(self.player_controls.play_pause_btn, self.player_controls.playPauseClicked.emit),
            hotkeys["Backward"]: lambda: self._call_if_enabled(self.player_controls.backward_btn, self.player_controls.backwardClicked.emit),
            hotkeys["Forward"]: lambda: self._call_if_enabled(self.player_controls.forward_btn, self.player_controls.forwardClicked.emit),
            hotkeys["Stop"]: lambda: self._call_if_media(self.player_controls.stopRequested.emit),
            hotkeys["Mute/Unmute"]: lambda: self._call_if_enabled(self.player_controls.mute_btn, self.player_controls.muteUnmuteClicked.emit),
            hotkeys["Previous"]: lambda: self._call_if_enabled(self.player_controls.previous_btn, self.player_controls.previousClicked.emit),
            hotkeys["Next"]: lambda: self._call_if_enabled(self.player_controls.next_btn, self.player_controls.nextClicked.emit),
            hotkeys["Jump to beginning"]: lambda: self._call_if_enabled(self.player_controls.seek_slider, self.player_controls.jumpToBeginningRequested.emit),
            hotkeys["Jump to the end"]: lambda: self._call_if_enabled(self.player_controls.seek_slider, self.player_controls.jumpToEndRequested.emit),
            hotkeys["Toggle repeat"]: lambda: self._call_if_enabled(self.player_controls.repeat_btn, self.player_controls.repeatClicked.emit),
            hotkeys["Volume up"]: lambda: self._call_if_enabled(self.player_controls.volume_slider, self.player_controls.volume_up),
            hotkeys["Volume down"]: lambda: self._call_if_enabled(self.player_controls.volume_slider, self.player_controls.volume_down),
            hotkeys["Bookmarks list"]: lambda: self.player_controls.show_bookmarks_dialog(),
            hotkeys["New mark at current position"]: lambda: self.player_controls.add_bookmark_at_current_position(),
            hotkeys["Repeat loop start"]: lambda: self._on_repeat_start_shortcut(),
            hotkeys["Repeat loop end"]: lambda: self._on_repeat_end_shortcut(),
            hotkeys["Clear repeat loop"]: lambda: self.player_controls.clear_repeat_loop(),
            hotkeys["Take snapshot"]: lambda: self._call_if_media(self.player_controls.screenshotRequested.emit),
            hotkeys["Delete current bookmark"]: lambda: self.player_controls.delete_current_bookmark(),
            hotkeys["Fullscreen"]: lambda: self.player_controls.fullscreenToggled.emit(True),
            hotkeys["Exit fullscreen"]: lambda: self.player_controls.fullscreenToggled.emit(False),
            hotkeys["Previous bookmark"]: lambda: self.player_controls.jump_to_previous_bookmark(),
            hotkeys["Next bookmark"]: lambda: self.player_controls.jump_to_next_bookmark(),
            hotkeys["Previous repeat loop"]: lambda: self.player_controls.jump_to_previous_loop(),
            hotkeys["Next repeat loop"]: lambda: self.player_controls.jump_to_next_loop(),
            hotkeys["Mark1 position"]: lambda: self.player_controls.jump_to_mark(0),
            hotkeys["Mark2 position"]: lambda: self.player_controls.jump_to_mark(1),
            hotkeys["Mark3 position"]: lambda: self.player_controls.jump_to_mark(2),
            hotkeys["Mark4 position"]: lambda: self.player_controls.jump_to_mark(3),
            hotkeys["Mark5 position"]: lambda: self.player_controls.jump_to_mark(4),
            hotkeys["Mark6 position"]: lambda: self.player_controls.jump_to_mark(5),
            hotkeys["Mark7 position"]: lambda: self.player_controls.jump_to_mark(6),
            hotkeys["Mark8 position"]: lambda: self.player_controls.jump_to_mark(7),
            hotkeys["Mark9 position"]: lambda: self.player_controls.jump_to_mark(8),
            hotkeys["Mark10 position"]: lambda: self.player_controls.jump_to_mark(9),
            hotkeys["close media"]: lambda: self.close_current_media()
        }
        
        for shortcut in self._shortcuts.values():
            shortcut.activated.disconnect()
            shortcut.setParent(None)
        self._shortcuts.clear()

        for shortcut, callback in shortcuts.items():
            sh = QShortcut(shortcut, self)
            sh.activated.connect(callback)
            sh.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self._shortcuts[shortcut] = sh

    def reset_shortcuts(self):
        pass

    def _on_repeat_start_shortcut(self):
        try:
            pos = None
            if hasattr(self, 'player') and self.player and self.player.primary_instance is not None:
                try:
                    pos = float(self.player.primary_instance.get_position())
                except Exception:
                    pos = None
            if pos is None:
                pos = float(self.player_controls.get_seek_position())
            self.player_controls.set_loop_start_precise(pos)
        except Exception:
            pass

    def _on_repeat_end_shortcut(self):
        try:
            pos = None
            if hasattr(self, 'player') and self.player and self.player.primary_instance is not None:
                try:
                    pos = float(self.player.primary_instance.get_position())
                except Exception:
                    pos = None
            if pos is None:
                pos = float(self.player_controls.get_seek_position())
            self.player_controls.set_loop_end_precise(pos)
        except Exception:
            pass

    def _install_event_filters(self):
        widgets = [
            self.player_controls.previous_btn, self.player_controls.backward_btn, self.player_controls.play_pause_btn, 
            self.player_controls.forward_btn, self.player_controls.next_btn, self.player_controls.repeat_btn, self.player_controls.shuffle_btn,
            self.player_controls.bookmarks_btn, self.player_controls.screenshot_btn,
            self.player_controls.seek_slider, self.player_controls.mute_btn, self.player_controls.volume_slider,
            self.player_controls.time_label, self.player_controls.current_track_label, self.player_controls.more_btn,
            self.player_controls.toggle_controls_btn
        ]
        self._key_event_filter.install_on_widgets(widgets)

    def show_youtube_info_dialog(self):

        current_file = self.player_controls._source_url or self.player_controls._current_file
        if not current_file:
            return
        
        from utilities.functions import is_youtube_url
        if not is_youtube_url(current_file):
            return
        
        from gui.dialogs.youtube_info_dialog import YouTubeInfoDialog
        
        cached = self._youtube_info_cache.get(current_file)
        dialog = YouTubeInfoDialog(current_file, parent=self.window(), cached_info=cached)
        dialog.exec()
        
        if dialog.cached_info and current_file not in self._youtube_info_cache:
            self._cache_youtube_info(current_file, dialog.cached_info)
    
    def _cache_youtube_info(self, url: str, info: dict):

        self._youtube_info_cache[url] = info

    def closeEvent(self, event):
        try:
            self._youtube_info_cache.clear()
            
            self.player_controls.save_last_position()
            if self.player.primary_instance is not None:
                try:
                    self.player.primary_instance.release()
                except Exception:
                    pass
            self.player.release()
        except Exception:
            pass
        super().closeEvent(event)
