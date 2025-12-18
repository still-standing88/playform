from __future__ import annotations

import sys
import logging
import logging.handlers
import faulthandler
import traceback
from pathlib import Path
from datetime import datetime

from utilities import get_app_path
from .handlers import QTextEditLogHandler

class LoggingSetup:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LoggingSetup, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_dir: Path | None = None, console_widget=None):
        if hasattr(self, 'initialized') and self.initialized:
            if console_widget and not hasattr(self, 'console_handler'):
                 self.add_console_handler(console_widget)
            return
            
        app_path = Path(get_app_path())
        self.log_dir = Path(log_dir) if log_dir else app_path / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.console_widget = console_widget

        self.error_log_file = self.log_dir / "errors.log"
        self.fault_log_file = self.log_dir / "faults.log"

        self.setup_logging()
        self.setup_fault_handler()
        self.setup_exception_handlers()
        self.initialized = True

    def setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        self.logger = logging.getLogger("AppLogger")
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        if not any(isinstance(h, logging.handlers.RotatingFileHandler) and getattr(h, 'baseFilename', '') == str(self.error_log_file) for h in root_logger.handlers):
            root_logger.addHandler(file_handler)
            
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) and getattr(h, 'baseFilename', '') == str(self.error_log_file) for h in self.logger.handlers):
            self.logger.addHandler(file_handler)
            
        if self.console_widget:
            self.add_console_handler(self.console_widget)

    def add_console_handler(self, console_widget):
        self.console_widget = console_widget
        root_logger = logging.getLogger()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler = QTextEditLogHandler(self.console_widget)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        if not any(isinstance(h, QTextEditLogHandler) for h in root_logger.handlers):
            root_logger.addHandler(console_handler)
            self.console_handler = console_handler

    def setup_fault_handler(self):
        try:
            self.fault_file = open(self.fault_log_file, 'a', encoding='utf-8', errors='replace')
            faulthandler.enable(file=self.fault_file, all_threads=True)
            self.fault_file.write(f"\n{'='*50}\n")
            self.fault_file.write(f"Application started - {datetime.now().isoformat()}\n")
            self.fault_file.write(f"{'='*50}\n")
            self.fault_file.flush()
        except Exception as e:
            print(f"Failed to setup fault handler: {e}")

    def setup_exception_handlers(self):
        self.original_excepthook = sys.excepthook
        sys.excepthook = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.logger.error(f"Uncaught exception:\n{error_msg}")

        try:
            with open(self.error_log_file, 'a', encoding='utf-8', errors='replace') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"UNCAUGHT EXCEPTION - {datetime.now().isoformat()}\n")
                f.write(f"{'='*50}\n")
                f.write(error_msg)
                f.write(f"\n{'='*50}\n")
        except Exception as e:
            print(f"Failed to write exception log: {e}")

        self.original_excepthook(exc_type, exc_value, exc_traceback)

    def cleanup(self):
        if hasattr(self, 'fault_file') and self.fault_file:
            try:
                self.fault_file.write(f"\n{'='*50}\n")
                self.fault_file.write(f"Application closed - {datetime.now().isoformat()}\n")
                self.fault_file.write(f"{'='*50}\n")
                self.fault_file.close()
            except:
                pass
                
        if hasattr(self, 'console_handler'):
            try:
                root_logger = logging.getLogger()
                root_logger.removeHandler(self.console_handler)
            except:
                pass

    @staticmethod
    def get_logger():
        return logging.getLogger("AppLogger")
