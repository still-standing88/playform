import sys
import logging
import logging.handlers
import faulthandler
import traceback
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QPlainTextEdit, QTextBrowser, QTabWidget, QLabel
from PySide6.QtCore import Qt


class LoggingStreamRedirect:
    def __init__(self, widget, original_stream, logger, is_stderr=False):
        self.widget = widget
        self.original_stream = original_stream
        self.logger = logger
        self.is_stderr = is_stderr
        
    def write(self, text):
        if text.strip():
            if isinstance(self.widget, QPlainTextEdit):
                self.widget.appendPlainText(text.strip())
            elif isinstance(self.widget, (QTextEdit, QTextBrowser)):
                if self.is_stderr:
                    self.widget.setTextColor(Qt.red)
                self.widget.append(text.strip())
                if self.is_stderr:
                    self.widget.setTextColor(Qt.black)
            
            self.original_stream.write(text)
            self.original_stream.flush()
            
            if self.is_stderr:
                self.logger.error(text.strip())
            else:
                self.logger.info(text.strip())
    
    def flush(self):
        self.original_stream.flush()


class LoggingSetup:
    def __init__(self, log_dir=None):
        self.log_dir = Path(log_dir) if log_dir else Path.cwd() / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        self.error_log_file = self.log_dir / "errors.log"
        self.fault_log_file = self.log_dir / "faults.log"
        
        self.setup_logging()
        self.setup_fault_handler()
        self.setup_exception_handlers()
        
    def setup_logging(self):
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
        self.logger.addHandler(file_handler)
        
    def setup_fault_handler(self):
        try:
            self.fault_file = open(self.fault_log_file, 'a')
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
            with open(self.error_log_file, 'a') as f:
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


class MainWindow(QMainWindow):
    def __init__(self, logging_setup):
        super().__init__()
        self.logging_setup = logging_setup
        self.setWindowTitle("Screen Reader Accessibility Test with Logging")
        self.setGeometry(100, 100, 900, 700)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        info = QLabel(f"Test each tab with your screen reader. Logs saved to: {logging_setup.log_dir}")
        layout.addWidget(info)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.output1 = QTextEdit()
        self.output1.setReadOnly(True)
        self.output1.setAccessibleName("QTextEdit Output Console")
        self.output1.setAccessibleDescription("Standard QTextEdit widget")
        self.tabs.addTab(self.output1, "QTextEdit (Default)")
        
        self.output2 = QPlainTextEdit()
        self.output2.setReadOnly(True)
        self.output2.setAccessibleName("QPlainTextEdit Output Console")
        self.output2.setAccessibleDescription("QPlainTextEdit widget - better line navigation")
        self.tabs.addTab(self.output2, "QPlainTextEdit")
        
        self.output3 = QTextBrowser()
        self.output3.setAccessibleName("QTextBrowser Output Console")
        self.output3.setAccessibleDescription("QTextBrowser widget - designed for read-only")
        self.tabs.addTab(self.output3, "QTextBrowser")
        
        self.output4 = QTextEdit()
        self.output4.setReadOnly(True)
        self.output4.setTextInteractionFlags(Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse)
        self.output4.setAccessibleName("QTextEdit with Keyboard Selection")
        self.output4.setAccessibleDescription("QTextEdit with explicit keyboard selection enabled")
        self.tabs.addTab(self.output4, "QTextEdit + Selection")
        
        self.output5 = QPlainTextEdit()
        self.output5.setReadOnly(True)
        self.output5.setTextInteractionFlags(Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse)
        self.output5.setAccessibleName("QPlainTextEdit with Keyboard Selection")
        self.output5.setAccessibleDescription("QPlainTextEdit with explicit keyboard selection")
        self.tabs.addTab(self.output5, "QPlainTextEdit + Selection")
        
        btn_layout = QHBoxLayout()
        
        print_btn = QPushButton("Print Statement")
        print_btn.clicked.connect(self.do_print)
        btn_layout.addWidget(print_btn)
        
        multiline_btn = QPushButton("Print Multiple Lines")
        multiline_btn.clicked.connect(self.do_multiline)
        btn_layout.addWidget(multiline_btn)
        
        error_btn = QPushButton("Trigger Error")
        error_btn.clicked.connect(self.do_error)
        btn_layout.addWidget(error_btn)
        
        crash_btn = QPushButton("Trigger Crash")
        crash_btn.clicked.connect(self.do_crash)
        btn_layout.addWidget(crash_btn)
        
        clear_btn = QPushButton("Clear Current Tab")
        clear_btn.clicked.connect(self.clear_current)
        btn_layout.addWidget(clear_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_all_btn)
        
        layout.addLayout(btn_layout)
        
        self.all_outputs = [self.output1, self.output2, self.output3, self.output4, self.output5]
        
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        self.stdout_redirect = LoggingStreamRedirect(
            self.output1, 
            self.original_stdout, 
            logging_setup.logger,
            is_stderr=False
        )
        self.stderr_redirect = LoggingStreamRedirect(
            self.output1, 
            self.original_stderr, 
            logging_setup.logger,
            is_stderr=True
        )
        
        sys.stdout = self.stdout_redirect
        sys.stderr = self.stderr_redirect
        
        self.tabs.currentChanged.connect(self.on_tab_change)
        
        print("Application started - streams redirected to GUI and logs")
        print("Use arrow keys to navigate text in each tab")
        
    def write_to_all(self, text, is_stderr=False):
        for output in self.all_outputs:
            if isinstance(output, QPlainTextEdit):
                output.appendPlainText(text)
            elif isinstance(output, (QTextEdit, QTextBrowser)):
                if is_stderr:
                    output.setTextColor(Qt.red)
                output.append(text)
                if is_stderr:
                    output.setTextColor(Qt.black)
                
    def on_tab_change(self, index):
        current = self.all_outputs[index]
        self.stdout_redirect.widget = current
        self.stderr_redirect.widget = current
        
    def do_print(self):
        print("This is a normal print statement")
        print(f"Current tab: {self.tabs.tabText(self.tabs.currentIndex())}")
        
    def do_multiline(self):
        print("Line 1: First line of output")
        print("Line 2: Second line of output")
        print("Line 3: Third line of output")
        print("Line 4: Fourth line of output")
        print("Line 5: Fifth line of output")
        
    def do_error(self):
        try:
            result = 1 / 0
        except Exception as e:
            print(f"Caught error: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            
    def do_crash(self):
        print("About to trigger an uncaught exception...")
        raise RuntimeError("This is an intentional crash for testing")
        
    def clear_current(self):
        current = self.all_outputs[self.tabs.currentIndex()]
        current.clear()
        if isinstance(current, QPlainTextEdit):
            current.appendPlainText(f"Cleared {self.tabs.tabText(self.tabs.currentIndex())}")
        else:
            current.append(f"Cleared {self.tabs.tabText(self.tabs.currentIndex())}")
        
    def clear_all(self):
        for output in self.all_outputs:
            output.clear()
        self.write_to_all("All outputs cleared")
        
    def closeEvent(self, event):
        print("Application closing...")
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.logging_setup.cleanup()
        event.accept()


if __name__ == "__main__":
    logging_setup = LoggingSetup()
    
    app = QApplication(sys.argv)
    
    try:
        window = MainWindow(logging_setup)
        window.show()
        exit_code = app.exec()
        logging_setup.cleanup()
        sys.exit(exit_code)
    except Exception as e:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        print(f"Error starting application: {e}")
        traceback.print_exc()
        logging_setup.cleanup()