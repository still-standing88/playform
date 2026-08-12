import locale
import logging
import mpv
import os
import queue
import sys
import threading
import time
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from typing import Dict, Any, Union, List, Callable, Optional
from .__AV_Common import *
from .__AV_Instance import AVMediaInstance
from .__AV_Interface import AVMediaInterface
from .__AV_Player import AVPlayer
from .mpv_audio_filter import MPVAudioFilter

logger = logging.getLogger(__name__)


def handle_mpv_error(call_func: Callable) -> Any:
    try:
        return call_func()
    except mpv.PropertyUnavailableError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER, f"Property unavailable: {str(e)}")
    except AttributeError as e:
        if "mpv property does not exist" in str(e) or "does not exist" in str(e):
            raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER, f"Property not available: {str(e)}")
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Attribute error: {str(e)}")
    except mpv.ShutdownError:
        raise AVError(AVErrorInfo.INVALID_HANDLE, "MPV core has been shutdown")
    except RuntimeError as e:
        if "loading failed" in str(e).lower():
            raise AVError(AVErrorInfo.FILE_NOTFOUND, f"File loading failed: {str(e)}")
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Runtime error: {str(e)}")
    except SystemError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER, f"Command error: {str(e)}")
    except TypeError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_TYPE, f"Type error: {str(e)}")
    except ValueError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_VALUE, f"Value error: {str(e)}")
    except Exception as e:
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Unknown error: {str(e)}")


_SHUTDOWN = object()


class _MPVWorker(threading.Thread):
    """Owns the single mpv.MPV instance for its whole lifetime. No other thread
    may touch the mpv.MPV object directly -- every operation, including
    construction and terminate(), runs on this thread via submit()."""

    def __init__(self, config: dict) -> None:
        super().__init__(daemon=True, name="MPVCommandWorker")
        self._config = config
        self._queue: "queue.Queue" = queue.Queue()
        self._ready = threading.Event()
        self._mpv: Optional[mpv.MPV] = None
        self._init_error: Optional[Exception] = None
        self._stopped = threading.Event()

    def run(self) -> None:
        # This thread is the sole owner of the mpv.MPV instance, including
        # its WASAPI audio output and device-enumeration calls -- both
        # COM-based on Windows. A plain threading.Thread never initializes
        # a COM apartment for itself; touching COM-dependent Windows APIs
        # from an uninitialized thread produces RPC_E_WRONG_THREAD /
        # RPC_E_CANTCALLOUT_ININPUTSYNCCALL-class failures, which is a
        # documented prior issue in this codebase (see the COM-apartment/
        # WASAPI investigation scripts under scripts/, and
        # app_db/base_database.py's queue worker doing the same
        # CoInitialize/CoUninitialize dance for the same reason).
        win_com = None
        if sys.platform == "win32":
            try:
                import pythoncom
                pythoncom.CoInitialize()
                win_com = pythoncom
            except Exception:
                win_com = None

        try:
            # Qt's QApplication construction can silently change the process-
            # wide LC_NUMERIC locale away from "C". libmpv's internal number
            # parsing depends on "C" numeric formatting; python-mpv's own
            # README calls this out as required before constructing the first
            # mpv.MPV(). Re-asserted here (not just once at process startup)
            # so it holds even if something re-changes the locale between
            # player instances -- setlocale() is process-wide, so this is a
            # cheap, safe no-op when it's already "C".
            try:
                locale.setlocale(locale.LC_NUMERIC, "C")
            except locale.Error:
                pass
            self._mpv = mpv.MPV(**self._config)
        except Exception as e:
            self._init_error = e
            self._ready.set()
            self._stopped.set()
            if win_com is not None:
                try:
                    win_com.CoUninitialize()
                except Exception:
                    pass
            return
        self._ready.set()

        while True:
            item = self._queue.get()
            if item is _SHUTDOWN:
                break
            func, future = item
            try:
                result = handle_mpv_error(func)
                if future is not None:
                    future.set_result(result)
            except Exception as e:
                if future is not None:
                    future.set_exception(e)
                else:
                    # Fire-and-forget (wait=False) jobs have nowhere to
                    # report a failure to -- without this, a command mpv
                    # rejects (e.g. an invalid af filter chain) fails
                    # completely silently, with no error and no visible
                    # effect other than "the feature just doesn't work".
                    logger.warning("MPV command failed (fire-and-forget): %s", e)
            if self._mpv is not None and self._mpv.core_shutdown:
                self._drain_rejecting(AVError(AVErrorInfo.INVALID_HANDLE, "MPV core has been shutdown"))
                break

        try:
            if self._mpv is not None and not self._mpv.core_shutdown:
                self._mpv.terminate()
        except Exception:
            pass
        self._mpv = None
        self._stopped.set()
        if win_com is not None:
            try:
                win_com.CoUninitialize()
            except Exception:
                pass

    def _drain_rejecting(self, error: AVError) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is _SHUTDOWN:
                continue
            _func, future = item
            if future is not None:
                future.set_exception(error)

    def wait_ready(self, timeout: float = 10.0) -> None:
        if not self._ready.wait(timeout=timeout):
            raise AVError(AVErrorInfo.INITIALIZATION_ERROR, "MPV worker did not start in time")
        if self._init_error is not None:
            raise AVError(AVErrorInfo.INITIALIZATION_ERROR, f"Failed to initialize MPV: {self._init_error}")

    def submit(self, func: Callable, wait: bool, timeout: Optional[float]) -> Any:
        if self._stopped.is_set():
            raise AVError(AVErrorInfo.INVALID_HANDLE, "MPV worker has shut down")
        future: Optional[Future] = Future() if wait else None
        self._queue.put((func, future))
        if not wait:
            return None
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            raise AVError(AVErrorInfo.INVALID_HANDLE, "MPV command timed out")

    def shutdown(self, timeout: float = 5.0) -> None:
        if self._stopped.is_set():
            return
        self._queue.put(_SHUTDOWN)
        self.join(timeout=timeout)
        self._stopped.set()


class MPVMediaInterface(AVMediaInterface):

    def __init__(self) -> None:
        super().__init__(AVMediaType.AV_TYPE_VIDEO, AVMediaBackend.AV_BACKEND_MPV)
        self.__instances: dict[int, str] = {}
        self.__worker: Optional[_MPVWorker] = None
        self.__current_id: int | None = None
        self.__applied_filters: Dict[int, MPVAudioFilter] = {}
        self.__stopped = False
        self.__end_reached = False
        self.__fresh_load_pending = False
        self.__generation = 0
        self.__seek_token: object | None = None
        self.__volume_token: object | None = None
        self.__command_count = 0
        self.__last_command_time = 0.0
        self.__last_error: Optional[AVError] = None

    @property
    def last_error(self) -> Optional[AVError]:
        return self.__last_error

    def _track_command(self):
        current_time = time.time()
        self.__command_count += 1
        if current_time - self.__last_command_time > 1.0:
            self.__command_count = 1
        self.__last_command_time = current_time

    def is_heavy_usage_period(self) -> bool:
        return self._is_heavy_usage()

    def _is_heavy_usage(self) -> bool:
        return self.__command_count > 20

    def _mpv(self) -> mpv.MPV:
        assert self.__worker is not None and self.__worker._mpv is not None
        return self.__worker._mpv

    def _submit(self, func: Callable, wait: bool = True, timeout: Optional[float] = 2.0, record_only: bool = True) -> Any:
        if self.__worker is None:
            raise AVError(AVErrorInfo.UNINITIALIZED, "MPV not initialized")

        def wrapped():
            self._track_command()
            return func()

        try:
            result = self.__worker.submit(wrapped, wait=wait, timeout=timeout)
            self.__last_error = None
            return result
        except AVError as e:
            self.__last_error = e
            if record_only:
                return None
            raise

    def run_on_mpv(self, func: Callable[[mpv.MPV], Any], wait: bool = True, timeout: Optional[float] = 1.0, record_only: bool = True) -> Any:
        """Public escape hatch for callers (MPVVideoPlayer) that need direct mpv
        access for calls this interface doesn't already wrap. func always runs
        on the single MPV command-owner thread; nothing outside this module
        should ever call methods on an mpv.MPV instance directly."""
        return self._submit(lambda: func(self._mpv()), wait=wait, timeout=timeout, record_only=record_only)

    def init(self, *args, **kw):
        config = dict(kw.get("config", {}) or {})
        window = kw.get("window", None)
        if window is not None:
            config['wid'] = str(int(window))
        config.setdefault('ytdl', True)
        # mpv's own default keybindings (arrow-key seek, space to pause, etc.)
        # would otherwise fire independently on the embedded window's native
        # input, racing/duplicating the app's own Qt-level shortcuts for the
        # same keys. The app is the sole source of truth for playback control.
        config.setdefault('input_default_bindings', False)
        config.setdefault('input_vo_keyboard', False)
        # mpv defaults to vo=gpu-next (libplacebo), a shader-graph renderer
        # with runtime HLSL compilation -- far more moving parts than the
        # classic vo=gpu, and the source of a real access-violation crash
        # (null-pointer read) seen during real playback. Pin to the older,
        # far more battle-tested renderer; callers can still override via
        # config explicitly if they want gpu-next back.
        config.setdefault('vo', 'gpu')

        worker = _MPVWorker(config)
        worker.start()
        try:
            worker.wait_ready()
        except AVError:
            worker.shutdown()
            raise
        self.__worker = worker
        self.__stopped = False
        self.__end_reached = False

    def free(self):
        worker = self.__worker
        if worker is not None:
            # worker.shutdown() blocks (joins the worker thread) so terminate()
            # is guaranteed to finish before returning. free() is reachable
            # from GUI event handlers on the Qt main thread (MPVVideoPlayer.
            # release() -> here); run the wait on a throwaway thread instead
            # of blocking the caller.
            #
            # self.__worker is deliberately NOT cleared here (unlike before):
            # release()/free() commonly follow right behind other
            # fire-and-forget jobs (e.g. AVMediaInstance.release()'s own
            # pause()) that are still sitting in the worker's queue, not yet
            # executed. Those closures call self._mpv(), which reads
            # self.__worker -- nulling it immediately on this (calling)
            # thread raced the worker thread still draining that queue,
            # so those in-flight jobs hit self._mpv()'s assertion and failed
            # (verified empirically). shutdown() enqueues its sentinel
            # behind any already-queued work, so everything queued before
            # this call still runs against a valid worker/mpv instance;
            # _MPVWorker.submit() already rejects new work once the worker
            # actually stops (_stopped.is_set()), so nothing needs
            # self.__worker itself to go None to be correctly protected.
            threading.Thread(target=worker.shutdown, daemon=True, name="MPVWorkerShutdown").start()
        self.__current_id = None
        self.__applied_filters.clear()
        self.__stopped = False
        self.__end_reached = False
        self.__fresh_load_pending = False

    def _check_initialized(self):
        if self.__worker is None:
            raise AVError(AVErrorInfo.UNINITIALIZED, "MPV not initialized")
        if self.__worker._stopped.is_set():
            raise AVError(AVErrorInfo.INVALID_HANDLE, "MPV core has been shutdown")

    def _check_instance(self, id: int):
        self._check_initialized()
        if self.__current_id != id:
            raise AVError(AVErrorInfo.INVALID_HANDLE, f"Invalid instance ID: {id}")

    def load_file(self, id: int, path: str):
        self._check_initialized()
        if not (path and is_path(path) and os.path.exists(path)):
            return

        self.__generation += 1
        gen = self.__generation
        self.__current_id = id
        self.__instances[id] = path
        self.__stopped = False
        self.__end_reached = False
        self.__fresh_load_pending = True

        def do_load():
            if gen != self.__generation:
                return
            self._mpv().command("loadfile", path)

        self._submit(do_load, wait=False)
        self._load_subtitles(path, gen)

    def load_url(self, id: int, url: str):
        self._check_initialized()
        if not (url and is_url(url)):
            return

        self.__generation += 1
        gen = self.__generation
        self.__current_id = id
        self.__instances[id] = url
        self.__stopped = False
        self.__end_reached = False
        self.__fresh_load_pending = True

        def do_load():
            if gen != self.__generation:
                return
            self._mpv().command("loadfile", url)

        self._submit(do_load, wait=False)

    def _load_subtitles(self, path: str, gen: int):
        subtitle_formats = ["idx", "sub", "srt", "rt", "ssa", "ass", "mks", "vtt", "sup", "scc", "smi", "lrc", "pgs"]
        dir_path = os.path.dirname(path)
        filename = os.path.splitext(os.path.basename(path))[0]

        for format in subtitle_formats:
            subtitle_path = os.path.join(dir_path, f"{filename}.{format}")
            if os.path.exists(subtitle_path):
                def add_subtitle():
                    if gen != self.__generation:
                        return
                    self._mpv().sub_add(subtitle_path)
                self._submit(add_subtitle, wait=False)
                break

    def release(self, id: int):
        if self.__current_id == id:
            self._check_initialized()

            def halt():
                # Property write instead of the stop command -- see
                # set_position()'s comment. release() can run soon after a
                # load (e.g. closing media right after opening it), and
                # __stopped below already makes get_play_state() report
                # stopped regardless of whether mpv itself finishes this in
                # time, so silencing via "pause" is enough here.
                self._mpv().pause = True
            self._submit(halt, wait=False)
            self.__current_id = None
            self.__applied_filters.clear()
            self.__stopped = True
            self.__end_reached = False

    def play(self, id: int):
        self._check_instance(id)
        gen = self.__generation
        instance_path = self.__instances.get(id)
        # If load_file()/load_url() just issued its own loadfile for this
        # exact generation, that load is already in flight -- reissuing
        # loadfile here races mpv's own open (interrupting it mid-open,
        # confirmed via traced mpv events: a spurious extra end-file per
        # transition). Only consumed once, for this specific play() call; a
        # bare play() not preceded by a fresh load (e.g. un-pausing after
        # mpv genuinely went idle) still falls through to the
        # reload-if-idle check below, unchanged.
        skip_reload = self.__fresh_load_pending
        self.__fresh_load_pending = False

        def resume():
            if gen != self.__generation:
                return
            mpv_instance = self._mpv()
            if not skip_reload and (self.__end_reached or mpv_instance.time_pos is None):
                if instance_path:
                    mpv_instance.command("loadfile", instance_path)
                self.__end_reached = False
            mpv_instance.pause = False
            self.__stopped = False

        self._submit(resume, wait=False)

    def pause(self, id: int):
        self._check_instance(id)
        gen = self.__generation

        def pause_play():
            if gen != self.__generation:
                return
            self._mpv().pause = True
        self._submit(pause_play, wait=False)

    def mute(self, id: int):
        self._check_instance(id)
        gen = self.__generation

        def toggle_mute():
            if gen != self.__generation:
                return
            mpv_instance = self._mpv()
            mpv_instance.mute = not mpv_instance.mute
        self._submit(toggle_mute, wait=False)

    def unmute(self, id: int):
        self._check_instance(id)
        gen = self.__generation

        def unmute_audio():
            if gen != self.__generation:
                return
            self._mpv().mute = False
        self._submit(unmute_audio, wait=False)

    def stop(self, id: int):
        self._check_instance(id)
        gen = self.__generation

        def halt():
            if gen != self.__generation:
                return
            self._mpv().stop()
            self.__stopped = True
            self.__end_reached = False

        self._submit(halt, wait=False)

    def set_volume(self, id: int, offset: float):
        self._check_instance(id)
        token = object()
        self.__volume_token = token

        def set_vol():
            if self.__volume_token is not token:
                return
            self._mpv().volume = offset
        self._submit(set_vol, wait=False)

    def set_position(self, id: int, offset: int):
        self._check_instance(id)
        token = object()
        self.__seek_token = token

        def seek():
            if self.__seek_token is not token:
                return
            # time_pos is a read/write mpv property; setting it does an
            # absolute/exact seek just like the seek command, but property
            # writes don't go through mpv_command_node -- unlike .seek(),
            # this doesn't fail with "Error running mpv command" when
            # issued immediately after a load, before mpv has actually
            # finished opening the file (verified empirically). Matters
            # a lot here since callers like "resume last position" seek
            # right after load_file()/play() with no delay.
            self._mpv().time_pos = offset
        self._submit(seek, wait=False)

    def set_loop(self, id: int, loop: bool):
        self._check_instance(id)
        gen = self.__generation
        loop_value = "inf" if loop else "no"

        def set_loop_mode():
            if gen != self.__generation:
                return
            self._mpv().loop = loop_value
        self._submit(set_loop_mode, wait=False)

    def get_length(self, id: int) -> int:
        self._check_instance(id)

        def get_duration():
            return self._mpv().duration
        duration = self._submit(get_duration, wait=True, timeout=0.5)
        return int(duration) if duration is not None else 0

    def get_position(self, id: int) -> int:
        self._check_instance(id)

        def get_time():
            return self._mpv().time_pos
        pos = self._submit(get_time, wait=True, timeout=0.5)
        return int(pos) if pos is not None else 0

    def get_play_state(self, id: int) -> AVPlaybackState:
        try:
            self._check_instance(id)
        except AVError:
            return AVPlaybackState.AV_STATE_NOTHING

        if self.__stopped:
            return AVPlaybackState.AV_STATE_STOPPED

        def get_state_info():
            mpv_instance = self._mpv()
            return {
                'pause': mpv_instance.pause,
                'idle_active': bool(mpv_instance.idle_active),
            }

        state_info = self._submit(get_state_info, wait=True, timeout=0.5)
        if state_info is None:
            return AVPlaybackState.AV_STATE_NOTHING

        # idle-active is mpv's "nothing is loaded/playing right now" signal.
        # eof-reached was tried here first, but per mpv's own docs it's only
        # meaningful with --keep-open (which this app doesn't set): without
        # it, mpv fully unloads the file at EOF instead of holding on the
        # last frame, and eof-reached never flips to true at all -- so that
        # approach silently broke *all* end-of-track detection (verified
        # empirically: idle_active/path/time_pos/duration all reset but
        # eof_reached stayed False). idle_active, in contrast, both catches
        # genuine EOF and correctly reports "not idle" the instant a new
        # loadfile is issued -- before duration/time_pos are even known --
        # so it has neither of the previous heuristic's false-positive
        # windows either.
        if state_info['idle_active']:
            self.__end_reached = True
            return AVPlaybackState.AV_STATE_NOTHING

        return AVPlaybackState.AV_STATE_PAUSED if state_info['pause'] else AVPlaybackState.AV_STATE_PLAYING

    def get_mute_state(self, id: int) -> AVMuteState:
        self._check_instance(id)

        def get_mute():
            return self._mpv().mute
        muted = self._submit(get_mute, wait=True, timeout=0.5)
        return AVMuteState.AV_AUDIO_MUTED if muted else AVMuteState.AV_AUDIO_UNMUTED

    def get_volume(self, id: int) -> float:
        self._check_instance(id)

        def get_vol():
            return self._mpv().volume
        volume = self._submit(get_vol, wait=True, timeout=0.5)
        return float(volume) if volume is not None else 0.0

    def get_loop(self, id: int) -> bool:
        self._check_instance(id)

        def get_loop_state():
            return self._mpv().loop
        loop_val = self._submit(get_loop_state, wait=True, timeout=0.5)
        return loop_val == "inf" if loop_val is not None else False

    def _rebuild_filter_chain(self):
        # Order by filter name (handle), not by dict-insertion/filter_id
        # order -- otherwise unchecking and re-checking an effect moves it
        # to the end of the chain, silently changing the audible result
        # (and evaluation order matters for some filter combinations).
        filter_objs = sorted(self.__applied_filters.values(), key=lambda f: f.handle)
        filter_strings = []
        for filter_obj in filter_objs:
            filter_string = filter_obj.construct()
            if filter_string:
                filter_strings.append(filter_string)
        return ",".join(filter_strings) if filter_strings else ""

    def apply_filter(self, id: int, filter_id: int, filter_struct: AVFilter):
        self._check_instance(id)
        if not isinstance(filter_struct, MPVAudioFilter):
            raise AVError(AVErrorInfo.INVALID_MEDIA_FILTER, "Filter must be MPVAudioFilter")

        self.__applied_filters[filter_id] = filter_struct
        filter_chain = self._rebuild_filter_chain()

        def set_af_chain():
            self._mpv().af = filter_chain
        self._submit(set_af_chain, wait=False)

    def remove_filter(self, id: int, filter_id: int):
        self._check_instance(id)
        if filter_id in self.__applied_filters:
            del self.__applied_filters[filter_id]
            filter_chain = self._rebuild_filter_chain()

            def set_af_chain():
                self._mpv().af = filter_chain
            self._submit(set_af_chain, wait=False)

    def set_parameter(self, id: int, filter_id: int, parameter_name: str, value: ParameterValue):
        self._check_instance(id)
        if filter_id in self.__applied_filters:
            filter_struct = self.__applied_filters[filter_id]
            filter_struct.set_parameter(parameter_name, value)
            filter_chain = self._rebuild_filter_chain()

            def set_af_chain():
                self._mpv().af = filter_chain
            self._submit(set_af_chain, wait=False)

    def get_parameter(self, id: int, filter_id: int, parameter_name: str) -> ParameterValue | None:
        self._check_instance(id)
        if filter_id in self.__applied_filters:
            return self.__applied_filters[filter_id].get_parameter(parameter_name)
        return None

    def get_devices(self) -> int:
        self._check_initialized()

        def get_device_list():
            return self._mpv().audio_device_list
        audio_devices = self._submit(get_device_list, wait=True, timeout=0.5) or []
        return len(audio_devices)

    def get_device_info(self, index: int) -> AVDevice:
        self._check_initialized()

        def get_device_list():
            return self._mpv().audio_device_list
        audio_devices = self._submit(get_device_list, wait=True, timeout=0.5) or []
        if 0 <= index < len(audio_devices):
            device = audio_devices[index]
            return AVDevice(AVMediaBackend.AV_BACKEND_MPV, device.get('description', device.get('name', 'Unknown')))
        raise IndexError("Device index out of range")

    def set_device(self, index: int):
        self._check_initialized()

        def get_device_list():
            return self._mpv().audio_device_list
        audio_devices = self._submit(get_device_list, wait=True, timeout=0.5) or []
        if 0 <= index < len(audio_devices):
            device_name = audio_devices[index]['name']

            def set_audio_device():
                self._mpv().audio_device = device_name
            self._submit(set_audio_device, wait=False)
        else:
            raise IndexError("Device index out of range")

    def get_current_device(self) -> int:
        self._check_initialized()

        def get_audio_device():
            return self._mpv().audio_device

        def get_device_list():
            return self._mpv().audio_device_list

        current_device = self._submit(get_audio_device, wait=True, timeout=0.5)
        audio_devices = self._submit(get_device_list, wait=True, timeout=0.5) or []

        for i, device in enumerate(audio_devices):
            if device['name'] == current_device:
                return i
        return 0


class MPVVideoPlayer(AVPlayer):

    def __init__(self) -> None:
        self.__mpv_interface: MPVMediaInterface = MPVMediaInterface()
        super().__init__(AVMediaType.AV_TYPE_VIDEO, AVMediaBackend.AV_BACKEND_MPV, self.__mpv_interface)

    def init(self, *args, **kw):
        self._controler.init(*args, **kw)

    def release(self):
        super().release()
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
        self.__mpv_interface.run_on_mpv(lambda m: m._set_property("wid", str(int(window))), wait=False)

    def forward(self, offset):
        # See set_position()'s comment: time_pos writes are race-safe
        # right after a load in a way .seek() commands aren't.
        self.__mpv_interface.run_on_mpv(lambda m: setattr(m, 'time_pos', (m.time_pos or 0.0) + offset), wait=False)

    def backward(self, offset):
        self.__mpv_interface.run_on_mpv(lambda m: setattr(m, 'time_pos', max(0.0, (m.time_pos or 0.0) - offset)), wait=False)

    def set_volume_relative(self, direction, offset):
        def adjust(m):
            if direction == "up":
                m.volume = m.volume + offset
            elif direction == "down":
                m.volume = m.volume - offset
        self.__mpv_interface.run_on_mpv(adjust, wait=False)

    def set_fullscreen(self, state):
        self.__mpv_interface.run_on_mpv(lambda m: setattr(m, 'fullscreen', state), wait=False)

    def get_fullscreen(self):
        return bool(self.__mpv_interface.run_on_mpv(lambda m: m.fullscreen, wait=True, timeout=0.5))

    def set_playback_speed(self, speed):
        self.__mpv_interface.run_on_mpv(lambda m: setattr(m, 'speed', speed), wait=False)

    def set_resolution(self, width, height):
        self.__mpv_interface.run_on_mpv(lambda m: setattr(m, 'vf', f"scale={width}:{height}"), wait=False)

    def set_video_adjust_float(self, name: str, value: float):
        # The widget's own range is 0.0-2.0 (brightness/contrast/saturation) or
        # 0.1-10.0 (gamma) with 1.0 == neutral; mpv's equalizer properties are
        # -100..100 with 0 == neutral. hue is already degrees on both sides.
        if name == "hue":
            self.__mpv_interface.run_on_mpv(lambda m, v=value: setattr(m, 'hue', v), wait=False)
            return
        mpv_property = {"brightness": "brightness", "contrast": "contrast",
                         "gamma": "gamma", "saturation": "saturation"}.get(name)
        if mpv_property is None:
            return
        mpv_value = (value - 1.0) * 100.0
        self.__mpv_interface.run_on_mpv(lambda m, p=mpv_property, v=mpv_value: setattr(m, p, v), wait=False)

    def set_video_rotate(self, degrees: int):
        self.__mpv_interface.run_on_mpv(lambda m, d=degrees: setattr(m, 'video_rotate', d), wait=False)

    def set_video_pan(self, pan_x: float, pan_y: float):
        # mpv's native pan properties translate the visible image within its
        # bounding box (revealing letterbox on the opposite side) rather than
        # cropping into it, unlike an lavfi crop filter -- deliberate choice
        # to keep panning non-destructive, same spirit as rotate/flip.
        def apply(m):
            m.video_pan_x = pan_x
            m.video_pan_y = pan_y
        self.__mpv_interface.run_on_mpv(apply, wait=False)

    def set_deinterlace(self, enabled: bool):
        self.__mpv_interface.run_on_mpv(lambda m, e=enabled: setattr(m, 'deinterlace', e), wait=False)

    def set_deband(self, enabled: bool):
        self.__mpv_interface.run_on_mpv(lambda m, e=enabled: setattr(m, 'deband', e), wait=False)

    def set_flip_horizontal(self, enabled: bool):
        self._flip_horizontal = enabled
        self._apply_video_flip()

    def set_flip_vertical(self, enabled: bool):
        self._flip_vertical = enabled
        self._apply_video_flip()

    def _apply_video_flip(self):
        # mpv has no direct hflip/vflip property (unlike video-rotate) --
        # both axes only exist as ffmpeg filters reachable through the lavfi
        # vf wrapper, so the two toggles have to be combined into one vf
        # string rather than set independently.
        filters = []
        if getattr(self, '_flip_horizontal', False):
            filters.append('hflip')
        if getattr(self, '_flip_vertical', False):
            filters.append('vflip')
        vf = f"lavfi=[{','.join(filters)}]" if filters else ""
        self.__mpv_interface.run_on_mpv(lambda m, v=vf: setattr(m, 'vf', v), wait=False)

    def get_video_track_id(self):
        """mpv's vid property: an int track id, or a falsy value (False/
        None/"no") when there is no video track -- i.e. audio-only media."""
        return self.__mpv_interface.run_on_mpv(lambda m: m.vid, wait=True, timeout=0.5)

    def is_audio_only(self) -> bool:
        vid = self.get_video_track_id()
        if vid is None:
            return False
        if isinstance(vid, bool):
            return vid is False
        if isinstance(vid, (int, float)):
            return vid < 0
        if isinstance(vid, str):
            return vid.strip().lower() == "no"
        return False

    def set_reverse_playback(self, enabled: bool):
        # play-direction is a real mpv property (0.39+) but the docs call
        # it unreliable; verified empirically it's fine for local audio
        # files with room left to play into, but running off the start of
        # the file while reversed can leave mpv's position tracking stuck
        # (idle_active/time_pos) even after switching back to "forward" --
        # an explicit re-seek reliably un-sticks it, so always do one when
        # turning reverse off.
        self._reverse_playback_active = enabled
        direction = "backward" if enabled else "forward"
        self.__mpv_interface.run_on_mpv(lambda m, d=direction: setattr(m, 'play_direction', d), wait=False)
        if not enabled:
            def recover(m):
                pos = m.time_pos
                # Property write, not the seek command -- see set_position().
                m.time_pos = pos if pos is not None else 0.0
            self.__mpv_interface.run_on_mpv(recover, wait=False)

    def get_reverse_playback(self) -> bool:
        return self._reverse_playback_active

    def set_start_file_callback(self, callback):
        def register(m):
            @m.event_callback('file-loaded')
            def start_file_handler(event):
                if callback:
                    callback(event)
            return start_file_handler
        return self.__mpv_interface.run_on_mpv(register, wait=True, timeout=1.0)

    def set_end_file_callback(self, callback):
        def register(m):
            @m.event_callback('end-file')
            def end_file_handler(event):
                if callback:
                    callback(event)
            return end_file_handler
        return self.__mpv_interface.run_on_mpv(register, wait=True, timeout=1.0)

    def set_shutdown_callback(self, callback):
        def register(m):
            @m.event_callback('shutdown')
            def shutdown_handler(event):
                if callback:
                    callback(event)
            return shutdown_handler
        return self.__mpv_interface.run_on_mpv(register, wait=True, timeout=1.0)

    def get_equalizer_bands(self) -> List[float]:
        from .mpv_audio_filter import MPVEqualizerFilter
        return list(MPVEqualizerFilter.BAND_FREQUENCIES)

    def get_equalizer_presets(self) -> List[str]:
        from .mpv_equalizer_presets import EQUALIZER_PRESETS
        return [name for name, _bands in EQUALIZER_PRESETS]

    def get_preset_amps(self, preset: int) -> List[float]:
        from .mpv_equalizer_presets import EQUALIZER_PRESETS
        if 0 <= preset < len(EQUALIZER_PRESETS):
            return list(EQUALIZER_PRESETS[preset][1])
        return [0.0] * 10
