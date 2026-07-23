from abc import ABC, abstractmethod
from typing import Any, List
from .__AV_Common import *


class AVMediaInterface(ABC):


    def __init__(self, media_type: AVMediaType, media_backend: AVMediaBackend) -> None:
        super().__init__()
        self.__backend = media_backend
        self.__type = media_type
        self.__devices:List[AVDevice] = []
        self.__instances:dict[int, Any] = {}
        self.__effects:dict[int, Any] = {}


    @property
    def backend(self):
        return self.__backend

    @property
    def type(self):
     return self.__type


    @abstractmethod
    def load_file(self, id:int, path:str):
        pass

    @abstractmethod
    def load_url(self, id:int, url:str):
        pass

    @abstractmethod
    def init(self, *args, **kw):
        pass

    @abstractmethod
    def free(self):
        pass

    @abstractmethod
    def release(self, id:int):
        pass

    # Playback
    @abstractmethod
    def play(self, id:int):
        pass

    @abstractmethod
    def pause(self, id:int):
        pass

    @abstractmethod
    def mute(self, id:int):
        pass

    @abstractmethod
    def unmute(self, id:int):
        pass

    @abstractmethod
    def stop(self, id:int):
        pass


    @abstractmethod
    def set_volume(self, id:int, offset:float):
        pass

    @abstractmethod
    def set_position(self, id:int, offset:int):
        pass

    @abstractmethod
    def set_loop(self, id:int, loop:bool):
        pass


        # Geters
    @abstractmethod
    def get_length(self, id:int) -> int:
        pass

    @abstractmethod
    def get_position(self, id:int) -> int:
        pass

    @abstractmethod
    def get_play_state(self, id:int) -> AVPlaybackState:
        pass

    @abstractmethod
    def get_mute_state(self, id:int) -> AVMuteState:
        pass

    @abstractmethod
    def get_volume(self, id:int) -> float:
        pass

    @abstractmethod
    def get_loop(self, id:int) -> bool:
        return False


        # Effects/filters
    @abstractmethod
    def apply_filter(self, id:int, filter_id:int, filter_struct:AVFilter):
        pass

    @abstractmethod
    def remove_filter(self, id:int, filter_id):
        pass

    @abstractmethod
    def set_parameter(self, id:int, filter_id:int, parameter_name:str, value:ParameterValue):
        pass

    @abstractmethod
    def get_parameter(self, id:int, filter_id:int, parameter_name:str) -> ParameterValue |None:
        pass

    # Device handling
    @abstractmethod
    def get_devices(self) -> int:
        pass

    @abstractmethod
    def get_device_info(self, index:int) -> AVDevice:
        pass

    @abstractmethod
    def set_device(self, index:int):
        pass

    @abstractmethod
    def get_current_device(self) -> int:
        pass

    def is_heavy_usage_period(self) -> bool:
        return False
