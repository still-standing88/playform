import platform
from . import prefs
from utilities.speech import speech_manager


def load_speech_config():
    if platform.system() == "Windows":
        speech_manager.prefer_sapi(prefs.prefs.get("tts_prefer_sapi", True))

    speech_manager.set_rate(prefs.prefs.get("tts_rate", 1.0))
    speech_manager.set_volume(prefs.prefs.get("tts_volume", 100.0))


prefs.initialize()