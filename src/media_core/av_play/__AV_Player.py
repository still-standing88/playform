from abc import ABC, abstractmethod
from .__AV_Common import *
from .__AV_Instance import AVMediaInstance
from .__AV_Interface import AVMediaInterface
from .playlist import Playlist
import threading
import time
import random
from typing import List, Optional, Callable


class AVPlayer(ABC):

    # The backend reports AV_STATE_NOTHING both for "this file reached EOF"
    # (the case _monitor_playback wants to act on) and, transiently, for "a
    # new file was just requested but mpv hasn't started it yet" (loadfile is
    # fire-and-forget). Without this grace window, that transient loading
    # state looks identical to "track ended" and triggers a second, spurious
    # _advance_track() on top of whatever navigation just happened.
    LOAD_GRACE_PERIOD = 3.0

    def __init__(self, media_type:AVMediaType, media_backend:AVMediaBackend, interface:AVMediaInterface) -> None:
        super().__init__()
        # Reentrant on purpose: the public navigation entry points
        # (next/previous/jump_to_track) and the monitor thread's
        # auto-advance all take this lock and then call _advance_track(),
        # which reaches _consume_queue_head() -- which takes it again.
        # With a plain Lock that second acquire never returns, so the
        # caller's thread hangs forever still holding it: next() froze the
        # GUI thread outright, and the monitor thread deadlocking on the
        # first track end left the lock permanently held, so every later
        # previous()/next()/queue call froze the GUI too.
        self._advance_lock = threading.RLock()
        self._device:AVDevice | None = None
        self._media_type = media_type
        self._media_backend = media_backend
        self._controler = interface
        self._config:dict[str, Any] = {}
        self._primary_instance:AVMediaInstance|None = None
        self._current_playlist:Playlist|None = None
        self._current_playlist_index = -1
        

        self._auto_play_enabled = False
        self._playlist_repeat_mode = AVPlaylistRepeatMode.REPEAT_OFF
        self._playlist_shuffle_mode = AVPlaylistShuffleMode.SEQUENTIAL
        self._playlist_state = AVPlaylistState.STOPPED
        self._monitor_thread:threading.Thread|None = None
        self._monitor_running = False
        self._shuffle_order:List[int] = []
        self._track_end_callback:Optional[Callable[[int], None]] = None
        self._track_loading = False
        self._track_load_started_at = 0.0
        self._reverse_playback_active = False
        self._reverse_stopped_callback:Optional[Callable[[], None]] = None
        self._playback_queue:List[str] = []
        self._queue_changed_callback:Optional[Callable[[], None]] = None
        self._queue_track_active = False


    @property
    def media_type(self):
        return self._media_type

    @property
    def media_backend(self):
        return self._media_backend

    @property
    def config(self):
        return self._config

    @property
    def primary_instance(self):
            return self._primary_instance

    @property
    def current_playlist(self):
        return self._current_playlist


    def create_file_instance(self, file_path:str) -> AVMediaInstance:
        instance:AVMediaInstance = AVMediaInstance(self._controler)
        instance.load_file(file_path)
        self._primary_instance = instance
        return instance

    def create_url_instance(self, url:str) -> AVMediaInstance:
        instance:AVMediaInstance = AVMediaInstance(self._controler)
        instance.load_url(url)
        return instance

    def set_config_value(self, name:str, value:Any):
        self._config[name] = value

    def get_config(self, name) -> Any:
        if name in self._config:
            return self._config[name]
        return None

    def load_playlist(self, playlist:Playlist, auto_play:bool = False, start_index = 0):
        if playlist is not None:
            self._current_playlist = playlist
            self._auto_play_enabled = auto_play
            self._playlist_state = AVPlaylistState.STOPPED


            if self._playlist_shuffle_mode == AVPlaylistShuffleMode.SHUFFLE:
                self._generate_shuffle_order()

            if self._primary_instance is not None:
                self._primary_instance.stop()
            else:
                self._primary_instance = AVMediaInstance(self._controler)
                
            if len(playlist) > 0:
                if playlist is not None and 0 <= start_index < len(playlist):
                    self._current_playlist_index = start_index

                if auto_play:
                    self._play_playlist_track()
                    self._start_monitor()

    def set_playlist_repeat_mode(self, mode:AVPlaylistRepeatMode):
        self._playlist_repeat_mode = mode

    def set_playlist_shuffle_mode(self, mode:AVPlaylistShuffleMode):
        self._playlist_shuffle_mode = mode
        if mode == AVPlaylistShuffleMode.SHUFFLE:
            self._generate_shuffle_order()

    def set_auto_play(self, enabled:bool):
        self._auto_play_enabled = enabled
        if enabled and self._current_playlist and len(self._current_playlist) > 0:
            self._start_monitor()
        else:
            self._stop_monitor()

    def set_track_end_callback(self, callback:Optional[Callable[[int], None]]):
        self._track_end_callback = callback

    def set_queue_changed_callback(self, callback:Optional[Callable[[], None]]):
        self._queue_changed_callback = callback

    def queue_tracks(self, locations:List[str]) -> int:
        added = 0
        with self._advance_lock:
            for location in locations:
                if location:
                    self._playback_queue.append(location)
                    added += 1
        if added and self._queue_changed_callback:
            self._queue_changed_callback()
        return added

    def insert_queue_next(self, location:str) -> bool:
        if not location:
            return False
        with self._advance_lock:
            self._playback_queue.insert(0, location)
        if self._queue_changed_callback:
            self._queue_changed_callback()
        return True

    def get_queue(self) -> List[str]:
        with self._advance_lock:
            return list(self._playback_queue)

    def remove_from_queue(self, index:int) -> bool:
        with self._advance_lock:
            if 0 <= index < len(self._playback_queue):
                del self._playback_queue[index]
                removed = True
            else:
                removed = False
        if removed and self._queue_changed_callback:
            self._queue_changed_callback()
        return removed

    def clear_queue(self):
        with self._advance_lock:
            had_items = len(self._playback_queue) > 0
            self._playback_queue.clear()
        if had_items and self._queue_changed_callback:
            self._queue_changed_callback()

    def is_queue_track_active(self) -> bool:
        return self._queue_track_active

    def _consume_queue_head(self) -> Optional[str]:
        with self._advance_lock:
            if self._playback_queue:
                return self._playback_queue.pop(0)
        return None

    def _play_queue_track(self, location:str):
        if self._primary_instance is None:
            self._primary_instance = AVMediaInstance(self._controler)
        self._track_loading = True
        self._track_load_started_at = time.monotonic()
        self._queue_track_active = True
        if is_path(location):
            self._primary_instance.load_file(location)
        else:
            self._primary_instance.load_url(location)
        self._primary_instance.play()
        self._playlist_state = AVPlaylistState.PLAYING

    def set_reverse_stopped_callback(self, callback:Optional[Callable[[], None]]):
        self._reverse_stopped_callback = callback

    def is_reverse_playback_active(self) -> bool:
        return self._reverse_playback_active

    def get_playlist_state(self) -> AVPlaylistState:
        return self._playlist_state

    def get_playlist_repeat_mode(self) -> AVPlaylistRepeatMode:
        return self._playlist_repeat_mode

    def get_playlist_shuffle_mode(self) -> AVPlaylistShuffleMode:
        return self._playlist_shuffle_mode

    def is_auto_play_enabled(self) -> bool:
        return self._auto_play_enabled

    def get_current_track_index(self) -> int:
        return self._current_playlist_index

    def previous(self):
        with self._advance_lock:
            if self._current_playlist is not None and len(self._current_playlist) > 0:
                if self._playlist_shuffle_mode == AVPlaylistShuffleMode.SHUFFLE:
                    try:
                        current_shuffle_pos = self._shuffle_order.index(self._current_playlist_index)
                    except ValueError:
                        current_shuffle_pos = 0
                    current_shuffle_pos = max(0, current_shuffle_pos - 1)
                    self._current_playlist_index = self._shuffle_order[current_shuffle_pos]
                else:
                    self._current_playlist_index = max(0, self._current_playlist_index - 1)
                self._play_playlist_track()

    def next(self):
        with self._advance_lock:
            if self._current_playlist is not None and len(self._current_playlist) > 0:
                self._advance_track()

    def stop_playlist(self):
        if self._primary_instance:
            self._primary_instance.stop()
        self._playlist_state = AVPlaylistState.STOPPED
        self._stop_monitor()

    def pause_playlist(self):
        if self._primary_instance:
            self._primary_instance.pause()
        self._playlist_state = AVPlaylistState.PAUSED

    def resume_playlist(self):
        if self._primary_instance:
            self._primary_instance.play()
        self._playlist_state = AVPlaylistState.PLAYING
        if self._auto_play_enabled:
            self._start_monitor()

    def jump_to_track(self, index: int):
        with self._advance_lock:
            if self._current_playlist is not None and 0 <= index < len(self._current_playlist):
                self._current_playlist_index = index
                self._play_playlist_track()
                return True
            return False

    def _generate_shuffle_order(self):
        if self._current_playlist:
            self._shuffle_order = list(range(len(self._current_playlist)))
            random.shuffle(self._shuffle_order)

    def _advance_track(self):
        queued = self._consume_queue_head()
        if queued is not None:
            self._play_queue_track(queued)
            return

        self._queue_track_active = False
        if not self._current_playlist or len(self._current_playlist) == 0:
            return

        if self._playlist_repeat_mode == AVPlaylistRepeatMode.REPEAT_ONE:
            pass

        elif self._playlist_shuffle_mode == AVPlaylistShuffleMode.SHUFFLE:
            try:
                current_shuffle_pos = self._shuffle_order.index(self._current_playlist_index)
                current_shuffle_pos += 1
                if current_shuffle_pos >= len(self._shuffle_order):
                    if self._playlist_repeat_mode == AVPlaylistRepeatMode.REPEAT_ALL:
                        current_shuffle_pos = 0
                    else:
                        self._playlist_state = AVPlaylistState.FINISHED
                        return
                self._current_playlist_index = self._shuffle_order[current_shuffle_pos]
            except ValueError:
                self._current_playlist_index = self._shuffle_order[0] if self._shuffle_order else 0
        else:

            next_index = self._current_playlist_index + 1
            if next_index >= len(self._current_playlist):
                if self._playlist_repeat_mode == AVPlaylistRepeatMode.REPEAT_ALL:
                    self._current_playlist_index = 0
                else:
                    # Stay clamped on the last track instead of leaving the
                    # index stranded past the end -- otherwise repeated
                    # next() presses at the end of a non-repeating playlist
                    # silently drift the index out of bounds (with no
                    # audible change each time), and it then takes that many
                    # previous() presses just to walk back into valid range,
                    # landing on the wrong track.
                    self._current_playlist_index = len(self._current_playlist) - 1
                    self._playlist_state = AVPlaylistState.FINISHED
                    return
            else:
                self._current_playlist_index = next_index

        self._play_playlist_track()

    def _start_monitor(self):
        if not self._monitor_running:
            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self._monitor_thread.start()

    def _stop_monitor(self):
        # Must never block: this is reachable directly from GUI event
        # handlers (PlayerWidget.load_file -> stop_playlist -> here) on the
        # Qt main thread. A synchronous join() here freezes the entire
        # event loop -- including window-message pumping -- for up to its
        # timeout on every file open, while GPU-rendered video may be
        # actively live. That's exactly the kind of main-thread stall that
        # trips driver-level TDR/access-violation behavior, independent of
        # anything else in this codebase. The monitor is a daemon thread
        # that notices _monitor_running=False and exits on its own within
        # one poll iteration; any command it issues in that brief window
        # is safely rejected/no-op'd by the interface layer (generation
        # fencing, _check_initialized) rather than reaching a torn-down
        # backend.
        self._monitor_running = False

    def _is_track_loading(self) -> bool:
        """Whether a track request is still in flight, so the monitor should
        read an idle backend as "not started yet" rather than "ended".
        Subclasses that add their own pre-playback work (e.g. resolving a
        stream URL before the file even reaches mpv) override this to cover
        that window too."""
        return (self._track_loading and
                (time.monotonic() - self._track_load_started_at) < self.LOAD_GRACE_PERIOD)

    def _monitor_playback(self):
        while self._monitor_running and self._auto_play_enabled:
            try:
                if self._primary_instance:
                    state = self._primary_instance.get_playback_state()

                    if state == AVPlaybackState.AV_STATE_PLAYING:
                        self._playlist_state = AVPlaylistState.PLAYING
                        self._track_loading = False

                    elif state in [AVPlaybackState.AV_STATE_STOPPED, AVPlaybackState.AV_STATE_NOTHING]:
                        still_loading = self._is_track_loading()
                        if self._playlist_state == AVPlaylistState.PLAYING and not still_loading:
                            if self._reverse_playback_active:
                                # Idle here means playing backward ran off
                                # the *start* of the track, not the end --
                                # advancing the playlist forward would be
                                # exactly the wrong direction. Stop
                                # reversing and let the concrete player
                                # (via the callback) put mpv back in a
                                # normal, resumable forward state instead
                                # of skipping to a different track.
                                with self._advance_lock:
                                    self._reverse_playback_active = False
                                    self._playlist_state = AVPlaylistState.PAUSED
                                    if self._reverse_stopped_callback:
                                        self._reverse_stopped_callback()
                            else:
                                with self._advance_lock:
                                    self._advance_track()
                                    # Fire with the *new* current index (post-advance),
                                    # not the one that just ended -- and only if it's
                                    # still a valid track (advancing past the end of a
                                    # non-repeating playlist leaves no "now playing"
                                    # track to report). A queue-sourced advance leaves
                                    # the playlist index untouched, so the callback is
                                    # suppressed there and PlayerWidget learns of the
                                    # change through its queue signal instead.
                                    if (self._track_end_callback and not self._queue_track_active
                                            and self._current_playlist is not None
                                            and 0 <= self._current_playlist_index < len(self._current_playlist)):
                                        self._track_end_callback(self._current_playlist_index)

                time.sleep(0.1)

            except Exception as e:
                time.sleep(0.3)

    def _play_playlist_track(self):
        if self._primary_instance is None:
            self._primary_instance = AVMediaInstance(self._controler)
        
        if self._current_playlist and 0 <= self._current_playlist_index < len(self._current_playlist):
            instance_path = self._current_playlist.entries[self._current_playlist_index].location
            self._track_loading = True
            self._track_load_started_at = time.monotonic()
            if is_path(instance_path):
                self._primary_instance.load_file(instance_path)
            else:
                self._primary_instance.load_url(instance_path)
            self._primary_instance.play()
            self._playlist_state = AVPlaylistState.PLAYING


    @abstractmethod
    def init(self, *args, **kw):
        pass

    @abstractmethod
    def release(self):

        self._stop_monitor()
        pass

    def set_device(self, index:int):
        device_count:int  = self._controler.get_devices()
        if index < device_count and index >= 0:
            self._controler.set_device(index)
            self._device = self._controler.get_device_info(index)
        else:
            raise IndexError

    def get_device(self, index:int) -> AVDevice | None:
        device_count:int  = self._controler.get_devices()
        if index < device_count and index >= 0:
            return self._controler.get_device_info(index)
        else:
            raise IndexError

    def get_devices(self) -> int:
        return self._controler.get_devices()

    def get_current_device(self) -> int:
        return self._controler.get_current_device()


