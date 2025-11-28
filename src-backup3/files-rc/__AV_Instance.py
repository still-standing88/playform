import random
import os

from .media_info import MediaInfo
from .__AV_Interface import AVMediaInterface
from .__AV_Common import *


class AVMediaInstance:


    def __init__(self, controler:AVMediaInterface, file_path:str = ""):
        self.__controler = controler
        self.__media_type = self.__controler.type
        self.__media_backend = self.__controler.backend
        self.__media_source:AVMediaSource = AVMediaSource.AV_SRC_NOT_SET
        self.__file_path = file_path
        self.__id:int = random.randint(1000000, 9999999)
        self.__filters:dict[int, AVFilter] = {}


    @property
    def media_type(self):
        return self.__media_type

    @property
    def media_backend(self):
        return self.__media_backend

    @property
    def media_source(self):
        return self.__media_source

    @property
    def instance_id(self):
        return self.__id

    @property
    def file_path(self):
        return self.__file_path


    # Media control methods
    def load_file(self, file_path:str):
        #if self.get_playback_state() == AVPlaybackState.AV_STATE_PLAYING:
            #self.stop()
        if file_path != "" and is_path(file_path) and os.path.exists(file_path):
            self.__file_path = file_path
            self.__controler.load_file(self.__id, file_path)

    def load_url(self, url:str):
        if self.get_playback_state() == AVPlaybackState.AV_STATE_PLAYING:
            self.stop()
        if url != "" and is_url(url):
            self.__file_path = url
            self.__controler.load_url(self.__id, url)

    def play(self):
        self.__controler.play(self.__id)

    def pause(self):
        self.__controler.pause(self.__id)

    def stop(self):
        self.__controler.stop(self.__id)

    def mute(self):
        self.__controler.mute(self.__id)

    def unmute(self):
        self.__controler.unmute(self.__id)

    def set_position(self, position:int):
        self.__controler.set_position(self.__id, position)

    def set_volume(self, offset:float):
        self.__controler.set_volume(self.__id, offset)

    def set_loop(self, loop:bool):
        self.__controler.set_loop(self.__id, loop)

    def get_length(self) -> int:
        return self.__controler.get_length(self.__id, )

    def get_position(self) -> int:
        return self.__controler.get_position(self.__id, )

    def get_volume(self) -> float:
        return self.__controler.get_volume(self.__id, )

    def get_playback_state(self) -> AVPlaybackState:
        return self.__controler.get_play_state(self.__id, )

    def get_mute_state(self) -> AVMuteState:
        return self.__controler.get_mute_state(self.__id, )

    # Effects/filters
    def apply_filter(self, filter:AVFilter) -> int:
        if filter.type != self.media_type and filter.backend != self.media_backend:
            return -1
        filter_id = random.randint(1000000, 9999999)
        self.__filters[filter_id] = filter
        self.__controler.apply_filter(self.__id, filter_id, filter)
        return filter_id

    def remove_filter(self, filter_id:int):
        if filter_id in self.__filters:
            self.__filters.pop(filter_id)
            self.__controler.remove_filter(self.__id, filter_id )

    def remove_filters(self):

        for filter_id in list(self.__filters.keys()):
            try:
                self.remove_filter(filter_id)
            except:
                if filter_id in self.__filters:
                    self.__filters.pop(filter_id)

    def set_parameter(self, filter_id:int, parameter_name:str, parameter_value:ParameterValue):
        if filter_id in self.__filters and parameter_name in self.__filters[filter_id].get_parameters():
            self.__controler.set_parameter(self.__id, filter_id, parameter_name, parameter_value)

    def get_parameter(self, filter_id:int, parameter_name:str) -> ParameterValue | None:
        if filter_id in self.__filters and parameter_name in self.__filters[filter_id].get_parameters():
            return self.__controler.get_parameter(self.__id, filter_id, parameter_name)
        return None

    def release(self):

        try:
            if self.get_playback_state() == AVPlaybackState.AV_STATE_PLAYING:
                self.stop()
        except:
            pass
        

        try:
            self.remove_filters()
        except:
            pass
        

        try:
            self.__controler.release(self.__id)
        except:
            pass

    def media_info(self) -> Any:
        return MediaInfo(self.__file_path)
