import speech_core
import queue
from PySide6.QtCore import QThread, Signal


class SpeechWorker(QThread):
    def __init__(self, speech_manager):
        super().__init__()
        self.speech_manager = speech_manager
        self._speech_queue = queue.Queue()
        self._running = False
    
    def run(self):
        self._running = True
        while self._running:
            try:
                text, interrupt = self._speech_queue.get(timeout=0.1)
                try:
                    self.speech_manager._output_direct(text, interrupt)
                except:
                    pass
                self._speech_queue.task_done()
            except queue.Empty:
                continue
            except:
                break
    
    def add_to_queue(self, text, interrupt):
        if interrupt:
            with self._speech_queue.mutex:
                self._speech_queue.queue.clear()
        self._speech_queue.put((text, interrupt))
    
    def stop(self):
        self._running = False


class SpeechManager(speech_core.SpeechCore):


    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_queue()
        return cls._instance
    
    def _init_queue(self):
        self._worker = None
        self._running = False
    
    def start_queue(self):
        if not self._running:
            self._running = True
            self._worker = SpeechWorker(self)
            self._worker.start()
    
    def stop_queue(self):
        self._running = False
        if self._worker:
            self._worker.stop()
            self._worker.wait(1000)
    
    def _output_direct(self, text, interrupt):
        return super().output(text, interrupt)
    
    def output(self, text, interrupt=False):
        if hasattr(self, '_worker') and self._worker and self._running:
            self._worker.add_to_queue(text, interrupt)
            return True
        else:
            return super().output(text, interrupt)
    
    def find_voice_by_name(self, voice_name):
        if not voice_name:
            return -1
        try:
            voice_count = self.get_voices()
            for i in range(voice_count):
                current_voice = self.get_voice(i)
                if current_voice == voice_name:
                    return i
        except:
            pass
        return -1

speech_manager = SpeechManager()