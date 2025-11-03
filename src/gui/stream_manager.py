import sys
import logging
from typing import Optional, List, Callable
from PySide6.QtCore import QObject, Signal


class MultiStreamRedirect(QObject):
    text_written = Signal(str, bool)
    
    def __init__(self, original_stream, is_stderr=False):
        super().__init__()
        self.original_stream = original_stream
        self.is_stderr = is_stderr
        self.callbacks: List[Callable[[str, bool], None]] = []
        
    def add_callback(self, callback: Callable[[str, bool], None]):
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            
    def remove_callback(self, callback: Callable[[str, bool], None]):
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            
    def write(self, text):
        if text.strip():
            self.text_written.emit(text, self.is_stderr)
            for callback in self.callbacks:
                try:
                    callback(text, self.is_stderr)
                except Exception:
                    pass
                    
        self.original_stream.write(text)
        self.original_stream.flush()
    
    def flush(self):
        self.original_stream.flush()


class StreamManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
            
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.stdout_redirect: Optional[MultiStreamRedirect] = None
        self.stderr_redirect: Optional[MultiStreamRedirect] = None
        self.is_active = False
        self._initialized = True
        
    def start_redirection(self):
        if self.is_active:
            return
            
        self.stdout_redirect = MultiStreamRedirect(self.original_stdout, is_stderr=False)
        self.stderr_redirect = MultiStreamRedirect(self.original_stderr, is_stderr=True)
        
        sys.stdout = self.stdout_redirect
        sys.stderr = self.stderr_redirect
        
        self.is_active = True
        
    def stop_redirection(self):
        if not self.is_active:
            return
            
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        self.stdout_redirect = None
        self.stderr_redirect = None
        self.is_active = False
        
    def add_stdout_callback(self, callback: Callable[[str, bool], None]):
        if self.stdout_redirect:
            self.stdout_redirect.add_callback(callback)
            
    def add_stderr_callback(self, callback: Callable[[str, bool], None]):
        if self.stderr_redirect:
            self.stderr_redirect.add_callback(callback)
            
    def remove_stdout_callback(self, callback: Callable[[str, bool], None]):
        if self.stdout_redirect:
            self.stdout_redirect.remove_callback(callback)
            
    def remove_stderr_callback(self, callback: Callable[[str, bool], None]):
        if self.stderr_redirect:
            self.stderr_redirect.remove_callback(callback)
            
    def get_stdout_redirect(self) -> Optional[MultiStreamRedirect]:
        return self.stdout_redirect
        
    def get_stderr_redirect(self) -> Optional[MultiStreamRedirect]:
        return self.stderr_redirect


class DebugStreamHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.stream_manager = StreamManager()
        
    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                sys.stderr.write(msg + '\n')
            else:
                sys.stdout.write(msg + '\n')
        except Exception:
            self.handleError(record)


stream_manager = StreamManager()