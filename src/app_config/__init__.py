import platform
from . import prefs
from utilities.speech import speech_manager


def load_speech_config():
    prefer_sapi = prefs.prefs.get("tts_prefer_sapi", False)
    
    if platform.system() == "Windows":
        speech_manager.prefer_sapi(prefer_sapi)
    
    try:
        speech_manager.detect_driver()
    except:
        pass
    
    voice_name = prefs.prefs.get("tts_voice", "")
    if voice_name:
        if platform.system() == "Windows":
            if prefer_sapi:
                voice_index = speech_manager.find_voice_by_name(voice_name)
                if voice_index >= 0:
                    try:
                        speech_manager.set_voice(voice_index)
                    except:
                        pass
        else:
            voice_index = speech_manager.find_voice_by_name(voice_name)
            if voice_index >= 0:
                try:
                    speech_manager.set_voice(voice_index)
                except:
                    pass
    
    try:
        speech_manager.set_rate(prefs.prefs.get("tts_rate", 1.0))
        speech_manager.set_volume(prefs.prefs.get("tts_volume", 80.0))
    except:
        pass
    
    speech_manager.start_queue()


prefs.initialize()