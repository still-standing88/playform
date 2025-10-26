import logging
import logging.handlers
import faulthandler
import sys
import os
import traceback
import threading

from pathlib import Path
from datetime import datetime

class GlobalErrorHandler:
    
    
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.error_log_file = self.log_dir / "errors.log"
        self.crash_log_file = self.log_dir / "crashes.log"
        
        self.setup_logging()
        self.setup_fault_handler()
        self.setup_exception_handler()
        self.setup_qt_logging()
        
    def setup_logging(self):
        self.logger = logging.getLogger("GlobalErrorLogger")
        self.logger.setLevel(logging.ERROR)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        file_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
    def setup_fault_handler(self):
        fault_log_file = self.log_dir / "faults.log"
        try:
            self.fault_file = open(fault_log_file, 'a')
            faulthandler.enable(file=self.fault_file, all_threads=True)
        except Exception as e:
            self.logger.error(f"Failed to setup fault handler: {e}")
            
    def setup_exception_handler(self):
        sys.excepthook = self.handle_exception
        threading.excepthook = self.handle_thread_exception
        
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.logger.error(f"Uncaught exception: {error_msg}")
        self.log_crash(exc_type, exc_value, exc_traceback)
        
    def handle_thread_exception(self, args):
        error_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        self.logger.error(f"Uncaught thread exception: {error_msg}")
        self.log_crash(args.exc_type, args.exc_value, args.exc_traceback)
        
    def log_crash(self, exc_type, exc_value, exc_traceback):
        try:
            with open(self.crash_log_file, 'a') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"CRASH REPORT - {datetime.now().isoformat()}\n")
                f.write(f"{'='*50}\n")
                f.write("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                f.write(f"\n{'='*50}\n")
        except Exception as e:
            print(f"Failed to write crash log: {e}")
            
    def log_error(self, message, exception=None):
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(message)
            
    def setup_qt_logging(self):
        try:
            from PySide6 import QtCore
            def handler(msg_type, context, message):
                if msg_type == QtCore.QtMsgType.QtDebugMsg:
                    lvl = logging.DEBUG
                elif msg_type == QtCore.QtMsgType.QtInfoMsg:
                    lvl = logging.INFO
                elif msg_type == QtCore.QtMsgType.QtWarningMsg:
                    lvl = logging.WARNING
                elif msg_type == QtCore.QtMsgType.QtCriticalMsg:
                    lvl = logging.ERROR
                elif msg_type == QtCore.QtMsgType.QtFatalMsg:
                    lvl = logging.CRITICAL
                else:
                    lvl = logging.ERROR
                self.logger.log(lvl, f"Qt: {message}")
            QtCore.qInstallMessageHandler(handler)
        except Exception as e:
            self.logger.error(f"Failed to setup Qt message handler: {e}")
            
    def cleanup(self):
        if hasattr(self, 'fault_file') and self.fault_file:
            try:
                self.fault_file.close()
            except:
                pass

error_handler = GlobalErrorHandler()

def log_error(message, exception=None):
    error_handler.log_error(message, exception)

def cleanup_logging():
    error_handler.cleanup()
