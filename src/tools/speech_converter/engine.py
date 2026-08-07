import os
import sys
import tempfile

from PySide6.QtCore import QObject, Signal
from PySide6.QtTextToSpeech import QTextToSpeech

ENGINE_PRIORITY = ["sapi", "macos", "speechd", "flite", "mock"]
IS_WINDOWS = sys.platform == "win32"


def pick_engine_name() -> str:
    available = QTextToSpeech.availableEngines()
    for name in ENGINE_PRIORITY:
        if name in available:
            return name
    return available[0] if available else "mock"


def wrap_pitch_xml(text: str, pitch_middle: int) -> str:
    return f'<pitch middle="{pitch_middle}">\n{text}\n</pitch>'


class SpeechEngine(QObject):
    state_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine_name = pick_engine_name()
        self.tts = QTextToSpeech(self.engine_name)
        self.tts.stateChanged.connect(self._on_state_changed)

        self._using_sapi_direct = False
        self._sapi_voice = None
        if IS_WINDOWS and self.engine_name == "sapi":
            self._init_sapi()

    def _init_sapi(self):
        try:
            import win32com.client
            self._sapi_voice = win32com.client.gencache.EnsureDispatch("SAPI.SpVoice")
        except Exception:
            self._sapi_voice = None

    def supports_pause_resume(self) -> bool:
        return bool(self.tts.engineCapabilities() & QTextToSpeech.Capability.PauseResume)

    def supports_pitch_xml(self) -> bool:
        return self._sapi_voice is not None

    def available_locales(self):
        return self.tts.availableLocales()

    def available_voices(self):
        return self.tts.availableVoices()

    def set_locale(self, locale):
        self.tts.setLocale(locale)

    def set_voice(self, voice):
        self.tts.setVoice(voice)

    def set_rate(self, value: float):
        self.tts.setRate(value)

    def set_pitch(self, value: float):
        self.tts.setPitch(value)

    def set_volume(self, value: float):
        self.tts.setVolume(value)

    def speak(self, text: str, use_pitch_xml: bool = False, pitch_middle: int = 0):
        if not text:
            return

        if use_pitch_xml and self._sapi_voice is not None:
            xml_text = wrap_pitch_xml(text, pitch_middle)
            try:
                self._sapi_voice.Speak(xml_text, 1 | 2 | 8)  # Async | PurgeBeforeSpeak | IsXML
                self._using_sapi_direct = True
                self.state_changed.emit("speaking")
            except Exception as error:
                self.error_occurred.emit(str(error))
            return

        self._using_sapi_direct = False
        self.tts.say(text)

    def pause(self):
        if self._using_sapi_direct and self._sapi_voice is not None:
            try:
                self._sapi_voice.Pause()
                self.state_changed.emit("paused")
            except Exception as error:
                self.error_occurred.emit(str(error))
            return
        self.tts.pause()

    def resume(self):
        if self._using_sapi_direct and self._sapi_voice is not None:
            try:
                self._sapi_voice.Resume()
                self.state_changed.emit("speaking")
            except Exception as error:
                self.error_occurred.emit(str(error))
            return
        self.tts.resume()

    def stop(self):
        if self._using_sapi_direct and self._sapi_voice is not None:
            try:
                self._sapi_voice.Speak("", 2)  # PurgeBeforeSpeak
                self.state_changed.emit("ready")
            except Exception as error:
                self.error_occurred.emit(str(error))
            self._using_sapi_direct = False
            return
        self.tts.stop()

    def state(self):
        return self.tts.state()

    def can_save_to_file(self) -> bool:
        return IS_WINDOWS and self._sapi_voice is not None

    def save_to_file(self, text: str, output_path: str, use_pitch_xml: bool = False, pitch_middle: int = 0) -> bool:
        if not self.can_save_to_file():
            raise RuntimeError(_("Saving speech to a file requires the Windows SAPI5 engine."))

        import win32com.client
        from win32com.client import gencache

        wav_path = output_path
        needs_transcode = not output_path.lower().endswith(".wav")
        if needs_transcode:
            fd, wav_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

        stream = gencache.EnsureDispatch("SAPI.SpFileStream")
        try:
            audio_format = gencache.EnsureDispatch("SAPI.SpAudioFormat")
            audio_format.Type = win32com.client.constants.SAFT44kHz16BitStereo
            stream.Format = audio_format
            stream.Open(wav_path, win32com.client.constants.SSFMCreateForWrite, False)

            previous_output = self._sapi_voice.AudioOutputStream
            self._sapi_voice.AudioOutputStream = stream

            speak_text = wrap_pitch_xml(text, pitch_middle) if use_pitch_xml else text
            flags = 8 if use_pitch_xml else 0  # IsXML
            self._sapi_voice.Speak(speak_text, flags)

            self._sapi_voice.AudioOutputStream = previous_output
        finally:
            stream.Close()

        if needs_transcode:
            try:
                self._transcode(wav_path, output_path)
            finally:
                os.remove(wav_path)

        return True

    @staticmethod
    def _transcode(wav_path: str, output_path: str):
        from tools.ffmpeg_handler import FFmpegHandler
        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        ffmpeg.input(wav_path).output(output_path)
        ffmpeg.execute()

    def _on_state_changed(self, state):
        labels = {
            QTextToSpeech.State.Ready: "ready",
            QTextToSpeech.State.Speaking: "speaking",
            QTextToSpeech.State.Paused: "paused",
            QTextToSpeech.State.Error: "error",
        }
        self.state_changed.emit(labels.get(state, "ready"))
        if state == QTextToSpeech.State.Error:
            self.error_occurred.emit(self.tts.errorString())
