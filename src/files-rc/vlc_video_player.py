import vlc
import os

from typing import Dict, Any, Union, List, Callable
from .__AV_Common import *
from .__AV_Instance import AVMediaInstance
from .__AV_Interface import AVMediaInterface
from .__AV_Player import AVPlayer

def handle_vlc_error(call_func: Callable) -> Any:
    try:
        return call_func()
    except vlc.VLCException as e:
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"VLC Exception: {str(e)}")
    except AttributeError as e:
        if "vlc" in str(e).lower():
            raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER, f"VLC property not available: {str(e)}")
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Attribute error: {str(e)}")
    except RuntimeError as e:
        if "media" in str(e).lower():
            raise AVError(AVErrorInfo.FILE_NOTFOUND, f"Media loading failed: {str(e)}")
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Runtime error: {str(e)}")
    except OSError as e:
        raise AVError(AVErrorInfo.FILE_NOTFOUND, f"File error: {str(e)}")
    except TypeError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_TYPE, f"Type error: {str(e)}")
    except ValueError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_VALUE, f"Value error: {str(e)}")
    except Exception as e:
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Unknown error: {str(e)}")

class VLCMediaInterface(AVMediaInterface):
    
    def __init__(self) -> None:
        super().__init__(AVMediaType.AV_TYPE_VIDEO, AVMediaBackend.AV_BACKEND_VLC)
        self.__instances: dict[int, str] = {}
        self.__vlc_instance: vlc.Instance | None = None
        self.__media_player: vlc.MediaPlayer | None = None
        self.__current_id: int | None = None
        self.__is_initialized = False
        self.__stopped = False
        self.__end_reached = False

    def init(self, *args, **kw):
        try:
            vlc_args = kw.get("vlc_args", [])
            
            def create_instance():
                self.__vlc_instance = vlc.Instance(vlc_args)
                self.__media_player = self.__vlc_instance.media_player_new()
                
            handle_vlc_error(create_instance)
            
            self.__is_initialized = True
            self.__stopped = False
            self.__end_reached = False
            
        except Exception as e:
            raise AVError(AVErrorInfo.INITIALIZATION_ERROR, f"Failed to initialize VLC: {str(e)}")

    def free(self):
        if self.__media_player is not None:
            try:
                def stop_and_release():
                    self.__media_player.stop()
                    self.__media_player.release()
                    
                handle_vlc_error(stop_and_release)
                self.__media_player = None
                self.__vlc_instance = None
                self.__current_id = None
                self.__applied_filters.clear()
                self.__is_initialized = False
                self.__stopped = False
                self.__end_reached = False
            except Exception:
                pass

    def _check_initialized(self):
        if not self.__is_initialized or self.__vlc_instance is None or self.__media_player is None:
            raise AVError(AVErrorInfo.UNINITIALIZED, "VLC not initialized")

    def _check_instance(self, id: int):
        self._check_initialized()
        if self.__current_id != id:
            raise AVError(AVErrorInfo.INVALID_HANDLE, f"Invalid instance ID: {id}")

    def get_vlc_instance(self):
        self._check_initialized()
        return self.__vlc_instance

    def get_media_player(self):
        self._check_initialized()
        return self.__media_player

    def load_file(self, id: int, path: str):
        self._check_initialized()

        def loadfile():
            self.__vlc_instance = vlc.Instance()
            media = self.__vlc_instance.media_new(path)
            self.__media_player.set_media(media)
            
        if path and is_path(path) and os.path.exists(path):
            self.__current_id = id
            self.__instances[id] = path
            self.__stopped = False
            self.__end_reached = False
            handle_vlc_error(loadfile)

    def load_url(self, id: int, url: str):
        self._check_initialized()
        
        def loadurl():
            media = self.__vlc_instance.media_new(url)
            self.__media_player.set_media(media)
        
        if url and is_url(url):
            self.__current_id = id
            self.__instances[id] = url
            self.__stopped = False
            self.__end_reached = False
            handle_vlc_error(loadurl)

    def release(self, id: int):
        if self.__current_id == id:
            self._check_initialized()
            
            def stop():
                self.__media_player.stop()
                
            handle_vlc_error(stop)
            self.__current_id = None
            self.__applied_filters.clear()
            self.__stopped = True
            self.__end_reached = False

    def play(self, id: int):
        self._check_instance(id)
        
        def resume():
            if self.__end_reached:
                media = self.__vlc_instance.media_new(self.__instances[id])
                self.__media_player.set_media(media)
                self.__end_reached = False
                self.__stopped = False
            self.__media_player.play()
        
        self.__stopped = False
        handle_vlc_error(resume)

    def pause(self, id: int):
        self._check_instance(id)
        
        def pause_play():
            self.__media_player.pause()
            
        handle_vlc_error(pause_play)

    def mute(self, id: int):
        self._check_instance(id)
        
        def toggle_mute():
            current_mute = self.__media_player.audio_get_mute()
            self.__media_player.audio_set_mute(not current_mute)
            
        handle_vlc_error(toggle_mute)

    def unmute(self, id: int):
        self._check_instance(id)
        
        def unmute_audio():
            self.__media_player.audio_set_mute(False)
            
        handle_vlc_error(unmute_audio)

    def stop(self, id: int):
        self._check_instance(id)
        
        def halt():
            self.__media_player.stop()
            
        handle_vlc_error(halt)
        self.__stopped = True
        self.__end_reached = False

    def set_volume(self, id: int, offset: float):
        self._check_instance(id)
        
        def set_vol():
            volume = int(max(0, min(100, offset)))
            self.__media_player.audio_set_volume(volume)
            
        handle_vlc_error(set_vol)

    def set_position(self, id: int, offset: int):
        self._check_instance(id)
        
        def seek():
            self.__media_player.set_time(offset * 1000)
            
        handle_vlc_error(seek)

    def set_loop(self, id: int, loop: bool):
        self._check_instance(id)
        
        def set_loop_mode():
            media = self.__media_player.get_media()
            if media:
                if loop:
                    media.add_option(":input-repeat=-1")
                else:
                    media.add_option(":input-repeat=0")
                    
        handle_vlc_error(set_loop_mode)

    def get_length(self, id: int) -> int:
        self._check_instance(id)
        
        def get_duration():
            length = self.__media_player.get_length()
            return length // 1000 if length > 0 else 0
            
        return handle_vlc_error(get_duration)

    def get_position(self, id: int) -> int:
        self._check_instance(id)
        
        def get_time():
            time_ms = self.__media_player.get_time()
            return time_ms // 1000 if time_ms > 0 else 0
            
        return handle_vlc_error(get_time)

    def get_play_state(self, id: int) -> AVPlaybackState:
        self._check_instance(id)
        try:
            def get_state():
                return self.__media_player.get_state()
                
            if self.__stopped:
                return AVPlaybackState.AV_STATE_STOPPED
            
            state = handle_vlc_error(get_state)
            
            if state == vlc.State.Playing:
                return AVPlaybackState.AV_STATE_PLAYING
            elif state == vlc.State.Paused:
                return AVPlaybackState.AV_STATE_PAUSED
            elif state == vlc.State.Stopped:
                return AVPlaybackState.AV_STATE_STOPPED
            elif state == vlc.State.Ended:
                self.__end_reached = True
                return AVPlaybackState.AV_STATE_NOTHING
            else:
                return AVPlaybackState.AV_STATE_NOTHING
                
        except AVError:
            return AVPlaybackState.AV_STATE_NOTHING

    def get_mute_state(self, id: int) -> AVMuteState:
        self._check_instance(id)
        
        def get_mute():
            return self.__media_player.audio_get_mute()
            
        muted = handle_vlc_error(get_mute)
        return AVMuteState.AV_AUDIO_MUTED if muted else AVMuteState.AV_AUDIO_UNMUTED

    def get_volume(self, id: int) -> float:
        self._check_instance(id)
        
        def get_vol():
            return float(self.__media_player.audio_get_volume())
            
        return handle_vlc_error(get_vol)

    def get_loop(self, id: int) -> bool:
        self._check_instance(id)
        return False


    def apply_filter(self, id: int, filter_id: int, filter_struct: AVFilter):
        pass

    def remove_filter(self, id: int, filter_id: int):
        pass

    def set_parameter(self, id: int, filter_id: int, parameter_name: str, value: ParameterValue):
        pass

    def get_parameter(self, id: int, filter_id: int, parameter_name: str) -> ParameterValue | None:
        pass

    def get_devices(self) -> int:
        self._check_initialized()
        
        def get_device_list():
            devices = self.__media_player.audio_output_device_enum()
            count = 0
            device = devices
            while device:
                count += 1
                device = device.next
            return count
            
        return handle_vlc_error(get_device_list)

    def get_device_info(self, index: int) -> AVDevice:
        self._check_initialized()
        
        def get_device_info_by_index():
            devices = self.__media_player.audio_output_device_enum()
            count = 0
            device = devices
            while device and count < index:
                device = device.next
                count += 1
            if device and count == index:
                return AVDevice(AVMediaBackend.AV_BACKEND_VLC, device.description or device.device or "Unknown")
            raise IndexError("Device index out of range")
            
        return handle_vlc_error(get_device_info_by_index)

    def set_device(self, index: int):
        self._check_initialized()
        
        def set_audio_device():
            devices = self.__media_player.audio_output_device_enum()
            count = 0
            device = devices
            while device and count < index:
                device = device.next
                count += 1
            if device and count == index:
                self.__media_player.audio_output_device_set(device.device)
            else:
                raise IndexError("Device index out of range")
                
        handle_vlc_error(set_audio_device)

    def get_current_device(self) -> int:
        self._check_initialized()
        
        def get_current_device_index():
            current_device = self.__media_player.audio_output_device_get()
            devices = self.__media_player.audio_output_device_enum()
            count = 0
            device = devices
            while device:
                if device.device == current_device:
                    return count
                device = device.next
                count += 1
            return 0
            
        return handle_vlc_error(get_current_device_index)


class VLCVideoPlayer(AVPlayer):
    
    def __init__(self) -> None:
        self.__vlc_interface: VLCMediaInterface = VLCMediaInterface()
        super().__init__(AVMediaType.AV_TYPE_VIDEO, AVMediaBackend.AV_BACKEND_VLC, self.__vlc_interface)

    def init(self, *args, **kw):
        self._controler.init(*args, **kw)

    def release(self):
        if self._primary_instance is not None:
            self._primary_instance.release()
            self._primary_instance = None
        self._controler.free()

    def create_file_instance(self, file_path: str) -> AVMediaInstance:
        if self._primary_instance is None:
            self._primary_instance = AVMediaInstance(self._controler)
        self._primary_instance.load_file(file_path)
        return self._primary_instance

    def create_url_instance(self, url: str) -> AVMediaInstance:
        if self._primary_instance is None:
            self._primary_instance = AVMediaInstance(self._controler)
        self._primary_instance.load_url(url)
        return self._primary_instance

    def set_window(self, window):
        def set_hwnd():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                media_player.set_hwnd(int(window))
                
        handle_vlc_error(set_hwnd)

    def forward(self, offset):
        def seek_forward():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                current_time = media_player.get_time()
                media_player.set_time(current_time + (offset * 1000))
                
        handle_vlc_error(seek_forward)

    def backward(self, offset):
        def seek_backward():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                current_time = media_player.get_time()
                media_player.set_time(max(0, current_time - (offset * 1000)))
                
        handle_vlc_error(seek_backward)

    def set_volume_relative(self, direction, offset):
        def adjust_volume():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                current_volume = media_player.audio_get_volume()
                if direction == "up":
                    new_volume = min(100, current_volume + offset)
                elif direction == "down":
                    new_volume = max(0, current_volume - offset)
                else:
                    return
                media_player.audio_set_volume(int(new_volume))
                
        handle_vlc_error(adjust_volume)

    def set_fullscreen(self, state):
        def toggle_fullscreen():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                media_player.set_fullscreen(state)
                
        handle_vlc_error(toggle_fullscreen)

    def get_fullscreen(self):
        def get_fs_state():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                return media_player.get_fullscreen()
            return False
            
        return handle_vlc_error(get_fs_state)


    def get_aspect_ratio(self):
        def get_video_aspect_ratio():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                return media_player.video_get_aspect_ratio()
            return None

        handle_vlc_error(get_video_aspect_ratio)

    def get_scale(self):
        def get_video_scale():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                return media_player.video_get_scale()
            return 0.0

        return handle_vlc_error(get_video_scale)

    def set_playback_speed(self, speed):
        def set_rate():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                media_player.set_rate(speed)
                
        handle_vlc_error(set_rate)

    def set_aspect_ratio(self, ratio):
        def set_video_aspect_ratio():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                media_player.video_set_aspect_ratio(ratio)
                
        handle_vlc_error(set_video_aspect_ratio)

    def set_scale(self, scale):
        def set_video_scale():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                media_player.video_set_scale(scale)
                
        handle_vlc_error(set_video_scale)

    def set_video_adjust_float(self, property_name, value):
        def set_video_adjust():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                media_player.video_set_adjust_int(vlc.VideoAdjustOption.Enable, 1)
                media_player.video_set_adjust_float(property_name, value)
                
        handle_vlc_error(set_video_adjust)

    def get_video_adjust_float(self, property_name):
        def get_video_adjust():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                return media_player.video_get_adjust_float(property_name)
            return None
            
        return handle_vlc_error(get_video_adjust)

    def take_screenshot(self, image_path, width = 0, height = 0, num_output = 0):
        def screenshot():
            media_player = self.__vlc_interface.get_media_player()
            if media_player:
                media_player.video_take_snapshot(num_output, image_path, width, height)
                
        handle_vlc_error(screenshot)
