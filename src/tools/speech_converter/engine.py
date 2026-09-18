import os
import sys
import tempfile

from PySide6.QtCore import QObject, QTimer, Signal
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
        self._voice_name = self.tts.voice().name()
        self._enumerator = None
        self._state = "ready"
        self._direct_poll = QTimer(self)
        self._direct_poll.setInterval(250)
        self._direct_poll.timeout.connect(self._poll_direct_speech)
        if IS_WINDOWS and self.engine_name == "sapi":
            self._init_sapi()
            self._select_sapi_voice(self._sapi_voice, self._voice_name)

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

    def supports_normal_pitch(self) -> bool:
        # SAPI5 silently ignores QTextToSpeech.setPitch() — the XML-tag path above is the
        # only way to control pitch on that engine.
        return self.engine_name != "sapi"

    def available_locales(self):
        return self.tts.availableLocales()

    def available_voices(self):
        return self.tts.availableVoices()

    def voices_for_locale(self, locale):
        # availableVoices() only reports the current locale's voices, so browsing another
        # locale's voices happens on a throwaway instance to leave playback state alone.
        if self._enumerator is None:
            self._enumerator = QTextToSpeech(self.engine_name, self)
        self._enumerator.setLocale(locale)
        return self._enumerator.availableVoices()

    def voices_for_locale_name(self, locale_name: str):
        # availableLocales() can list the same locale name more than once, each entry
        # exposing a different set of voices, so all of them are merged per language.
        pairs = []
        seen = set()
        for locale in self.available_locales():
            if locale.name() != locale_name:
                continue
            for voice in self.voices_for_locale(locale):
                if voice.name() in seen:
                    continue
                seen.add(voice.name())
                pairs.append((locale, voice))
        return pairs

    def current_locale(self):
        return self.tts.locale()

    def current_voice(self):
        return self.tts.voice()

    def set_locale(self, locale):
        self.tts.setLocale(locale)

    def set_voice(self, voice):
        self.tts.setVoice(voice)
        self._voice_name = voice.name()
        if self._sapi_voice is not None:
            try:
                self._select_sapi_voice(self._sapi_voice, self._voice_name)
            except Exception as error:
                self.error_occurred.emit(str(error))

    def apply_voice(self, locale_name: str, voice_name: str):
        if not locale_name or not voice_name:
            return
        for locale, voice in self.voices_for_locale_name(locale_name):
            if voice.name() == voice_name:
                self.set_locale(locale)
                self.set_voice(voice)
                return

    @staticmethod
    def _select_sapi_voice(sapi_voice, voice_name: str):
        if sapi_voice is None or not voice_name:
            return
        # Qt reports "Microsoft David Desktop" where SAPI describes the same token as
        # "Microsoft David Desktop - English (United States)".
        tokens = sapi_voice.GetVoices()
        for index in range(tokens.Count):
            token = tokens.Item(index)
            description = token.GetDescription()
            if description == voice_name or description.startswith(f"{voice_name} -"):
                sapi_voice.Voice = token
                return

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
                self._set_state("speaking")
            except Exception as error:
                self.error_occurred.emit(str(error))
            return

        self._using_sapi_direct = False
        self.tts.say(text)

    def pause(self):
        if self._using_sapi_direct and self._sapi_voice is not None:
            try:
                self._sapi_voice.Pause()
                self._set_state("paused")
            except Exception as error:
                self.error_occurred.emit(str(error))
            return
        self.tts.pause()

    def resume(self):
        if self._using_sapi_direct and self._sapi_voice is not None:
            try:
                self._sapi_voice.Resume()
                self._set_state("speaking")
            except Exception as error:
                self.error_occurred.emit(str(error))
            return
        self.tts.resume()

    def stop(self):
        if self._using_sapi_direct and self._sapi_voice is not None:
            try:
                self._sapi_voice.Speak("", 2)  # PurgeBeforeSpeak
                self._set_state("ready")
            except Exception as error:
                self.error_occurred.emit(str(error))
            self._using_sapi_direct = False
            return
        self.tts.stop()

    def state(self):
        return self._state

    def _set_state(self, state: str):
        self._state = state
        if state == "speaking" and self._using_sapi_direct:
            self._direct_poll.start()
        else:
            self._direct_poll.stop()
        self.state_changed.emit(state)

    def _poll_direct_speech(self):
        # SpVoice reports the utterance's own progress, which is the only
        # signal the direct path has that the speech ended -- Qt's engine
        # stays Ready throughout it, so nothing else would clear "speaking".
        try:
            running_state = self._sapi_voice.Status.RunningState
        except Exception as error:
            self.error_occurred.emit(str(error))
            self._using_sapi_direct = False
            self._set_state("ready")
            return
        if running_state == 1:  # SRSEDone: not speaking and not paused
            self._using_sapi_direct = False
            self._set_state("ready")

    def can_save_to_file(self) -> bool:
        return IS_WINDOWS and self._sapi_voice is not None

    def save_to_file(self, text: str, output_path: str, use_pitch_xml: bool = False, pitch_middle: int = 0) -> bool:
        if not self.can_save_to_file():
            raise RuntimeError(_("Saving speech to a file requires the Windows SAPI5 engine."))

        import pythoncom
        import win32com.client
        from win32com.client import gencache

        # This may run on a worker thread (SaveSpeechJob). self._sapi_voice was created
        # on the main thread's STA apartment, so it can't safely be reused here — call
        # cross-apartment without marshaling and SAPI either raises or silently misbehaves.
        # Initialize a fresh apartment plus a fresh SpVoice local to whichever thread
        # actually runs this method.
        com_initialized = False
        try:
            pythoncom.CoInitialize()
            com_initialized = True
        except pythoncom.com_error:
            pass

        try:
            voice = gencache.EnsureDispatch("SAPI.SpVoice")
            self._select_sapi_voice(voice, self._voice_name)

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

                voice.AudioOutputStream = stream

                speak_text = wrap_pitch_xml(text, pitch_middle) if use_pitch_xml else text
                flags = 8 if use_pitch_xml else 0  # IsXML
                voice.Speak(speak_text, flags)
            finally:
                stream.Close()

            if needs_transcode:
                try:
                    self._transcode(wav_path, output_path)
                finally:
                    os.remove(wav_path)
        finally:
            if com_initialized:
                pythoncom.CoUninitialize()

        return True

    @staticmethod
    def _transcode(wav_path: str, output_path: str):
        from tools.ffmpeg_handler import FFmpegHandler
        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        ffmpeg.input(wav_path).output(output_path)
        ffmpeg.execute()

    def _on_state_changed(self, state):
        if self._using_sapi_direct:
            # SpVoice is the one speaking, so Qt's Ready for a queued-up Qt
            # utterance would otherwise end the direct one's state mid-sentence.
            return
        labels = {
            QTextToSpeech.State.Ready: "ready",
            QTextToSpeech.State.Speaking: "speaking",
            QTextToSpeech.State.Paused: "paused",
            QTextToSpeech.State.Error: "error",
        }
        self._set_state(labels.get(state, "ready"))
        if state == QTextToSpeech.State.Error:
            self.error_occurred.emit(self.tts.errorString())
