from __future__ import annotations

import logging
from app_constance.styles import COLORS

class QTextEditLogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        try:
            msg = self.format(record)
            if hasattr(self.text_widget, "setTextColor"):
                if record.levelno >= logging.ERROR:
                    self.text_widget.setTextColor(COLORS['red'])
                elif record.levelno >= logging.WARNING:
                    self.text_widget.setTextColor(COLORS['orange'])
                else:
                    self.text_widget.setTextColor(COLORS['lightgray'])
                    
            if hasattr(self.text_widget, "appendPlainText"):
                self.text_widget.appendPlainText(msg)
            elif hasattr(self.text_widget, "append"):
                self.text_widget.append(msg)
                
            if hasattr(self.text_widget, "setTextColor"):
                self.text_widget.setTextColor(COLORS['white'])
        except Exception:
            pass

class LoggingStreamRedirect:
    def __init__(self, widget, original_stream, logger, is_stderr: bool = False):
        self.widget = widget
        self.original_stream = original_stream
        self.logger = logger
        self.is_stderr = is_stderr

    def write(self, text):
        if not text:
            return

        try:
            self.original_stream.write(text)
            self.original_stream.flush()
        except Exception:
            pass

        display_text = text.rstrip("\r\n")
        if hasattr(self.widget, "appendPlainText"):
            self.widget.appendPlainText(display_text)
        elif hasattr(self.widget, "append"):
            if self.is_stderr and hasattr(self.widget, "setTextColor"):
                self.widget.setTextColor(COLORS['red'])
            self.widget.append(display_text)
            if self.is_stderr and hasattr(self.widget, "setTextColor"):
                self.widget.setTextColor(COLORS['black'])

        for line in text.splitlines():
            if line:
                if self.is_stderr:
                    self.logger.error(line)
                else:
                    self.logger.info(line)

    def flush(self):
        self.original_stream.flush()
