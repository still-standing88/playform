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


    def __init__(self, media_type:AVMediaType, media_backend:AVMediaBackend, interface:AVMediaInterface) -> None:
        super().__init__()
        self._advance_lock = threading.Lock()
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
        if self._current_playlist is not None and len(self._current_playlist) > 0:
            if self._playlist_shuffle_mode == AVPlaylistShuffleMode.SHUFFLE:
                current_shuffle_pos = self._shuffle_order.index(self._current_playlist_index)
                current_shuffle_pos = max(0, current_shuffle_pos - 1)
                self._current_playlist_index = self._shuffle_order[current_shuffle_pos]
            else:
                self._current_playlist_index = max(0, self._current_playlist_index - 1)
            self._play_playlist_track()

    def next(self):
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

            self._current_playlist_index += 1
            if self._current_playlist_index >= len(self._current_playlist):
                if self._playlist_repeat_mode == AVPlaylistRepeatMode.REPEAT_ALL:
                    self._current_playlist_index = 0
                else:
                    self._playlist_state = AVPlaylistState.FINISHED
                    return

        self._play_playlist_track()

    def _start_monitor(self):
        if not self._monitor_running:
            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self._monitor_thread.start()

    def _stop_monitor(self):
        self._monitor_running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)

    def _monitor_playback(self):
        while self._monitor_running and self._auto_play_enabled:
            try:
                if self._primary_instance:
                    state = self._primary_instance.get_playback_state()
                    
                    if state == AVPlaybackState.AV_STATE_PLAYING:
                        self._playlist_state = AVPlaylistState.PLAYING
                        position = self._primary_instance.get_position()
                        length = self._primary_instance.get_length()
                        
                        if length > 0 and position >= length - 1:
                            with self._advance_lock:
                                if self._track_end_callback:
                                    self._track_end_callback(self._current_playlist_index)
                                self._advance_track()
                    
                    elif state in [AVPlaybackState.AV_STATE_STOPPED, AVPlaybackState.AV_STATE_NOTHING]:
                        if self._playlist_state == AVPlaylistState.PLAYING:
                            with self._advance_lock:
                                self._advance_track()
                
                time.sleep(0.1)
            
            except Exception as e:
                time.sleep(0.3)

    def _play_playlist_track(self):
        if self._primary_instance is None:
            self._primary_instance = AVMediaInstance(self._controler)
        
        if self._current_playlist and 0 <= self._current_playlist_index < len(self._current_playlist):
            instance_path = self._current_playlist.entries[self._current_playlist_index].location
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


