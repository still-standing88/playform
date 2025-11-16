import speech_core


class SpeechManager(speech_core.SpeechCore):


    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

speech_manager = SpeechManager()