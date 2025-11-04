from __future__ import annotations

import sys
import logging
import logging.handlers
import faulthandler
import traceback
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QDockWidget,
    QLabel,
)

from utilities import get_app_path
from app_constance.styles import COLORS


class QTextEditLogHandler(logging.Handler):
    """Custom logging handler that writes to a QTextEdit widget."""
    
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


class LoggingSetup:
    def __init__(self, log_dir: Path | None = None, console_widget=None):
        app_path = Path(get_app_path())
        self.log_dir = Path(log_dir) if log_dir else app_path / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.console_widget = console_widget

        self.error_log_file = self.log_dir / "errors.log"
        self.fault_log_file = self.log_dir / "faults.log"

        self.setup_logging()
        self.setup_fault_handler()
        self.setup_exception_handlers()

    def setup_logging(self):
        # Get root logger to capture all logging across the app
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Also keep AppLogger reference for backward compatibility
        self.logger = logging.getLogger("AppLogger")
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler for logging to file
        file_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # Add file handler to root logger if not already present
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) and getattr(h, 'baseFilename', '') == str(self.error_log_file) for h in root_logger.handlers):
            root_logger.addHandler(file_handler)
            
        # Also add to AppLogger for backward compatibility
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) and getattr(h, 'baseFilename', '') == str(self.error_log_file) for h in self.logger.handlers):
            self.logger.addHandler(file_handler)
            
        # Add console widget handler if provided
        if self.console_widget:
            console_handler = QTextEditLogHandler(self.console_widget)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            
            # Add to root logger to capture all loggers
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
                
        # Remove console handler from root logger
        if hasattr(self, 'console_handler'):
            try:
                root_logger = logging.getLogger()
                root_logger.removeHandler(self.console_handler)
            except:
                pass


class DebugConsoleDock(QDockWidget):

    def __init__(self, parent=None):
        super().__init__("Debug Console", parent)

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        info = QLabel("Console output. Tab key won't insert tabs inside editor.")
        layout.addWidget(info)


        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.console.setTabChangesFocus(True)
        self.console.setAccessibleName("Console Output")
        self.console.setAccessibleDescription("Read-only console output viewer")
        layout.addWidget(self.console, 1)


        # Pass console widget to LoggingSetup so logger messages appear in console
        self.logging_setup = LoggingSetup(console_widget=self.console)


        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        self.stdout_redirect = LoggingStreamRedirect(self.console, self.original_stdout, self.logging_setup.logger, is_stderr=False)
        self.stderr_redirect = LoggingStreamRedirect(self.console, self.original_stderr, self.logging_setup.logger, is_stderr=True)

        sys.stdout = self.stdout_redirect
        sys.stderr = self.stderr_redirect

        print("Debug console initialized.")



        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)



    def closeEvent(self, event):  # type: ignore[override]

        try:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
        except Exception:
            pass
        try:
            self.logging_setup.cleanup()
        except Exception:
            pass
        super().closeEvent(event)
