import os
import datetime as dt
import time
import logging
from typing import Optional, Dict
import utilities.mpv_bootstrap
import media_core.av_play as av_play

from PySide6.QtWidgets import (QWidget, QLayout, QVBoxLayout, QHBoxLayout, QSplitter,
                               QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSlider, QSpinBox,
                               QScrollArea, QFrame)
from PySide6.QtGui import QCloseEvent, QFont, QPalette, QColor, QShortcut
from PySide6.QtCore import Qt, Signal, QTimer, QSize, Slot

from app_config import prefs
from .player_controls import PlayerControls
from .widgets.subtitles_widget import SubtitlesWidget
from .widgets.video_display_widget import VideoDisplayWidget
from .timeline import SegmentTimelineWidget
from gui_controls.player_key_event_filter import KeyEventFilter
from gui_controls.toggle_button import ToggleButton
from gui_controls.accordion import Accordion
from .core.subtitles import SubtitleManager
from .widgets.filters_widget import FiltersWidget
from .widgets.video_effects_widget import VideoEffectsWidget
from .widgets.chapters_widget import ChaptersWidget
from .widgets.equalizer_widget import EqualizerWidget
from .widgets.audio_filters_widget import AudioFiltersWidget
from .core.lazy_playlist_player import LazyPlaylistPlayer
from .core.player_init import init_mpv_player
from .core.player_shortcuts import PlayerShortcuts
from .core.timeline_sync import TimelineSyncController
from .core.track_metadata_loader import TrackMetadataLoader
from .core.track_info_dialogs import TrackInfoDialogs
from app_constance.styles import PLAYER_WIDGET_STYLE

from utilities.functions import get_app_path, get_parent_dir
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
    currentTrackIndexChanged = Signal(int)
    _trackEndedFromMonitor = Signal(int)
    _reverseStoppedFromMonitor = Signal()
    _fileLoadedFromMpv = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Stored explicitly because a dock's content widget gets reparented
        # internally by Qt (and again if the dock is later floated), so
        # self.window() no longer reliably resolves back to MainWindow.
        self._main_window = parent
        self.is_seeking = False
        self._last_known_state = av_play.AVPlaybackState.AV_STATE_NOTHING
        self._last_muted: Optional[bool] = None
        self._had_media = False
        self._shortcuts:Dict[str, QShortcut] = {}
        self._key_event_filter = KeyEventFilter(self)
        self._last_subtitle_text: Optional[str] = None

        self._shortcuts_ctrl = PlayerShortcuts(self)
        self._timeline_sync = TimelineSyncController(self)
        self._track_loader = TrackMetadataLoader(self)
        self._info_dialogs = TrackInfoDialogs(self)

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
        self.video_effects_widget = VideoEffectsWidget(self)
        self.chapters_widget = ChaptersWidget(self)
        self.equalizer_widget = EqualizerWidget(self)
        self.audio_filters_widget = AudioFiltersWidget(self)
        self.side_accordion = Accordion(self)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Placed directly above the accordion it hides, rather than in the
        # far-away playback controls row - the button and the panel it
        # affects should be visually next to each other.
        self.toggle_accordion_btn = ToggleButton(_("Hide Side Panel"), self)
        self.toggle_accordion_btn.setFixedHeight(30)
        self.toggle_accordion_btn.setToolTip(_("Hide/Show Side Panel"))


        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_path_context_menu)

    def layout_widgets(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        left_layout.addWidget(self.video_display, 2)
        left_layout.addWidget(self.timeline)
        left_layout.addWidget(self.player_controls)
        self.video_display.set_position_info(left_layout, 0)

        self.side_accordion.add_section(_("Chapters"), self.chapters_widget)
        self.side_accordion.add_section(_("Subtitles"), self.subtitles_widget)
        self.side_accordion.add_section(_("Equalizer"), self.equalizer_widget)
        self.side_accordion.add_section(_("Color Adjustments"), self.filters_widget)
        self.side_accordion.add_section(_("Video Effects"), self.video_effects_widget)
        self.side_accordion.add_section(_("Audio Filters"), self.audio_filters_widget)

        # The accordion has no bounded height of its own - with several
        # sections' content stacked open, its total height can exceed the
        # dock's available space, silently pushing whatever's open (e.g.
        # Audio Filters, the last section) below the visible area with no
        # way to reach it. A scroll area bounds it instead of letting it
        # overflow the player container.
        self.accordion_scroll = QScrollArea(self)
        self.accordion_scroll.setWidget(self.side_accordion)
        self.accordion_scroll.setWidgetResizable(True)
        self.accordion_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.accordion_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # A floor on its own height still matters even as a side pane -
        # main_splitter gives every pane the full row height, but that row
        # height is itself bounded below by the tallest pane's minimum, so
        # this still competes for vertical space if it's ever the biggest
        # minimum in the row (same reasoning as before, just no longer
        # needing to *also* stack on top of the video/timeline/controls
        # column, which was the actual source of the combined-minimum
        # overflow this floor was originally added to guard against).
        self.accordion_scroll.setMinimumHeight(self.IDEAL_ACCORDION_FLOOR)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        accordion_header_layout = QHBoxLayout()
        accordion_header_layout.setContentsMargins(0, 0, 0, 0)
        accordion_header_layout.addStretch()
        accordion_header_layout.addWidget(self.toggle_accordion_btn)

        right_layout.addLayout(accordion_header_layout, 0)
        right_layout.setAlignment(accordion_header_layout, Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(self.accordion_scroll, 1)

        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(right_widget)

        # side_accordion used to be stacked below video/timeline/controls
        # in left_layout instead of here - main_splitter (already set up
        # for exactly this, right down to sizes/stretch factors for two
        # panes) just never got a second widget added to it. Putting the
        # accordion here instead means it competes with video for *width*,
        # which this app generally has more of to spare than height, rather
        # than adding its own height on top of everything else in the
        # column below it - the actual reason the combined minimum height
        # could exceed a small screen in the first place.
        self.main_splitter.setSizes([800, 300])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setCollapsible(1, True)

        self.main_layout.addWidget(self.main_splitter)

    def _init_player(self):
        init_mpv_player(self)

    def connect_signals(self):
        # The AVPlayer playlist monitor invokes the track-end callback from its
        # own background thread; routing it through a Qt signal instead of
        # calling _update_current_track directly marshals the widget updates
        # onto the GUI thread via Qt's queued cross-thread delivery.
        self._trackEndedFromMonitor.connect(self._update_current_track)
        self._reverseStoppedFromMonitor.connect(self._on_reverse_stopped_from_monitor)
        self._fileLoadedFromMpv.connect(self.seek_to_last)

        self.toggle_accordion_btn.actuated.connect(self._on_accordion_panel_toggled)
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
        self.timeline.segmentAdded.connect(self._timeline_sync.on_segment_added)
        self.timeline.segmentUpdated.connect(self._timeline_sync.on_segment_updated)
        self.timeline.segmentRemoved.connect(self._timeline_sync.on_segment_removed)
        self.timeline.segmentSelected.connect(self._timeline_sync.on_segment_selected)
        self.timeline.markerAdded.connect(self._timeline_sync.on_marker_added)
        self.timeline.markerMoved.connect(self._timeline_sync.on_marker_moved)
        self.timeline.markerRemoved.connect(self._timeline_sync.on_marker_removed)
        self.timeline.markerSelected.connect(self._timeline_sync.on_marker_selected)
        self.player_controls.aspectRatioChanged.connect(self._on_aspect_ratio_changed)
        self.player_controls.scaleChanged.connect(self._on_scale_changed)
        self.player_controls.rotateChanged.connect(self._on_rotate_changed)
        self.player_controls.flipHorizontalToggled.connect(self._on_flip_horizontal_toggled)
        self.player_controls.flipVerticalToggled.connect(self._on_flip_vertical_toggled)
        self.player_controls.screenshotRequested.connect(self._on_screenshot)
        self.player_controls.reverseToggled.connect(self._on_reverse_toggled)
        self.player.signals.extraction_started.connect(self._on_url_extraction_started)
        self.player.signals.extraction_complete.connect(self._on_url_extraction_complete)
        self.player.signals.extraction_failed.connect(self._on_url_extraction_failed)
        self.chapters_widget.chapterActivated.connect(self._track_loader.on_chapter_activated)
        self.subtitles_widget.languageSelected.connect(self._track_loader.on_subtitle_language_selected)

    def apply_styles(self):
        self.setStyleSheet(PLAYER_WIDGET_STYLE)

    @Slot(bool)
    def _on_accordion_panel_toggled(self, hidden):
        self.accordion_scroll.setVisible(not hidden)
        if hidden:
            self.toggle_accordion_btn.setText(_("Show Side Panel"))
            self.toggle_accordion_btn.setToolTip(_("Show Side Panel"))
        else:
            self.toggle_accordion_btn.setText(_("Hide Side Panel"))
            self.toggle_accordion_btn.setToolTip(_("Hide Side Panel"))

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
                # Any non-playing state (STOPPED, PAUSED, or NOTHING -- e.g.
                # right after a track hit EOF and mpv went idle) should
                # resume/restart playback; instance.play() already handles
                # reloading the file when the backend is idle.
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
            self._update_current_track(self.player.get_current_track_index())

    @Slot()
    def _on_next_clicked(self):
        if self.player:
            self.player.next()
            self._update_current_track(self.player.get_current_track_index())

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
                prefs.prefs["player_volume"] = volume
                prefs.save()
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, _("Volume Error"), msg)

    @Slot()
    def _on_volume_up(self):
        instance = self.player.primary_instance
        if instance:
            try:
                current_volume = instance.get_volume()
                new_volume = min(300, current_volume + prefs.prefs["offset"]["volume"])
                instance.set_volume(new_volume)
                prefs.prefs["player_volume"] = new_volume
                prefs.save()
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
                prefs.prefs["player_volume"] = new_volume
                prefs.save()
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

    @Slot(int)
    def _on_rotate_changed(self, degrees: int):
        self.player.set_video_rotate(degrees)

    @Slot(bool)
    def _on_flip_horizontal_toggled(self, enabled: bool):
        self.player.set_flip_horizontal(enabled)

    @Slot(bool)
    def _on_flip_vertical_toggled(self, enabled: bool):
        self.player.set_flip_vertical(enabled)

    @Slot(bool)
    def _on_fullscreen_toggled(self, enabled):
        self.video_display.set_fullscreen(enabled)
        try:
            self.player.set_fullscreen(enabled)
        except Exception:
            pass

    def _on_reverse_toggled(self, enabled):
        if self.player:
            try:
                self.player.set_reverse_playback(enabled)
            except Exception:
                pass

    def _on_reverse_stopped_from_monitor(self):
        # The monitor thread (AVPlayer._monitor_playback, background
        # thread) noticed reverse playback ran off the start of the track
        # and cleared its own bookkeeping flag, but it doesn't touch mpv
        # directly (that's backend-specific and stays out of the
        # backend-agnostic base class) -- set_reverse_playback(False) here
        # actually flips play-direction back to forward and does the
        # recovery re-seek. sync_reverse_state just updates the checkbox
        # without re-emitting reverseToggled (which would loop back here).
        if self.player:
            try:
                self.player.set_reverse_playback(False)
            except Exception:
                pass
        self.player_controls.sync_reverse_state(False)

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
        current_file = self.player_controls._current_file
        if not current_file:
            return
        menu = self.player_controls.build_path_context_menu(self)
        menu.exec(self.mapToGlobal(position))

    def _update_media_player_data(self):
        self.player_controls.load_bookmarks()
        self.player_controls.load_last_positions()
        self.player_controls.load_repeat_loops()
        try:
            self._timeline_sync.update_timeline_from_data()
        except Exception:
            pass

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
                    self._track_loader.load_subtitles_for_current_track()
                    self.filters_widget.reset_filters()
                    self.video_effects_widget.reset_effects()
                    self.currentTrackIndexChanged.emit(index)
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
                self._track_loader.load_subtitles_for_current_track()
                self.filters_widget.reset_filters()
                self.video_effects_widget.reset_effects()
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
            try:
                audio_only = self.player.is_audio_only()
                self.player_controls.set_reverse_available(audio_only)
                self.player_controls.set_video_available(not audio_only)
            except Exception:
                pass
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

    def seek_to_last(self):
        # Connected to _fileLoadedFromMpv, emitted from mpv's own
        # 'file-loaded' event (see player_init.py) -- not called right after
        # issuing load_playlist()/load_file() anymore. loadfile is
        # fire-and-forget, so seeking immediately after requesting it races
        # mpv actually opening the file; file-loaded is mpv's own signal
        # that the file is ready to seek in.
        instance = self.player.primary_instance
        if not instance:
            return

        try:
            self.player_controls.load_last_position()
            if self.player_controls.last_position and self.player_controls.last_position > 0:
                instance.set_position(self.player_controls.last_position)
        except av_play.AVError:
            pass

    def _reset_ui_to_default(self):
        self.player_controls.set_current_track(_("No media loaded"))
        self.player_controls.set_time_text("00:00 / 00:00")
        self.player_controls.set_seek_range(0, 100)
        self.player_controls.set_seek_position(0)
        self.player_controls.set_play_pause_state(False)
        self.player_controls.set_controls_enabled(False)
        self.subtitles_widget.clear_subtitles()
        self.filters_widget.reset_filters()
        self.video_effects_widget.reset_effects()
        self.chapters_widget.clear_chapters()

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
            # stop_playlist() must run first -- it stops the AVPlayer monitor
            # thread. Releasing primary_instance before that let the monitor
            # keep polling/loading against an instance mid-teardown.
            self.player.stop_playlist()
            if self.player.primary_instance is not None:
                try:
                    self.player.primary_instance.release()
                    self.player._primary_instance = None
                except Exception as e:
                    pass
            self._loading = True
            self.player.load_playlist(playlist, auto_play=True, start_index = start_index)
            #self.player._play_playlist_track()
            self._track_loader.load_subtitles_for_current_track()
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

    # Recomputed fresh on every clamp_to_screen() pass (see DockManager) -
    # never mutated cumulatively, so plugging into a bigger screen restores
    # the full, comfortable floor rather than leaving it permanently shrunk
    # from whatever the smallest screen ever seen last demanded.
    IDEAL_ACCORDION_FLOOR = 170
    MIN_ACCORDION_FLOOR = 0

    def set_accordion_floor(self, px: int):
        self.accordion_scroll.setMinimumHeight(max(self.MIN_ACCORDION_FLOOR, px))

    @Slot()
    def _on_url_extraction_started(self):
        self.video_display.show_loading(_("Extracting URL..."))
        self.player_controls.set_controls_enabled(False)
        signal_manager.statusbar_message.emit(_("Extracting URL..."))

    @Slot(object)
    def _on_url_extraction_complete(self, _result):
        self.video_display.hide_loading()
        self.player_controls.set_controls_enabled(True)
        self._track_loader.load_subtitles_for_current_track()
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
        self._shortcuts_ctrl.setup()

    def reset_shortcuts(self):
        pass

    def _install_event_filters(self):
        self._shortcuts_ctrl.install_event_filters()

    def show_youtube_info_dialog(self):
        self._info_dialogs.show_youtube_info_dialog()

    def download_subtitle_file(self):
        self._info_dialogs.download_subtitle_file()

    def view_youtube_comments(self):
        self._info_dialogs.view_youtube_comments()

    def view_media_metadata(self):
        self._info_dialogs.view_media_metadata()

    def closeEvent(self, event):
        try:
            self._track_loader.cleanup()
            self._info_dialogs.cleanup()

            self.player_controls.save_last_position()
            # player.release() stops the AVPlayer monitor thread before
            # releasing primary_instance and tearing down MPV -- releasing
            # primary_instance separately first raced the still-running
            # monitor against a half-torn-down instance.
            self.player.release()
        except Exception:
            pass
        super().closeEvent(event)
