# Project Snapshot: src

Generated on: The current date is: Tue 09/23/2025 
Enter the new date: (mm-dd-yy)

## Table of Contents

- [Directory: app_config](#directory-app_config)
- [Directory: app_constance](#directory-app_constance)
- [Directory: app_db](#directory-app_db)
- [Directory: data](#directory-data)
- [Directory: data\file_marks](#directory-data\file_marks)
- [Directory: data\playlists](#directory-data\playlists)
- [Directory: EXPLORER](#directory-explorer)
- [Directory: files-rc](#directory-files-rc)
- [Directory: gui](#directory-gui)
- [Directory: gui_controls](#directory-gui_controls)
- [Directory: player](#directory-player)
- [Directory: playlist_manager](#directory-playlist_manager)
- [Directory: Screen Shots](#directory-screen-shots)
- [Directory: tools](#directory-tools)
- [Directory: utilities](#directory-utilities)

## Files


<a name="directory-root"></a>
### Directory: `Root`


#### File: `app.py`

```python
import os, sys, logging
import PySide6

from utilities.functions import get_app_path, get_parent_dir

#qt_path= os.path.dirname(PySide6.__file__)
#os.environ['QT_PLUGIN_PATH'] = os.path.join(qt_path, "qt-plugins")
os.environ["MPV_LIB_PATH"] = os.path.join(get_parent_dir(), "lib")
os.environ["USE_MPV"] = "1"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPalette, QColor
from pathlib import Path

import app_guard
import av_play
import app_config
import app_db

from llog_handler import log_error, cleanup_logging
from app_config import key_config
from gui.main_window import MainWindow

def setup_application_style(app: QApplication):
    app.setStyle('Fusion')
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(50, 50, 50))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))

    dark_palette.setColor(QPalette.ColorRole.Button, QColor(80, 80, 80))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))

    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(120, 120, 120))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))

    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

    app.setPalette(dark_palette)


def main():
    if getattr(sys, 'frozen', False):
        BASE_DIR = Path(sys.executable).parent
        os.environ['QT_PLUGIN_PATH'] = str(BASE_DIR / "PySide6" / "qt-plugins")
    else:
        BASE_DIR = Path(__file__).parent

    try:
        cli_args = sys.argv
        app_instance = app_guard.AppGuard()
        app = QApplication(sys.argv)

        app_instance.init("PlayForm", lambda: None, False)
        if not app_instance.is_primary_instance():
            if cli_args:
                app_instance.send_msg_request("cli-args", cli_args[1])
            app_instance.focus_window("PlayForm")
            app_instance.release()
            sys.exit(0)

        def release():
            app_instance.release()

        app.setApplicationName("PlayForm")
        app.setApplicationVersion("1.0.0")
        app.aboutToQuit.connect(release)
        setup_application_style(app)
        import locale
        locale.setlocale(locale.LC_NUMERIC, 'C')
        key_config.load_keys()

        window = MainWindow()
        cli_args_msg:app_guard.IPCMsg = app_instance.create_ipc_msg("cli-args",
            lambda data: QTimer.singleShot(0, lambda: window.cli_load_file(data))
        )
        app_instance.register_msg(cli_args_msg)

        if len(cli_args) > 1:
            window.play_file(cli_args[1])
            app_instance.focus_window("PlayForm")

        key_config.initialize(window.global_hotkeys)
        window.show()
        exit_code = app.exec()

    except Exception as e:
        exc_t = sys.exc_info()[2]
        raise Exception(f"Error: {e}").with_traceback(exc_t)
        log_error(f"Critical error in main application{e}", )
        exit_code = 1

    finally:
        cleanup_logging()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
```

#### File: `llog_handler.py`

```python
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
```

#### File: `loading.py`

```python
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QDialog

class Worker(QThread):
    finished = Signal()
    def __init__(self, method):
        super().__init__()
        self.method = method

    def run(self):
        self.method()

class loadingDialog(QDialog):
    onLoadFinished = Signal()

    def __init__(self, method, parent=None):
        super().__init__(parent)
        self.method = method
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle("Loading")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(200, 200)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.ui()
        self.Layout()

        self.worker = Worker(self.method)
        self.worker.finished.connect(self.onFinished)

    def ui(self):
        self.label = QLabel("loading", self)

    def Layout(self):
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.label)

    def begin(self):
        self.show()
        self.worker.start()

    def onFinished(self):
        self.onLoadFinished.emit()
        self.close()

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_Escape, Qt.Key_F4] and (event.modifiers() & Qt.AltModifier):
            return
        super().keyPressEvent(event)

    def closeEvent(self,event):
        if self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
```

#### File: `project_snapshot.md`

```markdown

```

#### File: `xx.py`

```python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit
from PySide6.QtCore import Qt
import pyttsx3

# Initialize the text-to-speech engine
engine = pyttsx3.init()

class KeySpeaker(QMainWindow):
    """
    A simple PySide6 application that speaks the name of the pressed key.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Key Speaker")
        self.setGeometry(100, 100, 400, 200)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Press any key to hear its name...")
        self.text_edit.setReadOnly(True)  # Make it read-only
        self.setCentralWidget(self.text_edit)

        # Set the central widget to receive key events
        self.text_edit.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        """
        Overrides the keyPressEvent to handle key presses.
        """
        # Get the key code from the event
        key = event.key()

        # Check for special keys and their string names
        if key == Qt.Key_Space:
            key_name = "Space"
        elif key == Qt.Key_Enter or key == Qt.Key_Return:
            key_name = "Enter"
        elif key == Qt.Key_Backspace:
            key_name = "Backspace"
        elif key == Qt.Key_Escape:
            key_name = "Escape"
        elif key == Qt.Key_Shift:
            key_name = "Shift"
        elif key == Qt.Key_Control:
            key_name = "Control"
        elif key == Qt.Key_Alt:
            key_name = "Alt"
        elif key == Qt.Key_Tab:
            key_name = "Tab"
        elif key == Qt.Key_PageUp:
            key_name = "Page Up"
        elif key == Qt.Key_PageDown:
            key_name = "Page Down"
        else:
            # For other keys, get the text from the event
            key_name = event.text()
            if key_name.isspace() or key_name == '':
                # If the text is empty or a space (already handled),
                # get the key name from the key code
                key_name = Qt.Key(key).name

        # Speak the name of the key
        if key_name and key_name.strip():
            engine.say(f"{key_name}")
            engine.runAndWait()

            # Update the text edit with the spoken key
            current_text = self.text_edit.toPlainText()
            self.text_edit.setPlainText(f"Pressed: {key_name}\n{current_text}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = KeySpeaker()
    window.show()
    sys.exit(app.exec())
```

<a name="directory-app_config"></a>
### Directory: `app_config`


#### File: `app_config\__init__.py`

```python
from . import prefs

prefs.initialize()
```

#### File: `app_config\key_config.py`

```python
import os
import re
#import keyboard
import configparser as cfgp

from utilities.functions import get_app_path
from app_constance import default_keys

key_dict = default_keys.key_dict.copy()
hotkeys = {}
hotkeys_funcs = {}
key_config = cfgp.ConfigParser()

def modifyKey(section,hotkey,sequence):
    key_config[section][hotkey] = sequence
    if section == "global":
        pass #keyboard.remove_hotkey(hotkeys.pop(hotkey))
        #hotkeys[hotkey] = keyboard.add_hotkey(sequence,hotkeys_funcs[hotkey])
        

def is_valid_hotkey(hotkey):
    pattern = r"(alt|ctrl|shift|win)?\+?(alt|ctrl|shift|win)?\+?(alt|ctrl|shift|win)?\+?(space|enter|left|right|up|down|pageup|pagedown|home|end|\[|\]|f1|f2|f3|f4|f5|f6|f7|f8|f9|f10|f11|f12|\w)?"
    match = re.match(pattern, hotkey.replace(" ","").lower())
    return bool(match)

def keysToDefault():
    global key_config
    for keyset,keys in key_dict.items():
        key_config[keyset] = {}
        for key  in keys:
            key_config[keyset][key] = keys[key]

def saveConfig():
    key_config_file = f"{os.getcwd()}\\data\\key_config.cfg"
    with open(key_config_file, "w") as config_file:
        key_config.write(config_file)

def load_keys():
    current_path = get_app_path()
    key_config_file = f"{current_path}/data/key_config.cfg"
    if os.path.exists(key_config_file) == True: 
        key_config.read(key_config_file)
    else:
        keysToDefault()
        with open(key_config_file,"w") as config_file:
            key_config.write(config_file)

def apply_global_hotkeys():
    #for hotkey in hotkeys:
        #keyboard.remove_hotkey(hotkeys[hotkey])
    hotkeys.clear()
    #for hotkey in key_dict["Global"]:
        #hotkeys[hotkey] = keyboard.add_hotkey(key_config["Global"][hotkey],hotkeys_funcs[hotkey])

def initialize(func_dict):
    global hotkeys_funcs
    hotkeys_funcs = func_dict
```

#### File: `app_config\prefs.py`

```python
import os, sys, shutil, json

from utilities.functions import get_parent_dir, hexify,dehexify, user_path, get_app_path
from app_constance import prefs_dict

prefs = prefs_dict.prefs.copy()
current_path = get_app_path()
sc_path = f"{current_path}/Screen Shots/"
data_path = f"{current_path}/data/"
marks_path = f"{data_path}/file_marks/"
playlist_path = f"{data_path}/playlists"
prefs_file = os.path.join(data_path, "prefs.json")


def processData(path,mode,data="", target=""):
    if mode == "read":
        with open(path,"r") as file:
            tstrS = file.readlines()
            tstr = []
            for line in range(0,len(tstrS)-1+1):
                if tstrS[line]: tstr.append(dehexify(tstrS[line]))

        dstr = ""
        for line in tstr:
            dstr += line+"\n"
            pstr = json.loads(dstr)
            global prefs
            prefs = pstr

    elif mode == "write":
        with open(path,"w") as file:
            tstr = hexify(json.dumps(data))
            file.write(tstr)

    elif mode == "delete":
        with open(path,"w") as file:
            file.write("")

def save():        
    processData(prefs_file, "write", prefs)


def ffmpegbin():
    current_path = get_parent_dir()
    import pyffmpeg

    if prefs["ffmpeg_binary"] == "" or not os.path.exists(prefs["ffmpeg_binary"]):
        if not os.path.exists(f"{current_path}/bin/") : os.makedirs(f"{current_path}/bin/")
        ff = pyffmpeg.FFmpeg()
        ff.enable_log = False
        bin_path = ff.get_ffmpeg_bin()
        dest_path = f"{current_path}/bin/"
        shutil.copy(bin_path,dest_path)
        bin_dir = os.path.dirname(bin_path)
        ff.quit()
        del ff
        shutil.rmtree(bin_dir)
        prefs["ffmpeg_binary"] = f"{dest_path}/{os.path.split(bin_path)[1]}"
        save()

def initialize():
    if not os.path.exists(data_path): os.makedirs(data_path)
    if not os.path.exists(sc_path): os.makedirs(sc_path)
    if not os.path.exists(playlist_path): os.makedirs(playlist_path)
    if not os.path.exists(marks_path): os.makedirs(marks_path)
    if os.path.exists(prefs_file):
        processData(prefs_file, "read")
    elif not os.path.exists(prefs_file):
        save()
    ffmpegbin()
```

<a name="directory-app_constance"></a>
### Directory: `app_constance`


#### File: `app_constance\__init__.py`

```python

```

#### File: `app_constance\default_keys.py`

```python
key_dict = {
"Global": {
"Play/Pause":"Ctrl+Win+P",
"Mute/Unmute":"Ctrl+Win+M",
"Volume Down":"Ctrl+Win+F7",
"Volume Up":"Ctrl+Win+F8",
"Previous":"Ctrl+Win+F9",
"Next":"Ctrl+Win+F10"
},
"Main interface": {
"Hotkeys dialog": "F4",
"Open file": "Ctrl+O",
"Close file": "Ctrl+W",
"Close all": "Ctrl+Shift+w",
"Show/Hide explorer": "Ctrl+Alt+B",
"Show/Hide player controls": "Ctrl+H",
"Hide window": "Alt+H",
"Exit": "Alt+X",
"Open URL":"Ctrl+U",
"Documentation":"F1",
"Prefrences Dialog":"Ctrl+P"
},
"Explorer": {
"Play/Pause": "Space",
"Backward": "left",
"Forward": "right",
"Stop": "Ctrl+Space"
},
"Player": {
"Play/Pause": "Space",
"Backward": "left",
"Forward": "right",
"Stop": "Ctrl+Space",
"Mute/Unmute":"M",
"Previous": "PageUp",
"Next": "PageDown",
"Jump to beginning": "Home",
"Jump to the end": "End",
"Toggle repeat": "Ctrl+r",
"Volume up": "up",
"Volume down": "down",
"Bookmarks list": "Ctrl+B",
"New mark at current position": "K",
"Repeat loop start": "[",
"Repeat loop end": "]",
"Clear repeat loop":"backspace",
"Mark1 position": "Ctrl+1",
"Mark2 position": "Ctrl+2",
"Mark3 position": "Ctrl+3",
"Mark4 position": "Ctrl+4",
"Mark5 position": "Ctrl+5",
"Mark6 position": "Ctrl+6",
"Mark7 position": "Ctrl+7",
"Mark8 position": "Ctrl+8",
"Mark9 position": "Ctrl+9",
"Mark10 position": "Ctrl+0"
}
}

```

#### File: `app_constance\file_filter.py`

```python
from av_play import formats, format_descriptions

def build_media_file_filter(format_descriptions: dict[str, dict[str, str]]) -> str:
    filter_parts = []
    
    for category, formats in format_descriptions.items():
        for ext, description in formats.items():
            filter_parts.append(f"{description} (*.{ext})")
    
    audio_extensions = list(format_descriptions["audio"].keys())
    audio_pattern = " ".join(f"*.{ext}" for ext in audio_extensions)
    filter_parts.insert(0, f"Audio Files ({audio_pattern})")
    
    video_extensions = list(format_descriptions["video"].keys())
    video_pattern = " ".join(f"*.{ext}" for ext in video_extensions)
    filter_parts.insert(1, f"Video Files ({video_pattern})")
    
    all_extensions = []
    all_extensions.extend(format_descriptions["audio"].keys())
    all_extensions.extend(format_descriptions["video"].keys())
    all_pattern = " ".join(f"*.{ext}" for ext in all_extensions)
    filter_parts.insert(0, f"Supported Media Files ({all_pattern})")
    
    filter_parts.append("All Files (*.*)")
    
    return ";;".join(filter_parts)

file_filter = build_media_file_filter(format_descriptions)
```

#### File: `app_constance\misc.py`

```python
import os

title_lngs ={
  "en-US": "English (United States)",
  "en-GB": "English (United Kingdom)",
  "fr-FR": "French (France)",
  "es-ES": "Spanish (Spain)",
  "de-DE": "German (Germany)",
  "it-IT": "Italian (Italy)",
  "pt-PT": "Portuguese (Portugal)",
  "pt-BR": "Portuguese (Brazil)",
  "ru-RU": "Russian (Russia)",
  "zh-CN": "Chinese (Simplified, China)",
  "zh-TW": "Chinese (Traditional, Taiwan)",
  "ja-JP": "Japanese (Japan)",
  "ko-KR": "Korean (South Korea)",
  "ar-SA": "Arabic (Saudi Arabia)",
  "hi-IN": "Hindi (India)",
  "he-IL": "Hebrew (Israel)",
  "nl-NL": "Dutch (Netherlands)",
  "sv-SE": "Swedish (Sweden)",
  "da-DK": "Danish (Denmark)",
  "fi-FI": "Finnish (Finland)",
  "no-NO": "Norwegian (Norway)",
  "pl-PL": "Polish (Poland)",
  "tr-TR": "Turkish (Turkey)",
  "cs-CZ": "Czech (Czech Republic)",
  "el-GR": "Greek (Greece)",
  "hu-HU": "Hungarian (Hungary)",
  "ro-RO": "Romanian (Romania)",
  "sk-SK": "Slovak (Slovakia)",
  "uk-UA": "Ukrainian (Ukraine)",
  "vi-VN": "Vietnamese (Vietnam)"
}

video_resolutions = {
    "X600-480": {"width": 600, "height": 480},
    "X800-600": {"width": 800, "height": 600},
    "X1024-720": {"width": 1024, "height": 720},
    "X1280-720": {"width": 1280, "height": 720},
    "X1280-800": {"width": 1280, "height": 800},
    "X1600-900": {"width": 1600, "height": 900},
    "X1920-1080": {"width": 1920, "height": 1080},
}

video_speeds = [1.0,1.5,2.0,2.5,3]
screenshot_formats = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"]
app_languages = ["EN", "FR", "AR", "ES"]
```

#### File: `app_constance\prefs_dict.py`

```python
from .misc import screenshot_formats

prefs = {
"autoplay": True,
"repeat": False,
"offset": {"seek": 5,"volume":5},
"last_path": "",
"device": "auto",
"default path": "",
"ffmpeg_binary": "",
"image_format": screenshot_formats[2],
"language":"en",
"subtitle-language":"en-US",
"urlls": []
}
```

<a name="directory-app_db"></a>
### Directory: `app_db`


#### File: `app_db\__init__.py`

```python
import os

from .user_db import UserFiles
from .media_db import MediaFile, MediaType, MediaDatabase
from utilities.functions import get_app_path, get_user_directories

current_path = get_app_path()
db_path = f"{current_path}/data/db.sqlite3"
first_launch = True if not os.path.exists(db_path) else False
user_db = UserFiles(db_path)
user_db.connect_to_database()

if first_launch:
    folders = get_user_directories()
    for folder in folders:
        user_db.add_library_folder(folder)
```

#### File: `app_db\base_database.py`

```python
import os
import sqlite3
import threading
import queue
from contextlib import contextmanager
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

class MediaType(Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    MUSIC = "MUSIC"

class FileCategory(Enum):
    FAVORITE = "FAVORITE"
    RECENT = "RECENT"
    LIBRARY = "LIBRARY"

@dataclass
class MediaFile:
    id: str
    path: str
    filename: str
    size: int
    duration: Optional[float]
    media_type: MediaType
    metadata: Dict[str, Any]
    date_added: str
    date_modified: str

@dataclass
class FileEntry:
    id: str
    path: str
    category: FileCategory
    date_added: str

class BaseDatabaseHandler:
    
    def __init__(self, db_path: str, schema: str, simple_mode: bool = False):
        self._db_path = db_path
        self._schema = schema
        self._connection: Optional[sqlite3.Connection] = None
        self._cursor: Optional[sqlite3.Cursor] = None
        self._simple_mode = simple_mode
        
        if not self._simple_mode:
            self._entry_queue = queue.Queue()
            self._queue_thread = None
            self._stop_queue = threading.Event()

    def __enter__(self):
        if not self._connection:
            self.connect_to_database()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

    def connect_to_database(self):
        is_first_run = not os.path.exists(self._db_path)
        if is_first_run:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        self._connection = sqlite3.connect(self._db_path)
        self._cursor = self._connection.cursor()

        if is_first_run:
            self._cursor.executescript(self._schema)
            self._connection.commit()
        
        if not self._simple_mode:
            self._start_queue_worker()

    def _start_queue_worker(self):
        self._queue_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self._queue_thread.start()

    def _queue_worker(self):
        worker_connection = sqlite3.connect(self._db_path)
        worker_cursor = worker_connection.cursor()
        
        while not self._stop_queue.is_set():
            try:
                operation, data = self._entry_queue.get(timeout=1)
                self._process_queue_operation(operation, data, worker_cursor, worker_connection)
                self._entry_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                pass
        
        worker_cursor.close()
        worker_connection.close()

    def _process_queue_operation(self, operation: str, data: Any, cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        pass

    def close_connection(self):
        if not self._simple_mode:
            self._stop_queue.set()
            if self._queue_thread:
                self._queue_thread.join(timeout=2)
        
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._connection = None
        self._cursor = None

    def get_cursor(self) -> sqlite3.Cursor:
        if not self._cursor:
            raise RuntimeError("Database connection is not established.")
        return self._cursor

    @contextmanager
    def get_connection(self):
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()
        try:
            yield connection, cursor
        finally:
            cursor.close()
            connection.close()
```

#### File: `app_db\media_db.py`

```python
import os
import sqlite3
import hashlib
from typing import Optional, List, Dict, Any
from pathlib import Path

from .base_database import BaseDatabaseHandler, MediaFile, MediaType

class MediaDatabase(BaseDatabaseHandler):
    
    MEDIA_SCHEMA = """
    CREATE TABLE IF NOT EXISTS media_files (
        id TEXT PRIMARY KEY NOT NULL,
        path TEXT NOT NULL UNIQUE,
        filename TEXT NOT NULL,
        size INTEGER NOT NULL,
        duration REAL,
        media_type TEXT CHECK(media_type IN ('VIDEO', 'AUDIO', 'MUSIC')) NOT NULL,
        metadata TEXT,
        date_added TEXT NOT NULL,
        date_modified TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_media_type ON media_files(media_type);
    CREATE INDEX IF NOT EXISTS idx_filename ON media_files(filename);
    CREATE INDEX IF NOT EXISTS idx_path ON media_files(path);
    """

    def __init__(self, db_path: str = os.path.join("data", "media.sqlite3"), simple_mode: bool = False):
        super().__init__(db_path, self.MEDIA_SCHEMA, simple_mode)

    def _generate_file_id(self, file_path: str) -> str:
        return hashlib.md5(file_path.encode()).hexdigest()

    def _process_queue_operation(self, operation: str, data: Any, cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        if operation == "add_media":
            self._add_media_worker(data, cursor, connection)
        elif operation == "add_media_batch":
            self._add_media_batch_worker(data, cursor, connection)

    def _add_media_worker(self, media: MediaFile, cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        cursor.execute(
            "INSERT OR REPLACE INTO media_files (id, path, filename, size, duration, media_type, metadata, date_added, date_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (media.id, media.path, media.filename, media.size, media.duration, media.media_type.value, str(media.metadata), media.date_added, media.date_modified)
        )
        connection.commit()

    def _add_media_batch_worker(self, media_list: List[MediaFile], cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        media_tuples = [
            (m.id, m.path, m.filename, m.size, m.duration, m.media_type.value, str(m.metadata), m.date_added, m.date_modified)
            for m in media_list
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO media_files (id, path, filename, size, duration, media_type, metadata, date_added, date_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            media_tuples
        )
        connection.commit()

    def add_media_file(self, media: MediaFile):
        if self._simple_mode:
            self._add_media_worker(media, self.get_cursor(), self._connection)
        else:
            self._entry_queue.put(("add_media", media))

    def add_media_files(self, media_list: List[MediaFile]):
        if self._simple_mode:
            self._add_media_batch_worker(media_list, self.get_cursor(), self._connection)
        else:
            self._entry_queue.put(("add_media_batch", media_list))

    def scan_folder(self, folder_path: str, extensions: Dict[MediaType, List[str]] = None) -> List[MediaFile]:
        if extensions is None:
            extensions = {
                MediaType.VIDEO: ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'],
                MediaType.AUDIO: ['.wav', '.flac', '.aac', '.ogg'],
                MediaType.MUSIC: ['.mp3', '.m4a', '.opus']
            }
        
        media_files = []
        folder = Path(folder_path)
        
        if not folder.exists():
            return media_files

        for file_path in folder.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                media_type = None
                
                for mtype, exts in extensions.items():
                    if suffix in exts:
                        media_type = mtype
                        break
                
                if media_type:
                    stat = file_path.stat()
                    file_id = self._generate_file_id(str(file_path))
                    
                    media_file = MediaFile(
                        id=file_id,
                        path=str(file_path),
                        filename=file_path.name,
                        size=stat.st_size,
                        duration=None,
                        media_type=media_type,
                        metadata={},
                        date_added=str(stat.st_ctime),
                        date_modified=str(stat.st_mtime)
                    )
                    media_files.append(media_file)
        
        return media_files

    def search_by_filename(self, query: str, media_type: Optional[MediaType] = None, limit: Optional[int] = None) -> List[MediaFile]:
        cursor = self.get_cursor()
        
        if media_type:
            if limit:
                cursor.execute("SELECT * FROM media_files WHERE filename LIKE ? AND media_type = ? ORDER BY filename LIMIT ?", 
                              (f'%{query}%', media_type.value, limit))
            else:
                cursor.execute("SELECT * FROM media_files WHERE filename LIKE ? AND media_type = ? ORDER BY filename", 
                              (f'%{query}%', media_type.value))
        else:
            if limit:
                cursor.execute("SELECT * FROM media_files WHERE filename LIKE ? ORDER BY filename LIMIT ?", 
                              (f'%{query}%', limit))
            else:
                cursor.execute("SELECT * FROM media_files WHERE filename LIKE ? ORDER BY filename", (f'%{query}%',))
        
        return self._rows_to_media_files(cursor.fetchall())

    def filter_by_type(self, media_type: MediaType, limit: Optional[int] = None) -> List[MediaFile]:
        cursor = self.get_cursor()
        
        if limit:
            cursor.execute("SELECT * FROM media_files WHERE media_type = ? ORDER BY filename LIMIT ?", 
                          (media_type.value, limit))
        else:
            cursor.execute("SELECT * FROM media_files WHERE media_type = ? ORDER BY filename", (media_type.value,))
        
        return self._rows_to_media_files(cursor.fetchall())

    def get_by_id(self, file_id: str) -> Optional[MediaFile]:
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM media_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        return self._row_to_media_file(row) if row else None

    def delete_media_file(self, file_id: str):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM media_files WHERE id = ?", (file_id,))
        self._connection.commit()

    def get_all_media(self) -> List[MediaFile]:
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM media_files ORDER BY filename")
        return self._rows_to_media_files(cursor.fetchall())

    def _row_to_media_file(self, row) -> MediaFile:
        return MediaFile(
            id=row[0], path=row[1], filename=row[2], size=row[3], duration=row[4],
            media_type=MediaType(row[5]), metadata=eval(row[6]) if row[6] else {},
            date_added=row[7], date_modified=row[8]
        )

    def _rows_to_media_files(self, rows) -> List[MediaFile]:
        return [self._row_to_media_file(row) for row in rows]
```

#### File: `app_db\user_db.py`

```python
import os
import sqlite3
import hashlib
from typing import Optional, List, Any
from datetime import datetime

from .base_database import BaseDatabaseHandler, FileEntry, FileCategory

class UserFiles(BaseDatabaseHandler):
    
    USER_FILES_SCHEMA = """
    CREATE TABLE IF NOT EXISTS user_files (
        id TEXT PRIMARY KEY NOT NULL,
        path TEXT NOT NULL,
        category TEXT CHECK(category IN ('FAVORITE', 'RECENT', 'LIBRARY')) NOT NULL,
        date_added TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_category ON user_files(category);
    CREATE INDEX IF NOT EXISTS idx_date_added ON user_files(date_added);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_path_category ON user_files(path, category);
    """

    def __init__(self, db_path: str = os.path.join("data", "user.sqlite3"), simple_mode: bool = False):
        super().__init__(db_path, self.USER_FILES_SCHEMA, simple_mode)

    def _generate_entry_id(self, path: str, category: FileCategory) -> str:
        return hashlib.md5(f"{path}_{category.value}".encode()).hexdigest()

    def _process_queue_operation(self, operation: str, data: Any, cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        if operation == "add_entry":
            self._add_entry_worker(data, cursor, connection)

    def _add_entry_worker(self, entry: FileEntry, cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        cursor.execute(
            "INSERT OR REPLACE INTO user_files (id, path, category, date_added) VALUES (?, ?, ?, ?)",
            (entry.id, entry.path, entry.category.value, entry.date_added)
        )
        connection.commit()

    def add_favorite(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.FAVORITE)
        entry = FileEntry(entry_id, path, FileCategory.FAVORITE, str(datetime.now().timestamp()))
        
        if self._simple_mode:
            self._add_entry_worker(entry, self.get_cursor(), self._connection) # type: ignore
        else:
            self._entry_queue.put(("add_entry", entry))

    def add_recent(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.RECENT)
        entry = FileEntry(entry_id, path, FileCategory.RECENT, str(datetime.now().timestamp()))
        
        if self._simple_mode:
            self._add_entry_worker(entry, self.get_cursor(), self._connection) # type: ignore
        else:
            self._entry_queue.put(("add_entry", entry))

    def add_library_folder(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.LIBRARY)
        entry = FileEntry(entry_id, path, FileCategory.LIBRARY, str(datetime.now().timestamp()))
        
        if self._simple_mode:
            self._add_entry_worker(entry, self.get_cursor(), self._connection) # type: ignore
        else:
            self._entry_queue.put(("add_entry", entry))

    def remove_favorite(self, path: str):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE path = ? AND category = ?", (path, FileCategory.FAVORITE.value))
        self._connection.commit() # type: ignore

    def remove_recent(self, path: str):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE path = ? AND category = ?", (path, FileCategory.RECENT.value))
        self._connection.commit() # type: ignore

    def remove_library_folder(self, path: str):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE path = ? AND category = ?", (path, FileCategory.LIBRARY.value))
        self._connection.commit() # type: ignore

    def clear_favorites(self):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE category = ?", (FileCategory.FAVORITE.value,))
        self._connection.commit() # type: ignore

    def clear_recents(self):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE category = ?", (FileCategory.RECENT.value,))
        self._connection.commit() # type: ignore

    def clear_library_folders(self):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE category = ?", (FileCategory.LIBRARY.value,))
        self._connection.commit() # type: ignore

    def get_favorites(self, limit: Optional[int] = None) -> List[str]:
        cursor = self.get_cursor()
        if limit:
            cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?", 
                          (FileCategory.FAVORITE.value, limit))
        else:
            cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC", 
                          (FileCategory.FAVORITE.value,))
        return [row[0] for row in cursor.fetchall()]

    def get_recents(self, limit: Optional[int] = None) -> List[str]:
        cursor = self.get_cursor()
        if limit:
            cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?", 
                          (FileCategory.RECENT.value, limit))
        else:
            cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC", 
                          (FileCategory.RECENT.value,))
        return [row[0] for row in cursor.fetchall()]

    def get_library_folders(self) -> List[str]:
        cursor = self.get_cursor()
        cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added ASC", 
                      (FileCategory.LIBRARY.value,))
        return [row[0] for row in cursor.fetchall()]

    def is_favorite(self, path: str) -> bool:
        cursor = self.get_cursor()
        cursor.execute("SELECT 1 FROM user_files WHERE path = ? AND category = ?", 
                      (path, FileCategory.FAVORITE.value))
        return cursor.fetchone() is not None

    def is_in_library(self, path: str) -> bool:
        cursor = self.get_cursor()
        cursor.execute("SELECT 1 FROM user_files WHERE path = ? AND category = ?", 
                      (path, FileCategory.LIBRARY.value))
        return cursor.fetchone() is not None

    def cleanup_recents(self, max_count: int = 100):
        cursor = self.get_cursor()
        cursor.execute(
            "DELETE FROM user_files WHERE category = ? AND id NOT IN (SELECT id FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?)",
            (FileCategory.RECENT.value, FileCategory.RECENT.value, max_count)
        )
        self._connection.commit() # type: ignore
```

<a name="directory-data"></a>
### Directory: `data`


#### File: `data\bookmarks.json`

```json
{
  "E:\\videoes\\ApSlayz Rage Compilation Part 1 [Q3z2LA9vGyU].webm": [
    6,
    16,
    59,
    59,
    60,
    61,
    62,
    63,
    63,
    63,
    64,
    65,
    66,
    66,
    66,
    66,
    66,
    66,
    66
  ]
}
```

#### File: `data\last_positions.json`

```json
{
  "E:\\videoes\\ApSlayz Rage Compilation Part 1 [Q3z2LA9vGyU].webm": 775,
  "E:\\videoes\\ApSlayz Rage Compilation Part 4 [uVNhUyPA5Gs].webm": 1
}
```

#### File: `data\prefs.json`

```json
7b226175746f706c6179223a20747275652c2022726570656174223a2066616c73652c20226f6666736574223a207b227365656b223a20352c2022766f6c756d65223a20357d2c20226c6173745f70617468223a2022453a5c5c766964656f6573222c2022646576696365223a20226175746f222c202264656661756c742070617468223a2022222c202266666d7065675f62696e617279223a2022433a5c5c55736572735c5c65617273765c5c4f6e6544726976655c5c446f63756d656e74735c5c506c6179466f726d2f62696e2f2f66666d7065672e657865222c2022696d6167655f666f726d6174223a20222e706e67222c20226c616e6775616765223a2022656e222c20227375627469746c652d6c616e6775616765223a2022656e2d5553222c202275726c6c73223a205b5d2c202277696e646f775f67656f6d65747279223a2022303164396430636230303033303030303030303030303030666666666666663830303030303535353030303030326366303030303030303130303030303031393030303030353534303030303033333830303030303030303032303030303030303535363030303030303030303030303030313730303030303535353030303030326366222c202277696e646f775f7374617465223a202230303030303066663030303030303030666430303030303030323030303030303030303030303031343530303030303236666663303230303030303030316662666666666666666630313030303030303334303030303032366630303030303161313030666666666666303030303030303130303030303361313030303030323666666330323030303030303032666266666666666666663031303030303030333430303030303164303030303030323662303066666666666666626666666666666666303130303030303230613030303030303939303030303030393930306666666666663030303030303634303030303032366630303030303030343030303030303034303030303030303830303030303030386663303030303030303130303030303030323030303030303031666666666666666630313030303030303030666666666666666630303030303030303030303030303030227d
```

#### File: `data\repeat_loops.json`

```json
{
  "E:\\videoes\\ApSlayz Rage Compilation Part 1 [Q3z2LA9vGyU].webm": [
    null,
    null
  ]
}
```

<a name="directory-explorer"></a>
### Directory: `EXPLORER`


#### File: `EXPLORER\__init__.py`

```python

```

#### File: `EXPLORER\explorer.py`

```python
import os, string
import time, datetime as dt

from enum import Enum
from dataclasses import dataclass
from recursive_size import get_size
from hurry.filesize import size as sz


class PathType(Enum):
    FILE = "file"
    FOLDER = "folder"
    UNKNOWN = "UNKNOWN"

class PathInfo:

    @staticmethod
    def get_path_type(path: str) -> PathType:
        return PathType.FOLDER if os.path.isdir(path) else (PathType.FILE if os.path.isfile(path) else PathType.UNKNOWN)

    @staticmethod
    def get_modified_date(path):
        modify_date = os.path.getmtime(path)
        return dt.date.fromtimestamp(os.path.getmtime(path))

    def __init__(self, path):
        self.path: str = path
        self.name: str = os.path.basename(self.path)
        self.ext: str = os.path.splitext(self.path)[1]
        self.type: PathType = self.get_path_type(self.path)
        self.modify_date:dt.date = self.get_modified_date(self.path)
        self.size: str = f"{sz(get_size(self.path))}b" if type == PathType.FILE else "0"

@dataclass
class PathItem:
    path: str
    type: PathType
    info: PathInfo

class Explorer:
    __drives = []
    default_path = os.path.expanduser("~")

    @staticmethod
    def get_current(): return os.getcwd()

    @staticmethod
    def get_root(path): return os.path.dirname(path)

    @staticmethod
    def list_drives():
        return [f"{letter}:" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:")]

    def __init__(self, file_extensions=[]):
        self._file_extensions = file_extensions
        self._current_path = self.get_current()
        self._root_path = self.get_root(self._current_path)
        self.items = {}
        self.folders = []
        self.files = []
        self.__retrieve_listing()

    @property
    def current_path(self) -> str:
        return self._current_path

    @current_path.setter
    def current_path(self, value: str):
        self.set_current_path(value)

    @property
    def root_path(self):
        return self._root_path

    def get_prev_path(self): return self.root_path

    def set_default_path(self, path): self.default_path = path

    def get_current_path(self): return self._current_path

    def set_current_path(self, path):
        if os.path.exists(path):
            self._current_path = path
        else:
            self._current_path = self.default_path
        self._root_path = self.get_root(self._current_path)
        self._prev_path = self._current_path
        self.__retrieve_listing()

    def forward(self, path):
        if self._current_path == "drives" and path in self.items:
            self._current_path = self.items[path].path
        elif ((path in self.items and os.path.exists(path)) or
            (path in self.items and os.path.exists(f"{self._current_path}/{path}")) or
            os.path.exists(path)):
            if path in self.items:
                self._current_path = self.items[path].path
            else:
                self._current_path = path
        else:
            self._current_path = self.default_path
        self._root_path = self.get_root(self._current_path)
        self._prev_path = self._current_path
        self.__retrieve_listing()

    def backward(self):
        if len(self._current_path) <= 3 and self._current_path.endswith(":\\"):
            self._prev_path = self._current_path
            self._current_path = "drives"
            self._root_path = "drives"
        elif os.path.exists(self.current_path) and os.path.exists(self._root_path):
            self._prev_path = self._current_path
            self._current_path = self._root_path
        else:
            self._current_path = self.default_path
            self._prev_path = self._current_path
        self._root_path = self.get_root(self._current_path)
        self.__retrieve_listing()

    def __retrieve_listing(self):
        self.folders.clear()
        self.files.clear()
        self.items.clear()
        
        if self._current_path == "drives":
            drives = self.list_drives()
            for drive in drives:
                self.items[drive] = PathItem(path=drive + "\\", type=PathType.FOLDER, info=PathInfo(drive + "\\"))
                self.folders.append(drive)
        else:
            contents = os.listdir(self._current_path)
            for item in contents:
                item_path = os.path.join(self._current_path, item)
                if os.path.isdir(item_path):
                    self.items[item] = PathItem(path=item_path, type=PathType.FOLDER, info=PathInfo(item_path))
                    self.folders.append(item)
                elif os.path.isfile(item_path) and os.path.splitext(item_path)[1] in self._file_extensions:
                    self.items[item] = PathItem(path=item_path, type=PathType.FILE, info=PathInfo(item_path))
                    self.files.append(item)
```

#### File: `EXPLORER\explorer_view.py`

```python
from genericpath import isfile
import os

from typing import Optional, Callable
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QMenu, QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Qt as qt, QTimer
from av_play import AVMediaInstance, mpv_video_player, AVPlaybackState
import av_play

from app_config import prefs
from gui_controls.key_event_filter import ShortcutManager
from app_config import key_config
from utilities.functions import copyText
from utilities.util_gui import menuItem, contextMenu
from .explorer import Explorer, PathInfo, PathType


class ExplorerView(QListWidget):

    @staticmethod
    def set_last_path(path):
        prefs.prefs["last_path"] = path
        prefs.save()


    def __init__(self, explorer:Explorer, player:mpv_video_player.MPVVideoPlayer, **kw):
        self._callbacks = kw
        self._just_launched = True
        self._current_media:Optional[str] = None
        self._focused_item_path:Optional[str] = None
        self._player = player
        self._instance:Optional[AVMediaInstance] = None
        self._explorer = explorer
        
        self._media_load_timer = QTimer()
        self._media_load_timer.setSingleShot(True)
        self._media_load_timer.timeout.connect(self._delayed_media_load)
        self._pending_media_path:Optional[str] = None

        super().__init__(kw.get("parent", None))
        self.currentItemChanged.connect(self.onItemChange)
        self.itemClicked.connect(self.onItemActivate)
        self.itemActivated.connect(self.onItemActivate)
        contextMenu(self, self.context_menu)

        self._shortcut_manager:ShortcutManager = ShortcutManager(self)
        self.set_shortcuts()

        last_path = prefs.prefs["last_path"]
        if last_path != "" and os.path.exists(last_path):
            self.change_path(last_path)
        else:
            self.change_path(self._explorer.default_path)


    def set_shortcuts(self):
        hotkeys = key_config.key_config["Explorer"]
        shortcuts:dict[str, Callable] = {
        hotkeys["Play/Pause"]: self.media_play_pause,
        hotkeys["Stop"]: self.media_stop,
        hotkeys["Forward"]: self.media_forward,
        hotkeys["Backward"]: self.media_backward,
        }

        self._shortcut_manager.clear_shortcuts()
        for shortcut in shortcuts:
            self._shortcut_manager.add_widget_shortcut(self, shortcut, shortcuts[shortcut])
        self.install_shortcuts()

    def reset_shortcuts(self):
        self.set_shortcuts()
    
    def install_shortcuts(self):
        self._shortcut_manager.install_on_application()
    
    def uninstall_shortcuts(self):
        self._shortcut_manager.uninstall_from_application()

    def open_file(self):
        self._execute_callback("open_callback", self._focused_item_path) # type: ignore

    def open_new_tab(self):
        self._execute_callback("open_new_callback", self._focused_item_path) # type: ignore

    def add_to_favorites(self):
        self._execute_callback("favorites_callback", self._focused_item_path) # type: ignore

    def update_path(self):
        self._execute_callback("path_change_callback", with_param=False)

    def add_to_playlist(self):
        self._execute_callback("playlist_callback", self._focused_item_path) # type: ignore

    def create_playlist_from_folder(self):
        self._execute_callback("create_playlist_callback", self._focused_item_path) # type: ignore

    def add_to_library(self):
        self._execute_callback("library_callback", self._focused_item_path) # type: ignore

    def copy_path(self):
        copyText(self._focused_item_path)

    def _delayed_media_load(self):
        if self._pending_media_path and self._pending_media_path != self._current_media:
            self._current_media = self._pending_media_path
            
            if self._instance is None:
                self._instance = self._player.create_file_instance(self._pending_media_path)
            else:
                self._instance.load_file(self._pending_media_path)
            self._instance.stop()
            if not self._just_launched and prefs.prefs["autoplay"]:
                self._instance.play()
        self._pending_media_path = None

    def change_path(self, path:str):
        self._explorer.set_current_path(path)
        self.relist_contents()
        self.update_path()
        self.set_last_path(self._explorer.current_path)

    def forward(self):
        if self._focused_item_path is not None:
            self._explorer.forward(self._focused_item_path)
            self.relist_contents()
            self.update_path()
            self.set_last_path(self._explorer.current_path)

    def backward(self):
        item_name = os.path.basename(self._explorer.current_path)
        self._explorer.backward()
        self.relist_contents()
        self.update_path()
        if item_name in self._explorer.items:
            self.setCurrentItem(self.findItems(item_name, qt.MatchFlag.MatchExactly)[0])
        self.set_last_path(self._explorer.current_path)        

    def onItemActivate(self):
        if self._focused_item_path is not None:
            if os.path.isfile(self._focused_item_path):
                self.open_file()
            elif os.path.isdir(self._focused_item_path):
                self.forward()

    def relist_contents(self):
        self.clear()
        self.list_contents()

    def list_contents(self):
        self.addItems(self._explorer.folders+ self._explorer.files)


    def media_play_pause(self):
        if self._instance is not None:
            state:AVPlaybackState = self._instance.get_playback_state()
            if state == AVPlaybackState.AV_STATE_PLAYING:
                self._instance.pause()
            else:
                self._instance.play()


    def media_backward(self):
        if self._instance is not None:
            self._instance.set_position(self._instance.get_position() - prefs.prefs["offset"]["seek"])

    def media_forward(self):
        if self._instance is not None:
            self._instance.set_position(self._instance.get_position() + prefs.prefs["offset"]["seek"])

    def media_stop(self):
        if self._instance is not None:
            self._instance.stop()


    def set_item_info(self):
        if self.currentItem() is None: return
        current_item = self.currentItem().text()
        item_info:Optional[PathInfo] = self._explorer.items.get(current_item, None)
        info = f"Type extension: {item_info.info.ext}\rDate modified: {item_info.info.modify_date}{"\rsize: " + item_info.info.size if item_info.type == PathType.FILE else ""}" # type: ignore
#        position = self.viewport().mapToGlobal(self.visualItemRect(self.currentItem()).bottomLeft())
#        if hasattr(self,"tooltip")==True: del self.tooltip
#        self.tooltip = tooltip(self.info,position,3,self,self.parent)
        infoText  = QLabel(info,self)
        infoText.adjustSize()
        self.setItemWidget(self.currentItem(),infoText)
        infoText.setMinimumHeight(50)
        infoText.setMinimumWidth(200)
        self.currentItem().setSizeHint(infoText.sizeHint())
        self.currentItem().setData(qt.ItemDataRole.AccessibleDescriptionRole,f", {info}")

    def _execute_callback(self, callback_name:str, param:str = "", with_param :bool = True):
        callback:Optional[Callable[[str], None]] = self._callbacks.get(callback_name, None)
        if callback is not None:
            if with_param:
                callback(param)
            else:
                callback()

    def context_menu(self, event):
        if self.currentItem() is None: return
        item = self.currentItem().text()
        item_info:Optional[PathInfo] = self._explorer.items.get(item, None)
        menu = QMenu()

        if item_info.type == PathType.FOLDER: # type: ignore
            menuItem(menu, 'navigate to folder', self.forward, self)
        elif item_info.type == PathType.FILE: # type: ignore
                menuItem(menu, 'Open', self.open_file, self)
                #menuItem(menu, 'Open ina  new tab', self.open_new_tab, self)

                menuItem(menu,"copy path",self.copy_path,self)

        if item_info.type == PathType.FOLDER: # type: ignore
            menuItem(menu, 'Add to library', self.add_to_library, self)
            menuItem(menu, 'Create playlist from folder', self.create_playlist_from_folder, self)
        elif item_info.type == PathType.FILE: # type: ignore
                menuItem(menu, 'Add to playlist', self.add_to_playlist, self)
                menuItem(menu, 'Add to favorites', self.add_to_favorites, self)
        #menuItem(menu, 'add current path to library', self.addLibrary, self)

        menu.exec()


    def onItemChange(self, c, p):
        if p is not None:
            p.setData(qt.ItemDataRole.AccessibleDescriptionRole, "")
            self.removeItemWidget(p)

        if c is None: return

        item_name = c.text()
        item_info:Optional[PathInfo] = self._explorer.items.get(item_name, None)
        
        if item_info is None: return
        
        if self._explorer.current_path == "drives":
            self._focused_item_path = self._explorer.items[item_name].path
        else:
            self._focused_item_path = os.path.join(self._explorer.current_path, item_name)
        
        self.set_item_info()

        if item_info.type == PathType.FILE and self._focused_item_path is not None:
            self._media_load_timer.stop()
            self._pending_media_path = self._focused_item_path
            self._media_load_timer.start(300)

        if self._just_launched: self._just_launched = False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == qt.Key.Key_Backspace:
            self.backward()
        else:
            super().keyPressEvent(event)
```

#### File: `EXPLORER\explorer_widget.py`

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QPushButton, 
    QTextEdit, QListWidget, QCheckBox, QSpinBox, QLabel, 
    QSplitter, QGroupBox
)
from PySide6.QtCore import Qt as qt

from typing import Optional
from av_play import mpv_video_player, formats, AVMediaInstance, AVPlaybackState
from app_config import prefs
from app_db import UserFiles
from .explorer import Explorer
from .explorer_view import ExplorerView
from .library_view import LibraryView


extensions = list(map(lambda ext: f".{ext}", formats["audio"] + formats["video"]))


class ExplorerWidget(QWidget):

    
    def __init__(self, user_db:UserFiles, **kw):
        self._user_db = user_db
        self._player:mpv_video_player.MPVVideoPlayer = mpv_video_player.MPVVideoPlayer()
        self._instance:Optional[AVMediaInstance] = None
        self._explorer = Explorer(extensions)

        super().__init__(kw.get("parent", None))
        self.setWindowTitle("Explorer")
        
        self._callbacks = {**kw,
        "path_change_callback": self.update_path,
        "library_callback": lambda path: self.add_to_library(path)
        }
        
        self._setup_ui()
        self._player.init(window=self.video_widget.winId())


    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        title_label = QLabel("Explorer")
        main_layout.addWidget(title_label)
        main_splitter = QSplitter(qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        left_panel = QGroupBox("Library")
        left_layout = QVBoxLayout(left_panel)
        
        main_splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        path_group = QGroupBox("Path")
        path_layout = QVBoxLayout(path_group)
        self.parent_btn = QPushButton("Parent Directory")
        self.parent_btn.clicked.connect(self.backward)
        path_layout.addWidget(self.parent_btn)

        self.path_edit = QTextEdit()
        self.path_edit.setTabChangesFocus(True)
        path_layout.addWidget(self.path_edit)
        right_layout.addWidget(path_group)
        
        content_splitter = QSplitter(qt.Orientation.Vertical)
        right_layout.addWidget(content_splitter)
        explorer_group = QGroupBox("Files")
        explorer_layout = QVBoxLayout(explorer_group)

        self.explorer_view = ExplorerView(self._explorer, self._player, **{"parent": self, **self._callbacks})
        explorer_layout.addWidget(self.explorer_view)

        self.library_view = LibraryView(self._user_db, self,
        navigate_callback=lambda path: self.explorer_view.change_path(path)
        )
        left_layout.addWidget(self.library_view)

        content_splitter.addWidget(explorer_group)
        
        preview_group = QGroupBox("Media Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.video_widget = QWidget()
        self.video_widget.setAttribute(qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.video_widget.setAttribute(qt.WidgetAttribute.WA_NativeWindow)
        preview_layout.addWidget(self.video_widget)
        
        content_splitter.addWidget(preview_group)
        main_splitter.addWidget(right_panel)
        
        controls_layout = QHBoxLayout()
        self.autoplay_cb = QCheckBox("Auto Play")
        self.autoplay_cb.stateChanged.connect(self.autoplayState)
        self.autoplay_cb.setChecked(prefs.prefs["autoplay"])
        controls_layout.addWidget(self.autoplay_cb)
        controls_layout.addStretch()
        
        volume_label = QLabel("Volume:")
        controls_layout.addWidget(volume_label)
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setValue(100)
        self.volume_spinbox.setRange(0, 100)
        self.volume_spinbox.setSuffix("%")
        self.volume_spinbox.setAccessibleName("volume")
        self.volume_spinbox.valueChanged.connect(self.volumeChange)
        controls_layout.addWidget(self.volume_spinbox)
        
        main_layout.addLayout(controls_layout)

    def repeat_media(self):
        if prefs.prefs['repeat'] == True:
            if self._instance is not None:
                try:
                    if self._instance.get_playback_state == AVPlaybackState.AV_STATE_STOPPED:
                        self._instance.play()
                except:
                    pass


    def volumeChange(self, value):
        if self._instance is not None:
            try:
                self._instance.set_volume(value)
            except:
                pass
        else:
             self._instance = self._player.primary_instance
             if self._instance is not None: 
                 try:
                     self._instance.set_volume(value)
                 except:
                     pass

    def autoplayState(self, state):
        if state == 2:
            prefs.prefs['autoplay'] = True
        elif state == 0:
                prefs.prefs['autoplay'] = False
        prefs.save()

    def update_path(self):
        self.path_edit.setText(self._explorer.current_path)

    def backward(self):
        self.explorer_view.backward()

    def add_to_library(self, path):
        self.library_view.add_path(path)
```

#### File: `EXPLORER\library_dialogs.py`

```python
import os

from typing import Optional, Callable
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, 
QFileDialog, QTextEdit, QPlainTextEdit, QLabel, QPushButton, )
from PySide6.QtCore import Qt as qt


class libraryDialog(QDialog):


    def __init__(self, title, parent = None, path = None, on_confirm_callback:Optional[Callable[[str], None]] = None):
        self.path:Optional[str] = path
        self.title = title
        self.on_confirm_callback = on_confirm_callback

        super().__init__(parent)
        self.setWindowModality(qt.WindowModality.WindowModal)
        self.setWindowTitle(self.title)

        self.ui()
        self.layout()
        self.setLayout(self.Layout)

    def ui(self):
        self.pathLabel = QLabel('path', self)
        self.path_field = QPlainTextEdit(self)
        self.path_field.setReadOnly(False)
        self.path_field.setTabChangesFocus(True)
        self.brows_button = QPushButton('brows', self)
        self.confirm_button = QPushButton('confirm', self)
        self.cancel_button = QPushButton('cancel', self)
        self.brows_button.clicked.connect(self.onBrows)
        self.confirm_button.clicked.connect(self.onConfirm)
        self.cancel_button.clicked.connect(self.close)

    def layout(self):
        self.Layout = QVBoxLayout()
        topLayout = QHBoxLayout()
        pathLayout = QVBoxLayout()
        pathLayout.addWidget(self.pathLabel)
        pathLayout.addWidget(self.path_field)
        topLayout.addLayout(pathLayout)
        topLayout.addWidget(self.brows_button)
        self.Layout.addLayout(topLayout)
        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(self.confirm_button)
        bottomLayout.addWidget(self.cancel_button)
        self.Layout.addLayout(bottomLayout)

    def onBrows(self):
        path_dialog = QFileDialog.getExistingDirectory(self)
        if path_dialog:
            self.path = path_dialog
        self.path_field.setPlainText(self.path) # type: ignore

    def onConfirm(self):
        if self.on_confirm_callback:
            self.on_confirm_callback(self.path) # type: ignore
        self.close()


class NewDialog(libraryDialog):


    def __init__(self, on_confirm_callback, parent=None,path=None):
        super().__init__("Add new path to library", parent, path, on_confirm_callback)


class EditDialog(libraryDialog):

    def __init__(self, on_confirm_callback, parent=None,path=None):
        super().__init__("Add existing path", parent, path, on_confirm_callback)
        self.path_field.setPlainText(self.path) # type: ignore
```

#### File: `EXPLORER\library_view.py`

```python
import os

from typing import Optional, Callable, List
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu
from PySide6.QtCore import Qt as qt

from utilities.util_gui import  contextMenu, messageBox, menuItem
from app_db import UserFiles
from .library_dialogs import NewDialog, EditDialog


class LibraryView(QTreeWidget):


    def __init__(self, user_db:UserFiles, parent, **kw):
        self._user_db:UserFiles = user_db
        super().__init__(parent)
        self.navigate_callback:Optional[Callable[[str], None]] = kw.get("navigate_callback", None)
        self.itemClicked.connect(self.navigateTo)
        self.itemActivated.connect(self.navigateTo)

        contextMenu(self, self.context_menu)
        self.setColumnCount(1)
        self.setHeaderLabels(['folder'])

        self._folder_paths:List[str] = []
        self.lib = QTreeWidgetItem(self)
        self.lib.setText(0, 'library')
        self.insertTopLevelItem(0, self.lib)
        self.listContents()


    def add_path(self, path:str):
        if path in self._folder_paths:
            messageBox('path in library', 'this path already existsin the library')
            return 0

        self._user_db.add_library_folder(path)
        self.listContents()

    def new(self):
        d = NewDialog(self.add_callback, self.parent())
        d.exec()

    def modify(self):
        path = self.currentItem().text(0)
        if path in self._folder_paths:
            d = EditDialog(self.edit_callback, self.parent, path)
            d.exec()

    def delete(self):
        current_item = self.currentItem()
        if current_item and current_item.text(0) != "library":
            item_name = current_item.text(0)
            # Find the full path from _folder_paths based on basename
            item_path = None
            for path in self._folder_paths:
                if os.path.basename(path) == item_name:
                    item_path = path
                    break
            
            if item_path:
                self.lib.takeChild(self.lib.indexOfChild(current_item))
                self._user_db.remove_library_folder(item_path)

    def navigateTo(self):
        current_item = self.currentItem()
        if current_item is None or current_item.text(0) == "library":
            return
            
        item_name = current_item.text(0)
        item_path = None
        for path in self._folder_paths:
            if os.path.basename(path) == item_name:
                item_path = path
                break
                
        if self.navigate_callback is not None and item_path is not None:
            self.navigate_callback(item_path)

    def add_callback(self, path:str):
        if os.path.exists(path) == False:
            messageBox('error', 'path not found')
            return 0

        name = os.path.basename(path)
        if path in self._folder_paths:
            messageBox('error', 'path already exists')
            return 0

        self._user_db.add_library_folder(path)
        self.listContents()
        self.setCurrentItem(self.findItems(os.path.basename(path), qt.MatchFlag.MatchExactly, 0)[0])

    def edit_callback(self, path:str):
        if os.path.exists(path) == False:
            messageBox('error', 'path not found')
            return 0


        self.listContents()
        name = os.path.basename(path)
        self.setCurrentItem(self.findItems(os.path.basename(path), qt.MatchFlag.MatchExactly, 0)[0])


    def listContents(self):
        self._folder_paths.clear()
        self.Clear()
        self._folder_paths = self._user_db.get_library_folders()

        for item in self._folder_paths:
            folder = QTreeWidgetItem(self.lib)
            folder.setText(0, os.path.basename(item))
            self.lib.addChild(folder)

    def Clear(self):
        while self.lib.childCount() > 0:
            item = self.lib.child(0)
            self.lib.removeChild(item)

    def clear_library(self):
        self.clear()
        self._folder_paths.clear()
        self._user_db.clear_library_folders()

    def context_menu(self, event):
        item = self.currentItem().text(0)
        menu = QMenu()
        menuItem(menu, 'Add new', self.new, self)
        if self.currentItem().text(0) != "library":
            #menuItem(menu, 'modify path', self.modify, self)
            menuItem(menu, 'Remove', self.delete, self)
            menuItem(menu, 'Clear library', self.clear_library, self)
        menu.exec()
```

<a name="directory-files-rc"></a>
### Directory: `files-rc`


#### File: `files-rc\__AV_Common.py`

```python
from enum import Enum, auto
from typing import Union, Any
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from validators import url, ValidationError


ParameterValue = Union[int, float, bool, str]
formats:dict[str, list[str]] = {
       "audio": ["mp1", "mp2", "mp3", "ogg", "wav", "m4a", "aac", "flac", "wma", "aif", "wv"],
       "video": ["flv", "rm", "3gp", "mp4", "mkv", "mov", "wmv", "mpeg", "avi", "webm"]
}

format_descriptions: dict[str, dict[str, str]] = {
    "audio": {
        "mp1": "MPEG Audio Layer 1",
        "mp2": "MPEG Audio Layer 2",
        "mp3": "MPEG Audio Layer 3",
        "ogg": "Ogg Vorbis Audio Container",
        "wav": "Waveform Audio File Format",
        "m4a": "MPEG-4 Audio (often AAC)",
        "aac": "Advanced Audio Coding",
        "flac": "Free Lossless Audio Codec",
        "wma": "Windows Media Audio",
        "aif": "Audio Interchange File Format",
        "wv":  "WavPack Lossless Audio",
    },
    "video": {
        "flv": "Flash Video",
        "rm":  "RealMedia",
        "3gp": "3rd Generation Partnership Project ",
        "mp4": "MPEG-4 Part 14 Video Container",
        "mkv": "Matroska Multimedia Container",
        "mov": "Apple QuickTime Movie",
        "wmv": "Windows Media Video",
        "mpeg": "Moving Picture Experts Group Video (MPEG-1/MPEG-2)",
        "avi": "Audio Video Interleave",
        "webm": "WebM Video Format (VP8/VP9/AV1 Video, Vorbis/Opus Audio)"
    }
}

class AVErrorInfo(Enum):
      UNKNOWN_ERROR = -1
      INITIALIZATION_ERROR = 0
      FILE_NOTFOUND = 1
      UNSUPPORTED_FORMAT = 2
      INVALID_HANDLE = 3
      HTTP_ERROR = 4
      INVALID_MEDIA_FILTER = 5
      INVALID_FILTER_PARAMETER = 6
      INVALID_FILTER_PARAMETER_TYPE = 7
      INVALID_FILTER_PARAMETER_VALUE = 8
      INVALID_FILTER_PARAMETER_RANGE = 9
      UNINITIALIZED = 10
      NET_ERROR = 11

class AVPlaybackState(Enum):
    AV_STATE_NOTHING = -1
    AV_STATE_STOPPED = 0
    AV_STATE_PLAYING = 1
    AV_STATE_PAUSED = 2
    AV_STATE_BUFFERING = 3
    AV_STATE_LOADING = 4

class AVPlaylistMode(Enum):
    SEQUENTIAL = auto()
    REPEAT_ALL = auto()
    REPEAT_ONE = auto()
    SHUFFLE = auto()

class AVPlaylistState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    FINISHED = auto()

class AVMuteState(Enum):
                  AV_AUDIO_MUTED = -1
                  AV_AUDIO_UNMUTED = 1

class AVMediaType(Enum):
        AV_TYPE_AUDIO = "audio"
        AV_TYPE_VIDEO = "video"

class AVMediaBackend(Enum):
        AV_BACKEND_FMOD = "fmod"
        AV_BACKEND_MPV = "mpv"
        AV_BACKEND_VLC = "vlc"

class AVMediaSource(Enum):
      AV_SRC_FILE = 1
      AV_SRC_URL = 2
      AV_SRC_NOT_SET = 3

@dataclass
class AVDevice:
        media_backend:AVMediaBackend
        name: str


class AVError(Exception):
      

      def __init__(self, info:AVErrorInfo, message:str|None = None) -> None:
            self.info = info
            self.message = message
            super().__init__(message if message is not None else f"Info: {info}")

AVFilterType = AVMediaType

class AVFilter:
    
    def __init__(self, filter_type: AVFilterType, media_backend: AVMediaBackend,
                 filter_handle: str, parameters: dict[str, ParameterValue], backend_additional_info: dict[Any, Any]):
        self.__type = filter_type
        self.__backend:AVMediaBackend = media_backend
        self.__handle:str = filter_handle
        self.__parameters:dict[str, ParameterValue] = parameters
        self.__info:dict[Any, Any] = backend_additional_info


    @property
    def type(self):
           return self.__type

    @property
    def backend(self):
           return self.__backend

    @property
    def handle(self):
           return self.__handle

    @property
    def info(self):
           return self.__info



    def get_parameters(self):
            return self.__parameters

    def set_parameters(self, parameters: dict[str, ParameterValue] = {}):
            self.__parameters.update(parameters)

    def get_parameter(self, name: str) -> ParameterValue | None:
        if self.__parameters.__contains__(name):
           return self.__parameters[name]
        return None

    def set_parameter(self, name: str, value: ParameterValue):
            if name in self.__parameters:
                    self.__parameters[name] = value


def is_url(url_string: str, default_scheme: str = "https") -> bool:
    if not isinstance(url_string, str):
        return False
    original_trimmed = url_string.strip()
    if not original_trimmed:
        return False

    if default_scheme not in ("http", "https"):
        default_scheme = "https"
    url_to_validate = original_trimmed
    parsed = urlparse(original_trimmed)
    if not parsed.scheme:
        if original_trimmed.startswith('//'):
            url_to_validate = f"{default_scheme}:{original_trimmed}"
        else:
            potential_host = parsed.path.split('/')[0]
            if '.' in original_trimmed or 'localhost' in potential_host.lower():
                 url_to_validate = f"{default_scheme}://{original_trimmed}"
            else:
                 return False

    try:
        result = url(url_to_validate)
        return bool(result)
    except ValidationError:
        return False
    except Exception:
        return False
       

def is_path(path_str:str) -> bool:
    if not isinstance(path_str, str) or path_str == "":
        return False
    try:
        path = Path(path_str)
        return True
    except:
          return False
```

#### File: `files-rc\__AV_Instance.py`

```python
import random
import os

from .media_info import MediaInfo
from .__AV_Interface import AVMediaInterface
from .__AV_Common import *


class AVMediaInstance:


    def __init__(self, controler:AVMediaInterface, file_path:str = ""):
        self.__controler = controler
        self.__media_type = self.__controler.type
        self.__media_backend = self.__controler.backend
        self.__media_source:AVMediaSource = AVMediaSource.AV_SRC_NOT_SET
        self.__file_path = file_path
        self.__id:int = random.randint(1000000, 9999999)
        self.__filters:dict[int, AVFilter] = {}


    @property
    def media_type(self):
        return self.__media_type

    @property
    def media_backend(self):
        return self.__media_backend

    @property
    def media_source(self):
        return self.__media_source

    @property
    def instance_id(self):
        return self.__id

    @property
    def file_path(self):
        return self.__file_path


    # Media control methods
    def load_file(self, file_path:str):
        #if self.get_playback_state() == AVPlaybackState.AV_STATE_PLAYING:
            #self.stop()
        if file_path != "" and is_path(file_path) and os.path.exists(file_path):
            self.__file_path = file_path
            self.__controler.load_file(self.__id, file_path)

    def load_url(self, url:str):
        if self.get_playback_state() == AVPlaybackState.AV_STATE_PLAYING:
            self.stop()
        if url != "" and is_url(url):
            self.__file_path = url
            self.__controler.load_url(self.__id, url)

    def play(self):
        self.__controler.play(self.__id)

    def pause(self):
        self.__controler.pause(self.__id)

    def stop(self):
        self.__controler.stop(self.__id)

    def mute(self):
        self.__controler.mute(self.__id)

    def unmute(self):
        self.__controler.unmute(self.__id)

    def set_position(self, position:int):
        self.__controler.set_position(self.__id, position)

    def set_volume(self, offset:float):
        self.__controler.set_volume(self.__id, offset)

    def set_loop(self, loop:bool):
        self.__controler.set_loop(self.__id, loop)

    def get_length(self) -> int:
        return self.__controler.get_length(self.__id, )

    def get_position(self) -> int:
        return self.__controler.get_position(self.__id, )

    def get_volume(self) -> float:
        return self.__controler.get_volume(self.__id, )

    def get_playback_state(self) -> AVPlaybackState:
        return self.__controler.get_play_state(self.__id, )

    def get_mute_state(self) -> AVMuteState:
        return self.__controler.get_mute_state(self.__id, )

    # Effects/filters
    def apply_filter(self, filter:AVFilter) -> int:
        if filter.type != self.media_type and filter.backend != self.media_backend:
            return -1
        filter_id = random.randint(1000000, 9999999)
        self.__filters[filter_id] = filter
        self.__controler.apply_filter(self.__id, filter_id, filter)
        return filter_id

    def remove_filter(self, filter_id:int):
        if filter_id in self.__filters:
            self.__filters.pop(filter_id)
            self.__controler.remove_filter(self.__id, filter_id )

    def remove_filters(self):

        for filter_id in list(self.__filters.keys()):
            try:
                self.remove_filter(filter_id)
            except:
                if filter_id in self.__filters:
                    self.__filters.pop(filter_id)

    def set_parameter(self, filter_id:int, parameter_name:str, parameter_value:ParameterValue):
        if filter_id in self.__filters and parameter_name in self.__filters[filter_id].get_parameters():
            self.__controler.set_parameter(self.__id, filter_id, parameter_name, parameter_value)

    def get_parameter(self, filter_id:int, parameter_name:str) -> ParameterValue | None:
        if filter_id in self.__filters and parameter_name in self.__filters[filter_id].get_parameters():
            return self.__controler.get_parameter(self.__id, filter_id, parameter_name)
        return None

    def release(self):

        try:
            if self.get_playback_state() == AVPlaybackState.AV_STATE_PLAYING:
                self.stop()
        except:
            pass
        

        try:
            self.remove_filters()
        except:
            pass
        

        try:
            self.__controler.release(self.__id)
        except:
            pass

    def media_info(self) -> Any:
        return MediaInfo(self.__file_path)
```

#### File: `files-rc\__AV_Player.py`

```python
from abc import ABC, abstractmethod
from .__AV_Common import *
from .__AV_Instance import AVMediaInstance
from .__AV_Interface import AVMediaInterface
from .playlist import Playlist
import threading
import time
import random
from typing import List, Optional, Callable


class AVPlayer(ABC):


    def __init__(self, media_type:AVMediaType, media_backend:AVMediaBackend, interface:AVMediaInterface) -> None:
        super().__init__()
        self._media_type = media_type
        self._media_backend = media_backend
        self._controler = interface
        self._config:dict[str, Any] = {}
        self._primary_instance:AVMediaInstance|None = None
        self._current_playlist:Playlist|None = None
        self._current_playlist_index = -1
        

        self._auto_play_enabled = False
        self._playlist_mode = AVPlaylistMode.SEQUENTIAL
        self._playlist_state = AVPlaylistState.STOPPED
        self._monitor_thread:threading.Thread|None = None
        self._monitor_running = False
        self._shuffle_order:List[int] = []
        self._track_end_callback:Optional[Callable[[int], None]] = None


    @property
    def media_type(self):
        return self._media_type

    @property
    def media_backend(self):
        return self._media_backend

    @property
    def config(self):
        return self._config

    @property
    def primary_instance(self):
            return self._primary_instance

    @property
    def current_playlist(self):
        return self._current_playlist


    def create_file_instance(self, file_path:str) -> AVMediaInstance:
        instance:AVMediaInstance = AVMediaInstance(self._controler)
        instance.load_file(file_path)
        return instance

    def create_url_instance(self, url:str) -> AVMediaInstance:
        instance:AVMediaInstance = AVMediaInstance(self._controler)
        instance.load_url(url)
        return instance

    def set_config_value(self, name:str, value:Any):
        self._config[name] = value

    def get_config(self, name) -> Any:
        if name in self._config:
            return self._config[name]
        return None

    def load_playlist(self, playlist:Playlist, auto_play:bool = False, mode:AVPlaylistMode = AVPlaylistMode.SEQUENTIAL):
        """Load playlist with optional auto-play functionality"""
        if playlist is not None:
            self._current_playlist = playlist
            self._auto_play_enabled = auto_play
            self._playlist_mode = mode
            self._playlist_state = AVPlaylistState.STOPPED


            if mode == AVPlaylistMode.SHUFFLE:
                self._generate_shuffle_order()

            if self._primary_instance is not None:
                self._primary_instance.stop()
            else:
                self._primary_instance = AVMediaInstance(self._controler)
                
            if len(playlist) > 0:
                self._current_playlist_index = 0
                if auto_play:
                    self._play_playlist_track()
                    self._start_monitor()

    def set_playlist_mode(self, mode:AVPlaylistMode):
        """Change playlist playback mode"""
        self._playlist_mode = mode
        if mode == AVPlaylistMode.SHUFFLE:
            self._generate_shuffle_order()

    def set_auto_play(self, enabled:bool):
        """Enable/disable auto-play functionality"""
        self._auto_play_enabled = enabled
        if enabled and self._current_playlist and len(self._current_playlist) > 0:
            self._start_monitor()
        else:
            self._stop_monitor()

    def set_track_end_callback(self, callback:Optional[Callable[[int], None]]):
        """Set callback function called when a track ends"""
        self._track_end_callback = callback

    def get_playlist_state(self) -> AVPlaylistState:
        """Get current playlist state"""
        return self._playlist_state

    def get_playlist_mode(self) -> AVPlaylistMode:
        """Get current playlist mode"""
        return self._playlist_mode

    def is_auto_play_enabled(self) -> bool:
        """Check if auto-play is enabled"""
        return self._auto_play_enabled

    def get_current_track_index(self) -> int:
        """Get current track index in playlist"""
        return self._current_playlist_index

    def previous(self):
        if self._current_playlist is not None and len(self._current_playlist) > 0:
            if self._playlist_mode == AVPlaylistMode.SHUFFLE:

                current_shuffle_pos = self._shuffle_order.index(self._current_playlist_index)
                current_shuffle_pos = max(0, current_shuffle_pos - 1)
                self._current_playlist_index = self._shuffle_order[current_shuffle_pos]
            else:
                self._current_playlist_index = max(0, self._current_playlist_index - 1)
            self._play_playlist_track()

    def next(self):
        if self._current_playlist is not None and len(self._current_playlist) > 0:
            self._advance_track()

    def stop_playlist(self):
        """Stop playlist playback"""
        if self._primary_instance:
            self._primary_instance.stop()
        self._playlist_state = AVPlaylistState.STOPPED
        self._stop_monitor()

    def pause_playlist(self):
        """Pause playlist playback"""
        if self._primary_instance:
            self._primary_instance.pause()
        self._playlist_state = AVPlaylistState.PAUSED

    def resume_playlist(self):
        """Resume playlist playback"""
        if self._primary_instance:
            self._primary_instance.play()
        self._playlist_state = AVPlaylistState.PLAYING
        if self._auto_play_enabled:
            self._start_monitor()

    def jump_to_track(self, index: int):
        """Jump to a specific track index in the playlist"""
        if self._current_playlist is not None and 0 <= index < len(self._current_playlist):
            self._current_playlist_index = index
            self._play_playlist_track()
            return True
        return False

    def _generate_shuffle_order(self):
        """Generate random order for shuffle mode"""
        if self._current_playlist:
            self._shuffle_order = list(range(len(self._current_playlist)))
            random.shuffle(self._shuffle_order)

    def _advance_track(self):
        """Advance to next track based on current mode"""
        if not self._current_playlist or len(self._current_playlist) == 0:
            return

        if self._playlist_mode == AVPlaylistMode.REPEAT_ONE:

            pass
        elif self._playlist_mode == AVPlaylistMode.SHUFFLE:

            try:
                current_shuffle_pos = self._shuffle_order.index(self._current_playlist_index)
                current_shuffle_pos += 1
                if current_shuffle_pos >= len(self._shuffle_order):
                    if self._playlist_mode == AVPlaylistMode.REPEAT_ALL:
                        current_shuffle_pos = 0
                    else:
                        self._playlist_state = AVPlaylistState.FINISHED
                        return
                self._current_playlist_index = self._shuffle_order[current_shuffle_pos]
            except ValueError:
                self._current_playlist_index = self._shuffle_order[0] if self._shuffle_order else 0
        else:

            self._current_playlist_index += 1
            if self._current_playlist_index >= len(self._current_playlist):
                if self._playlist_mode == AVPlaylistMode.REPEAT_ALL:
                    self._current_playlist_index = 0
                else:
                    self._playlist_state = AVPlaylistState.FINISHED
                    return

        self._play_playlist_track()

    def _start_monitor(self):
        """Start background thread to monitor track completion"""
        if not self._monitor_running:
            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self._monitor_thread.start()

    def _stop_monitor(self):
        """Stop background monitoring thread"""
        self._monitor_running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)

    def _monitor_playback(self):
        """Background thread that monitors track completion"""
        consecutive_errors = 0
        base_sleep_time = 0.1
        heavy_usage_sleep_time = 0.5
        
        while self._monitor_running and self._auto_play_enabled:
            try:
                if self._primary_instance:
                    # Check if MPV is under heavy load (for MPV backend)
                    sleep_time = base_sleep_time
                    if hasattr(self._controler, 'is_heavy_usage_period') and self._controler.is_heavy_usage_period():
                        sleep_time = heavy_usage_sleep_time  # Reduce monitoring frequency during heavy usage
                    
                    state = self._primary_instance.get_playback_state()
                    
                    if state == AVPlaybackState.AV_STATE_PLAYING:
                        self._playlist_state = AVPlaylistState.PLAYING
                        consecutive_errors = 0  # Reset error counter on success
                        
                        # Only check position if we're not in heavy usage mode
                        if sleep_time == base_sleep_time:
                            position = self._primary_instance.get_position()
                            length = self._primary_instance.get_length()
                            
                            if length > 0 and position >= length - 1:
                                # Track ended
                                current_track = self._current_playlist_index
                                if self._track_end_callback:
                                    self._track_end_callback(current_track)
                                
                                time.sleep(0.5)
                                self._advance_track()
                        
                    elif state in [AVPlaybackState.AV_STATE_STOPPED, AVPlaybackState.AV_STATE_NOTHING]:
                        if self._playlist_state == AVPlaylistState.PLAYING:
                            # Unexpected stop, advance to next track
                            consecutive_errors = 0
                            self._advance_track()
                
                time.sleep(sleep_time)
                
            except Exception as e:
                consecutive_errors += 1
                # Exponential backoff on errors to prevent spam
                error_sleep_time = min(2.0, 0.1 * (2 ** consecutive_errors))
                time.sleep(error_sleep_time)
                
                # If too many consecutive errors, stop monitoring temporarily
                if consecutive_errors >= 10:
                    time.sleep(5.0)
                    consecutive_errors = 0

    def _play_playlist_track(self):
        if self._primary_instance is None:
            self._primary_instance = AVMediaInstance(self._controler)
        
        if self._current_playlist and 0 <= self._current_playlist_index < len(self._current_playlist):
            instance_path = self._current_playlist.entries[self._current_playlist_index].location
            if is_path(instance_path):
                self._primary_instance.load_file(instance_path)
            else:
                self._primary_instance.load_url(instance_path)
            self._primary_instance.play()
            self._playlist_state = AVPlaylistState.PLAYING


    @abstractmethod
    def init(self, *args, **kw):
        pass

    @abstractmethod
    def release(self):

        self._stop_monitor()
        pass

    def set_device(self, index:int):
        device_count:int  = self._controler.get_devices()
        if index < device_count and index >= 0:
            self._controler.set_device(index)
        else:
            raise IndexError

    def get_device(self, index:int) -> AVDevice | None:
        device_count:int  = self._controler.get_devices()
        if index < device_count and index >= 0:
            return self._controler.get_device_info(index)
        else:
            raise IndexError

    def get_devices(self) -> int:
        return self._controler.get_devices()

    def get_current_device(self) -> int:
        return self._controler.get_current_device()


```

#### File: `files-rc\mpv_audio_filter.py`

```python
from typing import Any
from .__AV_Common import *
from .audio_filter import AudioFilter

class MPVAudioFilter(AVFilter):
    def __init__(self, filter_handle: str, parameters: dict[str, ParameterValue], backend_additional_info: dict[Any, Any]):
        super().__init__(AVFilterType.AV_TYPE_AUDIO, AVMediaBackend.AV_BACKEND_MPV, filter_handle, parameters, backend_additional_info)
        self._validate_parameters()
    
    def _validate_parameters(self):
        mpv_param_map = self.info.get("mpv_param_map", {})
        current_params = self.get_parameters()
        
        for param_name, param_value in current_params.items():
            if param_name in mpv_param_map:
                _, param_type, param_range = mpv_param_map[param_name]
                
                if not isinstance(param_value, param_type):
                    raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_TYPE, 
                                f"Parameter {param_name} must be of type {param_type.__name__}")
                
                if param_range and param_type in [int, float]:
                    min_val, max_val = param_range[:2]
                    if not (min_val <= param_value <= max_val):
                        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_RANGE,
                                    f"Parameter {param_name} must be between {min_val} and {max_val}")
    
    def set_parameter(self, name: str, value: ParameterValue):
        mpv_param_map = self.info.get("mpv_param_map", {})
        if name in mpv_param_map:
            _, param_type, param_range = mpv_param_map[name]
            
            if not isinstance(value, param_type):
                raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_TYPE,
                            f"Parameter {name} must be of type {param_type.__name__}")
            
            if param_range and param_type in [int, float]:
                min_val, max_val = param_range[:2]
                if not (min_val <= value <= max_val):
                    raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_RANGE,
                                f"Parameter {name} must be between {min_val} and {max_val}")
        
        super().set_parameter(name, value)
    
    def construct(self) -> str:
        mpv_filter_name = self.info.get("mpv_filter_name", "")
        effect_syntax = self.info.get("effect_syntax", "lavfi")
        mpv_param_map = self.info.get("mpv_param_map", {})
        
        if not mpv_filter_name:
            return ""
        
        params = self.get_parameters()
        param_strings = []
        
        for param_name, param_value in params.items():
            if param_name in mpv_param_map:
                mpv_param_name, _, _ = mpv_param_map[param_name]
                param_strings.append(f"{mpv_param_name}={param_value}")
        
        param_string = ":".join(param_strings)
        
        if effect_syntax == "lavfi":
            if param_string:
                return f"lavfi=[{mpv_filter_name}={param_string}]"
            else:
                return f"lavfi=[{mpv_filter_name}]"
        elif effect_syntax == "@rb":
            if param_string:
                return f"@rb:{mpv_filter_name}={param_string}"
            else:
                return f"@rb:{mpv_filter_name}"
        else:
            if param_string:
                return f"{mpv_filter_name}={param_string}"
            else:
                return mpv_filter_name


class MPVEchoFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "in_gain": ("in_gain", float, (0.0, 1.0, 0.05, 0.6)),
            "out_gain": ("out_gain", float, (0.0, 1.0, 0.05, 0.3)),
            "delays": ("delays", str, ()),
            "decays": ("decays", str, ())
        }
        
        parameters = {
            "in_gain": 0.6,
            "out_gain": 0.3,
            "delays": "1000",
            "decays": "0.5"
        }
        
        backend_info = {
            "mpv_filter_name": "aecho",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Echo", parameters, backend_info)

class MPVReverbFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "dry": ("dry", float, (0.0, 1.0, 0.1, 1.0)),
            "wet": ("wet", float, (0.0, 1.0, 0.1, 0.3)),
            "length": ("length", int, (1, 100, 1, 1)),
            "irnorm": ("irnorm", float, (-1.0, 2.0, 0.1, 1.0)),
            "irgain": ("irgain", float, (0.0, 1.0, 0.1, 1.0))
        }
        
        parameters = {
            "dry": 1.0,
            "wet": 0.3,
            "length": 1,
            "irnorm": 1.0,
            "irgain": 1.0
        }
        
        backend_info = {
            "mpv_filter_name": "afir",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Reverb", parameters, backend_info)

class MPVLowPassFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 500.0)),
            "poles": ("poles", int, (1, 2, 1, 2)),
            "width": ("width", float, (0.1, 10.0, 0.1, 0.707)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0))
        }
        
        parameters = {
            "frequency": 500.0,
            "poles": 2,
            "width": 0.707,
            "mix": 1.0
        }
        
        backend_info = {
            "mpv_filter_name": "lowpass",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Low Pass", parameters, backend_info)

class MPVHighPassFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 3000.0)),
            "poles": ("poles", int, (1, 2, 1, 2)),
            "width": ("width", float, (0.1, 10.0, 0.1, 0.707)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0))
        }
        
        parameters = {
            "frequency": 3000.0,
            "poles": 2,
            "width": 0.707,
            "mix": 1.0
        }
        
        backend_info = {
            "mpv_filter_name": "highpass",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("High Pass", parameters, backend_info)

class MPVCompressorFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.015625, 64.0, 0.1, 1.0)),
            "threshold": ("threshold", float, (0.00097563, 1.0, 0.01, 0.125)),
            "ratio": ("ratio", float, (1.0, 20.0, 0.1, 2.0)),
            "attack": ("attack", float, (0.01, 2000.0, 1.0, 20.0)),
            "release": ("release", float, (0.01, 9000.0, 1.0, 250.0)),
            "makeup": ("makeup", float, (1.0, 64.0, 0.1, 1.0)),
            "knee": ("knee", float, (1.0, 8.0, 0.1, 2.82843)),
            "detection": ("detection", str, ()),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0))
        }
        
        parameters = {
            "level_in": 1.0,
            "threshold": 0.125,
            "ratio": 2.0,
            "attack": 20.0,
            "release": 250.0,
            "makeup": 1.0,
            "knee": 2.82843,
            "detection": "rms",
            "mix": 1.0
        }
        
        backend_info = {
            "mpv_filter_name": "acompressor",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Compressor", parameters, backend_info)

class MPVFlangerFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "delay": ("delay", float, (0.0, 30.0, 0.1, 0.0)),
            "depth": ("depth", float, (0.0, 10.0, 0.1, 2.0)),
            "regen": ("regen", float, (-95.0, 95.0, 1.0, 0.0)),
            "width": ("width", float, (0.0, 100.0, 1.0, 71.0)),
            "speed": ("speed", float, (0.1, 10.0, 0.1, 0.5)),
            "shape": ("shape", str, ()),
            "phase": ("phase", float, (0.0, 100.0, 1.0, 25.0)),
            "interp": ("interp", str, ())
        }
        
        parameters = {
            "delay": 0.0,
            "depth": 2.0,
            "regen": 0.0,
            "width": 71.0,
            "speed": 0.5,
            "shape": "sinusoidal",
            "phase": 25.0,
            "interp": "linear"
        }
        
        backend_info = {
            "mpv_filter_name": "flanger",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Flanger", parameters, backend_info)

class MPVChorusFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "in_gain": ("in_gain", float, (0.0, 1.0, 0.05, 0.4)),
            "out_gain": ("out_gain", float, (0.0, 1.0, 0.05, 0.4)),
            "delays": ("delays", str, ()),
            "decays": ("decays", str, ()),
            "speeds": ("speeds", str, ()),
            "depths": ("depths", str, ())
        }
        
        parameters = {
            "in_gain": 0.4,
            "out_gain": 0.4,
            "delays": "55",
            "decays": "0.4",
            "speeds": "0.25",
            "depths": "2"
        }
        
        backend_info = {
            "mpv_filter_name": "chorus",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Chorus", parameters, backend_info)

class MPVPitchShiftFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "pitch-scale": ("pitch-scale", float, (1.0, 100.0, 1.0, 1.0)),
            "engine": ("engine", str, ("faster", "finer"))
        }
        
        parameters = {
            "pitch-scale": 1.0,
            "engine": "finer"
        }
        
        backend_info = {
            "mpv_filter_name": "rubberband",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "@rb:"
        }
        
        super().__init__("Pitch Shift", parameters, backend_info)

class MPVTempoScaleFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "scale": ("scale", int, (1, 25, 1, 1)),
            "speed": ("speed", str, ("pitch", "none"))
        }
        
        parameters = {
            "scale": 1,
            "speed": "none"
        }
        
        backend_info = {
            "mpv_filter_name": "scaletempo",
            "mpv_param_map": mpv_param_map
        }
        
        super().__init__("Tempo Scale", parameters, backend_info)

class MPVLimiterFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.0, 64.0, 0.1, 1.0)),
            "level_out": ("level_out", float, (0.0, 64.0, 0.1, 1.0)),
            "limit": ("limit", float, (0.0, 1.0, 0.01, 1.0)),
            "attack": ("attack", float, (0.1, 1000.0, 0.1, 5.0)),
            "release": ("release", float, (1.0, 9000.0, 1.0, 50.0)),
            "asc": ("asc", str, ()),
            "asc_level": ("asc_level", float, (0.0, 1.0, 0.1, 0.5)),
            "level": ("level", str, ())
        }
        
        parameters = {
            "level_in": 1.0,
            "level_out": 1.0,
            "limit": 1.0,
            "attack": 5.0,
            "release": 50.0,
            "asc": "false",
            "asc_level": 0.5,
            "level": "true"
        }
        
        backend_info = {
            "mpv_filter_name": "alimiter",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Limiter", parameters, backend_info)

class MPVBandPassFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 3000.0)),
            "width": ("width", float, (0.1, 1000.0, 0.1, 100.0)),
            "csg": ("csg", int, (0, 1, 1, 0)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0)),
            "width_type": ("width_type", str, ())
        }
        
        parameters = {
            "frequency": 3000.0,
            "width": 100.0,
            "csg": 0,
            "mix": 1.0,
            "width_type": "h"
        }
        
        backend_info = {
            "mpv_filter_name": "bandpass",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Band Pass", parameters, backend_info)

class MPVGateFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.015625, 64.0, 0.1, 1.0)),
            "mode": ("mode", str, ()),
            "range": ("range", float, (0.0, 1.0, 0.01, 0.06125)),
            "threshold": ("threshold", float, (0.0, 1.0, 0.01, 0.125)),
            "ratio": ("ratio", float, (1.0, 9000.0, 0.1, 2.0)),
            "attack": ("attack", float, (0.01, 9000.0, 1.0, 20.0)),
            "release": ("release", float, (0.01, 9000.0, 1.0, 250.0)),
            "makeup": ("makeup", float, (1.0, 64.0, 0.1, 1.0)),
            "knee": ("knee", float, (1.0, 8.0, 0.1, 2.828427125)),
            "detection": ("detection", str, ()),
            "link": ("link", str, ())
        }
        
        parameters = {
            "level_in": 1.0,
            "mode": "downward",
            "range": 0.06125,
            "threshold": 0.125,
            "ratio": 2.0,
            "attack": 20.0,
            "release": 250.0,
            "makeup": 1.0,
            "knee": 2.828427125,
            "detection": "rms",
            "link": "average"
        }
        
        backend_info = {
            "mpv_filter_name": "agate",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Gate", parameters, backend_info)
        
```

#### File: `files-rc\mpv_video_player.py`

```python
import mpv
import os
import threading
import time
from typing import Dict, Any, Union, List, Callable
from .__AV_Common import *
from .__AV_Instance import AVMediaInstance
from .__AV_Interface import AVMediaInterface
from .__AV_Player import AVPlayer
from .mpv_audio_filter import MPVAudioFilter

def handle_mpv_error(call_func: Callable) -> Any:
    try:
        return call_func()
    except mpv.PropertyUnavailableError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER, f"Property unavailable: {str(e)}")
    except AttributeError as e:
        if "mpv property does not exist" in str(e) or "does not exist" in str(e):
            raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER, f"Property not available: {str(e)}")
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Attribute error: {str(e)}")
    except mpv.ShutdownError:
        raise AVError(AVErrorInfo.INVALID_HANDLE, "MPV core has been shutdown")
    except RuntimeError as e:
        if "loading failed" in str(e).lower():
            raise AVError(AVErrorInfo.FILE_NOTFOUND, f"File loading failed: {str(e)}")
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Runtime error: {str(e)}")
    except SystemError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER, f"Command error: {str(e)}")
    except TypeError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_TYPE, f"Type error: {str(e)}")
    except ValueError as e:
        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_VALUE, f"Value error: {str(e)}")
    except Exception as e:
        raise AVError(AVErrorInfo.UNKNOWN_ERROR, f"Unknown error: {str(e)}")

class MPVMediaInterface(AVMediaInterface):
    
    def __init__(self) -> None:
        super().__init__(AVMediaType.AV_TYPE_VIDEO, AVMediaBackend.AV_BACKEND_MPV)
        self.__instances:dict[int, str] = {}
        self.__mpv: mpv.MPV | None = None
        self.__current_id: int | None = None
        self.__applied_filters: Dict[int, MPVAudioFilter] = {}
        self.__is_initialized = False
        self.__stopped = False
        self.__end_reached = False
        self.__mpv_lock = threading.RLock()
        self.__command_count = 0
        self.__last_command_time = 0.0

    def _track_command(self):
        current_time = time.time()
        self.__command_count += 1
        if current_time - self.__last_command_time > 1.0:
            self.__command_count = 1
        self.__last_command_time = current_time
    
    def is_heavy_usage_period(self) -> bool:
        return self._is_heavy_usage()

    def _is_heavy_usage(self) -> bool:
        return self.__command_count > 20
    
    def _mpv_call(self, func: Callable, timeout: float = 0.5) -> Any:
        if not self.__mpv_lock.acquire(timeout=timeout):
            raise AVError(AVErrorInfo.INVALID_HANDLE, "MPV access timeout - too many concurrent operations")
        try:
            self._track_command()
            return handle_mpv_error(func)
        finally:
            self.__mpv_lock.release()

    def init(self, *args, **kw):
        try:
            config = kw.get("config", {})
            window = kw.get("window", None)
            
            if window is not None:
                config['wid'] = str(int(window))
            
            config.setdefault('ytdl', True)
            config.setdefault('input_default_bindings', True)
            
            self.__mpv = mpv.MPV(**config)
            
            ytdl_path = kw.get("ytdl_path", None)
            if ytdl_path:
                pass
            
            self.__is_initialized = True
            self.__stopped = False
            self.__end_reached = False
            
        except Exception as e:
            raise AVError(AVErrorInfo.INITIALIZATION_ERROR, f"Failed to initialize MPV: {str(e)}")

    def free(self):
        if self.__mpv is not None:
            try:
                if not self.__mpv.core_shutdown:
                    self.__mpv.terminate()
                self.__mpv = None
                self.__current_id = None
                self.__applied_filters.clear()
                self.__is_initialized = False
                self.__stopped = False
                self.__end_reached = False
            except Exception:
                pass

    def _check_initialized(self):
        if not self.__is_initialized or self.__mpv is None:
            raise AVError(AVErrorInfo.UNINITIALIZED, "MPV not initialized")
        if self.__mpv.core_shutdown:
            raise AVError(AVErrorInfo.INVALID_HANDLE, "MPV core has been shutdown")

    def _check_instance(self, id: int):
        self._check_initialized()
        if self.__current_id != id:
            raise AVError(AVErrorInfo.INVALID_HANDLE, f"Invalid instance ID: {id}")

    def get_mpv_instance(self):
        self._check_initialized()
        return self.__mpv

    def load_file(self, id: int, path: str):
        self._check_initialized()

        def loadfile():
            assert self.__mpv is not None
            self.__mpv.command("loadfile", path)
        
        if path and is_path(path) and os.path.exists(path):
            self.__current_id = id
            self.__instances[id] = path
            self.__stopped = False
            self.__end_reached = False
            self._load_subtitles(path)
            handle_mpv_error(loadfile)

    def load_url(self, id: int, url: str):
        self._check_initialized()
        
        def loadurl():
            assert self.__mpv is not None
            self.__mpv.command("loadfile", url)
        
        if url and is_url(url):
            self.__current_id = id
            self.__instances[id] = url
            self.__stopped = False
            self.__end_reached = False
            handle_mpv_error(loadurl)

    def _load_subtitles(self, path: str):
        subtitle_formats = ["idx", "sub", "srt", "rt", "ssa", "ass", "mks", "vtt", "sup", "scc", "smi", "lrc", "pgs"]
        dir_path = os.path.dirname(path)
        filename = os.path.splitext(os.path.basename(path))[0]
        
        for format in subtitle_formats:
            subtitle_path = os.path.join(dir_path, f"{filename}.{format}")
            if os.path.exists(subtitle_path):
                def add_subtitle():
                    assert self.__mpv is not None
                    self.__mpv.sub_add(subtitle_path)
                handle_mpv_error(add_subtitle)
                break

    def release(self, id: int):
        if self.__current_id == id:
            self._check_initialized()
            
            def stop():
                assert self.__mpv is not None
                self.__mpv.stop()
            handle_mpv_error(stop)
            self.__current_id = None
            self.__applied_filters.clear()
            self.__stopped = True
            self.__end_reached = False

    def play(self, id: int):
        self._check_instance(id)
        
        def resume():
            assert self.__mpv is not None
            if self.__end_reached or self.__mpv.time_pos is None:
                self.__mpv.command("loadfile", self.__instances[id])
                self.__end_reached = False
                self.__stopped = False
            self.__mpv.pause = False
        
        self.__stopped = False
        self._mpv_call(resume, timeout=1.0)

    def pause(self, id: int):
        self._check_instance(id)
        
        def pause_play():
            assert self.__mpv is not None
            self.__mpv.pause = True
        self._mpv_call(pause_play, timeout=0.5)

    def mute(self, id: int):
        self._check_instance(id)
        
        def toggle_mute():
            assert self.__mpv is not None
            self.__mpv.mute = not self.__mpv.mute
        self._mpv_call(toggle_mute, timeout=0.5)

    def unmute(self, id: int):
        self._check_instance(id)
        
        def unmute_audio():
            assert self.__mpv is not None
            self.__mpv.mute = False
        self._mpv_call(unmute_audio, timeout=0.5)

    def stop(self, id: int):
        self._check_instance(id)
        
        def halt():
            assert self.__mpv is not None
            self.__mpv.stop()
        
        self._mpv_call(halt, timeout=1.0)
        self.__stopped = True
        self.__end_reached = False

    def set_volume(self, id: int, offset: float):
        self._check_instance(id)
        
        def set_vol():
            assert self.__mpv is not None
            self.__mpv.volume = offset
        self._mpv_call(set_vol, timeout=0.5)

    def set_position(self, id: int, offset: int):
        self._check_instance(id)
        
        def seek():
            assert self.__mpv is not None
            self.__mpv.seek(offset, "absolute")
        self._mpv_call(seek, timeout=0.5)

    def set_loop(self, id: int, loop: bool):
        self._check_instance(id)
        loop_value = "inf" if loop else "no"
        
        def set_loop_mode():
            assert self.__mpv is not None
            self.__mpv.loop = loop_value
        self._mpv_call(set_loop_mode, timeout=0.5)

    def get_length(self, id: int) -> int:
        self._check_instance(id)
        
        def get_duration():
            assert self.__mpv is not None
            return self.__mpv.duration
        duration = self._mpv_call(get_duration, timeout=0.1)
        return int(duration) if duration is not None else 0

    def get_position(self, id: int) -> int:
        self._check_instance(id)
        
        def get_time():
            assert self.__mpv is not None
            return self.__mpv.time_pos
        pos = self._mpv_call(get_time, timeout=0.1)
        return int(pos) if pos is not None else 0

    def get_play_state(self, id: int) -> AVPlaybackState:
        self._check_instance(id)
        try:
            def get_state_info():
                assert self.__mpv is not None
                return {
                    'pause': self.__mpv.pause,
                    'time_pos': self.__mpv.time_pos,
                    'duration': self.__mpv.duration
                }
            
            if self.__stopped:
                return AVPlaybackState.AV_STATE_STOPPED
            
            state_info = self._mpv_call(get_state_info, timeout=0.1)
            
            is_paused = state_info['pause']
            time_pos = state_info['time_pos']
            duration = state_info['duration']
            
            if duration is not None and time_pos is not None:
                if time_pos >= duration - 0.1:
                    self.__end_reached = True
                    return AVPlaybackState.AV_STATE_NOTHING
            elif time_pos is None and duration is not None:
                self.__end_reached = True
                return AVPlaybackState.AV_STATE_NOTHING
            
            if is_paused:
                return AVPlaybackState.AV_STATE_PAUSED
            else:
                return AVPlaybackState.AV_STATE_PLAYING
                
        except AVError:
            return AVPlaybackState.AV_STATE_NOTHING

    def get_mute_state(self, id: int) -> AVMuteState:
        self._check_instance(id)
        
        def get_mute():
            assert self.__mpv is not None
            return self.__mpv.mute
        muted = self._mpv_call(get_mute, timeout=0.1)
        return AVMuteState.AV_AUDIO_MUTED if muted else AVMuteState.AV_AUDIO_UNMUTED

    def get_volume(self, id: int) -> float:
        self._check_instance(id)
        
        def get_vol():
            assert self.__mpv is not None
            return self.__mpv.volume
        volume = self._mpv_call(get_vol, timeout=0.1)
        return float(volume) if volume is not None else 0.0

    def get_loop(self, id: int) -> bool:
        self._check_instance(id)
        
        def get_loop_state():
            assert self.__mpv is not None
            return self.__mpv.loop
        loop_val = self._mpv_call(get_loop_state, timeout=0.1)
        return loop_val == "inf" if loop_val is not None else False

    def _rebuild_filter_chain(self):
        filter_strings = []
        
        for filter_obj in self.__applied_filters.values():
            filter_string = filter_obj.construct()
            if filter_string:
                filter_strings.append(filter_string)
        
        return ",".join(filter_strings) if filter_strings else ""

    def apply_filter(self, id: int, filter_id: int, filter_struct: AVFilter):
        self._check_instance(id)
        if not isinstance(filter_struct, MPVAudioFilter):
            raise AVError(AVErrorInfo.INVALID_MEDIA_FILTER, "Filter must be MPVAudioFilter")
        
        self.__applied_filters[filter_id] = filter_struct
        
        filter_chain = self._rebuild_filter_chain()
        
        def set_af_chain():
            assert self.__mpv is not None
            self.__mpv.af = filter_chain
        
        self._mpv_call(set_af_chain, timeout=0.5)

    def remove_filter(self, id: int, filter_id: int):
        self._check_instance(id)
        if filter_id in self.__applied_filters:
            del self.__applied_filters[filter_id]
            
            filter_chain = self._rebuild_filter_chain()
            
            def set_af_chain():
                assert self.__mpv is not None
                self.__mpv.af = filter_chain
            
            self._mpv_call(set_af_chain, timeout=0.5)

    def set_parameter(self, id: int, filter_id: int, parameter_name: str, value: ParameterValue):
        self._check_instance(id)
        if filter_id in self.__applied_filters:
            filter_struct = self.__applied_filters[filter_id]
            filter_struct.set_parameter(parameter_name, value)
            
            filter_chain = self._rebuild_filter_chain()
            
            def set_af_chain():
                assert self.__mpv is not None
                self.__mpv.af = filter_chain
            
            self._mpv_call(set_af_chain, timeout=0.5)

    def get_parameter(self, id: int, filter_id: int, parameter_name: str) -> ParameterValue | None:
        self._check_instance(id)
        if filter_id in self.__applied_filters:
            return self.__applied_filters[filter_id].get_parameter(parameter_name)
        return None

    def get_devices(self) -> int:
        self._check_initialized()
        
        def get_device_list():
            assert self.__mpv is not None
            return self.__mpv.audio_device_list
        audio_devices = self._mpv_call(get_device_list, timeout=0.5) or []
        return len(audio_devices)

    def get_device_info(self, index: int) -> AVDevice:
        self._check_initialized()
        
        def get_device_list():
            assert self.__mpv is not None
            return self.__mpv.audio_device_list
        audio_devices = self._mpv_call(get_device_list, timeout=0.5) or []
        if 0 <= index < len(audio_devices):
            device = audio_devices[index]
            return AVDevice(AVMediaBackend.AV_BACKEND_MPV, device.get('description', device.get('name', 'Unknown')))
        raise IndexError("Device index out of range")

    def set_device(self, index: int):
        self._check_initialized()
        
        def get_device_list():
            assert self.__mpv is not None
            return self.__mpv.audio_device_list
        def set_audio_device(device_name):
            assert self.__mpv is not None
            self.__mpv.audio_device = device_name
        audio_devices = self._mpv_call(get_device_list, timeout=0.5) or []
        if 0 <= index < len(audio_devices):
            device_name = audio_devices[index]['name']
            self._mpv_call(lambda: set_audio_device(device_name), timeout=0.5)
        else:
            raise IndexError("Device index out of range")

    def get_current_device(self) -> int:
        self._check_initialized()
        
        def get_audio_device():
            assert self.__mpv is not None
            return self.__mpv.audio_device
        def get_device_list():
            assert self.__mpv is not None
            return self.__mpv.audio_device_list
        current_device = self._mpv_call(get_audio_device, timeout=0.5)
        audio_devices = self._mpv_call(get_device_list, timeout=0.5) or []
        
        for i, device in enumerate(audio_devices):
            if device['name'] == current_device:
                return i
        return 0


class MPVVideoPlayer(AVPlayer):
    
    def __init__(self) -> None:
        self.__mpv_interface:MPVMediaInterface = MPVMediaInterface()
        super().__init__(AVMediaType.AV_TYPE_VIDEO, AVMediaBackend.AV_BACKEND_MPV, self.__mpv_interface)

    def init(self, *args, **kw):
        self._controler.init(*args, **kw)

    def release(self):
        if self._primary_instance is not None:
            self._primary_instance.release()
            self._primary_instance = None
        self._controler.free()

    def create_file_instance(self, file_path:str) -> AVMediaInstance:
        if self._primary_instance is None:
            self._primary_instance = AVMediaInstance(self._controler)
        self._primary_instance.load_file(file_path)
        return self._primary_instance

    def create_url_instance(self, url:str) -> AVMediaInstance:
        if self._primary_instance is None:
            self._primary_instance = AVMediaInstance(self._controler)
        self._primary_instance.load_url(url)
        return self._primary_instance

    def set_window(self, window):
        def set_wid():
            mpv_instance = self.__mpv_interface.get_mpv_instance()
            if mpv_instance:
                mpv_instance._set_property("wid", str(int(window)))
        self.__mpv_interface._mpv_call(set_wid, timeout=1.0)

    def forward(self, offset):
        def seek_forward():
            mpv_instance = self.__mpv_interface.get_mpv_instance()
            if mpv_instance:
                mpv_instance.seek(+offset, reference='relative')
        self.__mpv_interface._mpv_call(seek_forward, timeout=0.5)

    def backward(self, offset):
        def seek_backward():
            mpv_instance = self.__mpv_interface.get_mpv_instance()
            if mpv_instance:
                mpv_instance.seek(-offset, reference='relative')
        self.__mpv_interface._mpv_call(seek_backward, timeout=0.5)

    def set_volume_relative(self, direction, offset):
        def adjust_volume():
            mpv_instance = self.__mpv_interface.get_mpv_instance()
            if mpv_instance:
                current_volume = mpv_instance.volume
                if direction == "up":
                    mpv_instance.volume = current_volume + offset
                elif direction == "down":
                    mpv_instance.volume = current_volume - offset
        self.__mpv_interface._mpv_call(adjust_volume, timeout=0.5)

    def set_fullscreen(self, state):
        def toggle_fullscreen():
            mpv_instance = self.__mpv_interface.get_mpv_instance()
            if mpv_instance:
                mpv_instance.fullscreen = state
        self.__mpv_interface._mpv_call(toggle_fullscreen, timeout=0.5)

    def get_fullscreen(self):
        def get_fs_state():
            mpv_instance = self.__mpv_interface.get_mpv_instance()
            if mpv_instance:
                return mpv_instance.fullscreen
            return False
        return self.__mpv_interface._mpv_call(get_fs_state, timeout=0.1)

    def set_playback_speed(self, speed):
        def set_speed():
            mpv_instance = self.__mpv_interface.get_mpv_instance()
            if mpv_instance:
                mpv_instance.speed = speed
        self.__mpv_interface._mpv_call(set_speed, timeout=0.5)

    def set_resolution(self, width, height):
        def set_res():
            mpv_instance = self.__mpv_interface.get_mpv_instance()
            if mpv_instance:
                mpv_instance.vf = f"scale={width}:{height}"
        self.__mpv_interface._mpv_call(set_res, timeout=0.5)

    def set_start_file_callback(self, callback):
        mpv_instance = self.__mpv_interface.get_mpv_instance()
        if mpv_instance:
            @mpv_instance.event_callback('file-loaded')
            def start_file_handler(event):
                if callback: callback(event)

            return start_file_handler

        return None

    def set_end_file_callback(self, callback):
        mpv_instance = self.__mpv_interface.get_mpv_instance()
        if mpv_instance:
            @mpv_instance.event_callback('end-file')
            def end_file_handler(event):
                if callback: callback(event)
            return end_file_handler
        return None

    def set_shutdown_callback(self, callback):
        mpv_instance = self.__mpv_interface.get_mpv_instance()
        if mpv_instance:
            @mpv_instance.event_callback('shutdown')
            def shutdown_handler(event):
                if callback: callback(event)
            return shutdown_handler
        return None
```

<a name="directory-gui"></a>
### Directory: `gui`


#### File: `gui\__init__.py`

```python

```

#### File: `gui\favorites.py`

```python
from PySide6.QtWidgets import QListWidget, QMenu, QMessageBox
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from app_db import UserFiles
from utilities.util_gui import contextMenu, messageBox


class FavoritesWidget(QListWidget):
    itemRequested = Signal(str)
    
    def __init__(self, user_db: UserFiles, parent=None):
        super().__init__(parent)
        self.user_db = user_db
        self.setAccessibleName("Favorites list")
        self.setAccessibleDescription("List of favorite media files")
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        
        contextMenu(self, self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_activated)
        
        self.load_favorites()
        
    def load_favorites(self):
        self.clear()
        try:
            favorites = self.user_db.get_favorites()
            for fav_path in favorites:
                self.addItem(fav_path)
        except Exception as e:
            print(f"Error loading favorites: {e}")
    
    def add_favorite(self, file_path: str):
        try:
            self.user_db.add_favorite(file_path)
            self.addItem(file_path)
        except Exception as e:
            messageBox("Error", f"Failed to add favorite: {e}")
    
    def remove_favorite(self, file_path: str):
        try:
            self.user_db.remove_favorite(file_path)
            for i in range(self.count()):
                if self.item(i).text() == file_path:
                    self.takeItem(i)
                    break
        except Exception as e:
            messageBox("Error", f"Failed to remove favorite: {e}")
    
    def clear_favorites(self):
        reply = QMessageBox.question(self, "Clear Favorites", 
                                   "Are you sure you want to clear all favorites?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.user_db.clear_favorites()
                self.clear()
            except Exception as e:
                messageBox("Error", f"Failed to clear favorites: {e}")
    
    def show_context_menu(self, position):
        menu = QMenu(self)
        
        clear_action = QAction("Clear All Favorites", self)
        clear_action.triggered.connect(self.clear_favorites)
        menu.addAction(clear_action)
        
        if self.itemAt(position):
            menu.addSeparator()
            remove_action = QAction("Remove from Favorites", self)
            remove_action.triggered.connect(self.remove_current_favorite)
            menu.addAction(remove_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def remove_current_favorite(self):
        current_item = self.currentItem()
        if current_item:
            self.remove_favorite(current_item.text())
    
    def on_item_activated(self, item):
        if item:
            self.itemRequested.emit(item.text())
```

#### File: `gui\hotkeys_dialog.py`

```python
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListView, 
                               QLineEdit, QPushButton, QLabel, QSplitter, QMessageBox)
from PySide6.QtCore import Qt, QModelIndex, Signal
from PySide6.QtGui import QKeySequence, QKeyEvent, QStandardItemModel, QStandardItem
from gui_controls.list_control import Listctrl, ListItem
from app_config import key_config
import re

class KeyCaptureEdit(QLineEdit):
    keySequenceCaptured = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Press keys to capture hotkey...")
        self.setReadOnly(True)
        self.captured_sequence = ""
        
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()
        
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
            
        sequence_parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            sequence_parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            sequence_parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            sequence_parts.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            sequence_parts.append("Win")
            
        key_name = QKeySequence(key).toString()
        if key_name:
            sequence_parts.append(key_name)
            
        self.captured_sequence = "+".join(sequence_parts)
        self.setText(self.captured_sequence)
        self.keySequenceCaptured.emit(self.captured_sequence)
        
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self.captured_sequence:
            self.keySequenceCaptured.emit(self.captured_sequence)

class HotkeysDialog(QDialog):
    def __init__(self, parent=None, reset_callback=None):
        super().__init__(parent)
        self.reset_callback = reset_callback
        self.current_category = None
        self.current_hotkey_row = -1
        self.key_capture_edit = None
        
        self.setWindowTitle("Hotkeys Configuration")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        
        self.setup_ui()
        self.populate_categories()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        self.category_model = QStandardItemModel()
        self.category_list = QListView()
        self.category_list.setModel(self.category_model)
        self.category_list.setMaximumWidth(200)
        self.category_list.selectionModel().currentChanged.connect(self.category_changed)
        
        self.hotkeys_list = Listctrl()
        self.hotkeys_list.column(0, "Action")
        self.hotkeys_list.column(1, "Shortcut")
        
        splitter.addWidget(self.category_list)
        splitter.addWidget(self.hotkeys_list)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self.reset_to_default)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_changes)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        self.hotkeys_list.itemClicked.connect(self.hotkey_item_clicked)
        
    def populate_categories(self):
        self.category_model.clear()
        for category in key_config.key_dict.keys():
            item = QStandardItem(category)
            item.setData(category, Qt.ItemDataRole.UserRole)
            self.category_model.appendRow(item)
            
    def category_changed(self, current: QModelIndex, previous: QModelIndex):
        if not current.isValid():
            return
            
        category = current.data(Qt.ItemDataRole.UserRole)
        self.current_category = category
        self.populate_hotkeys(category)
        
    def populate_hotkeys(self, category):
        self.hotkeys_list.clearAll()
        
        if category not in key_config.key_config:
            return
            
        self.hotkeys_list.column(0, "Action")
        self.hotkeys_list.column(1, "Shortcut")
        
        for action, shortcut in key_config.key_config[category].items():
            self.hotkeys_list.appendRow({
                "0": action,
                "1": shortcut
            })
            
    def hotkey_item_clicked(self, item):
        if not self.current_category:
            return
            
        row = self.hotkeys_list.row(item)
        if row == 0:
            return
            
        self.current_hotkey_row = row
        
        if self.key_capture_edit:
            self.key_capture_edit.deleteLater()
            
        self.key_capture_edit = KeyCaptureEdit(self)
        self.key_capture_edit.keySequenceCaptured.connect(self.update_hotkey)
        
        if isinstance(item, ListItem):
            shortcut_label = item.Widget.labels.get("1_label")
            if shortcut_label:
                rect = shortcut_label.geometry()
                self.key_capture_edit.setGeometry(rect)
                self.key_capture_edit.show()
                self.key_capture_edit.setFocus()
                
    def update_hotkey(self, sequence):
        if not self.current_category or self.current_hotkey_row == -1:
            return
            
        if not key_config.is_valid_hotkey(sequence):
            QMessageBox.warning(self, "Invalid Hotkey", 
                              "The entered hotkey sequence is not valid.")
            return
            
        item = self.hotkeys_list.item(self.current_hotkey_row)
        if item and isinstance(item, ListItem):
            action = item.Widget.columns[0]
            
            key_config.key_config[self.current_category][action] = sequence
            
            self.hotkeys_list.editColumn(self.current_hotkey_row, 1, sequence)
            
        if self.key_capture_edit:
            self.key_capture_edit.hide()
            
    def reset_to_default(self):
        reply = QMessageBox.question(self, "Reset to Default",
                                   "Are you sure you want to reset all hotkeys to default?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            key_config.keysToDefault()
            if self.current_category:
                self.populate_hotkeys(self.current_category)
                
    def apply_changes(self):
        key_config.saveConfig()
        key_config.apply_global_hotkeys()
        if self.reset_callback:
            self.reset_callback()
            
    def accept(self):
        self.apply_changes()
        super().accept()
        super().accept()
```

#### File: `gui\main_window.py`

```python
import os
import sys
import app_guard

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QMenuBar, QMenu, QStatusBar, QToolBar, QDockWidget, QLabel,
    QFileDialog, QInputDialog, QSystemTrayIcon, QApplication, QMessageBox, QDialog, QPushButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence

from app_db import UserFiles
from app_config import prefs
from EXPLORER.explorer_widget import ExplorerWidget
import app_db
from player.player_widget import PlayerWidget
from playlist_manager.playlists_widget import PlaylistsWidget
from playlist_manager.playlist_selection_dialog import PlaylistSelectionDialog
from playlist_manager.playlist_create_dialog import PlaylistCreateDialog
from .favorites import FavoritesWidget
from .recents import RecentsWidget
from .prefs_dialog import PreferencesDialog
from .hotkeys_dialog import HotkeysDialog
from utilities.util_gui import menuItem, messageBox
from utilities.media_utils import get_media_files_from_directory
from av_play import Playlist, PlaylistEntry, formats
from tools.batch_converter_ui import BatchConverterUI
from tools.extractor_ui import ExtractorUI
from tools.tag_editor_ui import TagEditorUI
from tools.thumbnail_generator_ui import ThumbnailGeneratorUI


class ToolDialog(QDialog):


    def __init__(self, tool_widget, title, parent=None):
        super().__init__(parent)
        self.tool_widget = tool_widget
        self.is_minimized = False
        self.original_size = None
        
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumSize(600, 400)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        

        title_bar = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFixedSize(30, 25)
        self.minimize_btn.setToolTip("Minimize to sidebar")
        self.minimize_btn.clicked.connect(self.toggle_minimize)
        title_bar.addWidget(self.minimize_btn)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 25)
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)
        
        layout.addLayout(title_bar)
        layout.addWidget(self.tool_widget)
        
    def toggle_minimize(self):
        if self.is_minimized:
            self.restore_dialog()
        else:
            self.minimize_dialog()
            
    def minimize_dialog(self):
        if not self.is_minimized:
            self.original_size = self.size()
            self.resize(250, 80)
            self.is_minimized = True
            self.minimize_btn.setText("□")
            self.minimize_btn.setToolTip("Restore")
            self.tool_widget.hide()
            
    def restore_dialog(self):
        if self.is_minimized:
            if self.original_size:
                self.resize(self.original_size)
            else:
                self.resize(800, 600)
            self.is_minimized = False
            self.minimize_btn.setText("−")
            self.minimize_btn.setToolTip("Minimize to sidebar")
            self.tool_widget.show()



class MainWindow(QMainWindow):
    fileOpened = Signal(str)
    urlOpened = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        self.user_db = app_db.user_db
        self.current_player_instance = None
        self.is_repeat_enabled = False
        self.tool_dialogs = {}
        
        self.global_hotkeys = {
            "Play/Pause": self.toggle_play_pause,
            "Mute/Unmute": self.toggle_mute,
            "Volume Down": self.volume_down,
            "Volume Up": self.volume_up,
            "Previous": self.previous_track,
            "Next": self.next_track,
        }


        self.user_db.connect_to_database()
        self.setWindowTitle("PlayForm")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
        self.setup_dock_widgets()
        self.setup_main_layout()
        self.setup_system_tray()
        self.connect_signals()
        
        self.restore_window_state()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(10)
        
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.main_splitter)
        
        self.favorites_widget = FavoritesWidget(self.user_db)
        self.recents_widget = RecentsWidget(self.user_db)
        
        self.explorer_widget = ExplorerWidget(
            self.user_db,
            parent=self,
            favorites_callback=self.add_to_favorites,
            open_callback=self.play_file,
            recent_callback=self.add_to_recents,
            playlist_callback=self.add_to_playlist,
            create_playlist_callback=self.create_playlist_from_folder
        )
        
        self.player_widget = PlayerWidget(self)
        
        self.playlists_widget = PlaylistsWidget(
            parent=self,
            play_callback=self.play_file
        )
        
    def setup_menus(self):
        menubar = self.menuBar()
        
        self.file_menu = menubar.addMenu("&File")
        self.setup_file_menu()
        
        self.media_menu = menubar.addMenu("&Media")
        self.setup_media_menu()
        
        self.view_menu = menubar.addMenu("&View")
        self.setup_view_menu()
        
        self.tools_menu = menubar.addMenu("&Tools")
        self.setup_tools_menu()
        
        self.about_menu = menubar.addMenu("&About")
        self.setup_about_menu()
        
    def setup_file_menu(self):
        self.open_file_action = QAction("&Open File...", self)
        self.open_file_action.triggered.connect(self.open_file_dialog)
        self.file_menu.addAction(self.open_file_action)
        
        self.open_url_action = QAction("Open &URL...", self)
        self.open_url_action.triggered.connect(self.open_url_dialog)
        self.file_menu.addAction(self.open_url_action)
        
        self.file_menu.addSeparator()
        
        self.recent_files_menu = QMenu("&Recent Files", self)
        self.file_menu.addMenu(self.recent_files_menu)
        self.update_recent_files_menu()
        
        self.file_menu.addSeparator()
        
        self.minimize_action = QAction("&Minimize to Taskbar", self)
        self.minimize_action.triggered.connect(self.hide_to_tray)
        self.file_menu.addAction(self.minimize_action)
        
        self.exit_action = QAction("E&xit", self)
        self.exit_action.triggered.connect(self.close_application)
        self.file_menu.addAction(self.exit_action)
        
    def setup_media_menu(self):
        self.play_pause_action = QAction("&Play/Pause", self)
        self.play_pause_action.triggered.connect(self.toggle_play_pause)
        self.media_menu.addAction(self.play_pause_action)
        
        self.stop_action = QAction("&Stop", self)
        self.stop_action.triggered.connect(self.stop_playback)
        self.media_menu.addAction(self.stop_action)
        
        self.media_menu.addSeparator()
        
        self.mute_action = QAction("&Mute/Unmute", self)
        self.mute_action.triggered.connect(self.toggle_mute)
        self.media_menu.addAction(self.mute_action)
        
        self.media_menu.addSeparator()
        
        self.forward_action = QAction("&Forward", self)
        self.forward_action.triggered.connect(self.seek_forward)
        self.media_menu.addAction(self.forward_action)
        
        self.backward_action = QAction("&Backward", self)
        self.backward_action.triggered.connect(self.seek_backward)
        self.media_menu.addAction(self.backward_action)
        
        self.media_menu.addSeparator()
        
        self.previous_action = QAction("&Previous", self)
        self.previous_action.triggered.connect(self.previous_track)
        self.media_menu.addAction(self.previous_action)
        
        self.next_action = QAction("&Next", self)
        self.next_action.triggered.connect(self.next_track)
        self.media_menu.addAction(self.next_action)
        
        self.media_menu.addSeparator()
        
        self.repeat_action = QAction("Toggle &Repeat: Off", self)
        self.repeat_action.triggered.connect(self.toggle_repeat)
        self.media_menu.addAction(self.repeat_action)
        
    def setup_view_menu(self):
        self.show_explorer_action = QAction("Show &Explorer", self)
        self.show_explorer_action.setCheckable(True)
        self.show_explorer_action.setChecked(True)
        self.show_explorer_action.triggered.connect(self.toggle_explorer)
        self.view_menu.addAction(self.show_explorer_action)
        
        self.minimize_player_action = QAction("&Minimize Player", self)
        self.minimize_player_action.setCheckable(True)
        self.minimize_player_action.triggered.connect(self.toggle_player_minimize)
        self.view_menu.addAction(self.minimize_player_action)
        
        self.show_playlists_action = QAction("Show &Playlists", self)
        self.show_playlists_action.setCheckable(True)
        self.show_playlists_action.setChecked(True)
        self.show_playlists_action.triggered.connect(self.toggle_playlists)
        self.view_menu.addAction(self.show_playlists_action)
        
    def setup_tools_menu(self):
        self.batch_converter_action = QAction("&Batch Converter", self)
        self.batch_converter_action.triggered.connect(self.open_batch_converter)
        self.tools_menu.addAction(self.batch_converter_action)
        
        self.extractor_action = QAction("&Media Extractor", self)
        self.extractor_action.triggered.connect(self.open_extractor)
        self.tools_menu.addAction(self.extractor_action)
        
        self.tag_editor_action = QAction("&Tag Editor", self)
        self.tag_editor_action.triggered.connect(self.open_tag_editor)
        self.tools_menu.addAction(self.tag_editor_action)
        
        self.thumbnail_generator_action = QAction("&Thumbnail Generator", self)
        self.thumbnail_generator_action.triggered.connect(self.open_thumbnail_generator)
        self.tools_menu.addAction(self.thumbnail_generator_action)
        
    def setup_about_menu(self):
        self.preferences_action = QAction("&Manage Preferences", self)
        self.preferences_action.triggered.connect(self.open_preferences)
        self.about_menu.addAction(self.preferences_action)
        
        self.hotkeys_action = QAction("Manage &Hotkeys", self)
        self.hotkeys_action.triggered.connect(self.open_hotkeys)
        self.about_menu.addAction(self.hotkeys_action)
        
    def setup_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        self.toolbar.addAction(self.open_file_action)
        self.toolbar.addAction(self.open_url_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.play_pause_action)
        self.toolbar.addAction(self.stop_action)
        self.toolbar.addAction(self.mute_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.previous_action)
        self.toolbar.addAction(self.next_action)
        
    def setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        self.media_info_label = QLabel("")
        self.status_bar.addPermanentWidget(self.media_info_label)
        
    def setup_dock_widgets(self):
        self.explorer_dock = QDockWidget("Explorer", self)
        self.explorer_dock.setWidget(self.explorer_widget)
        self.explorer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)
        
        self.player_dock = QDockWidget("Player", self)
        self.player_dock.setWidget(self.player_widget)
        self.player_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.player_dock)
        
        self.playlists_dock = QDockWidget("Playlists", self)
        self.playlists_dock.setWidget(self.playlists_widget)
        self.playlists_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.playlists_dock)
        
    def setup_main_layout(self):
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        favorites_label = QLabel("Favorites")
        favorites_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(favorites_label)
        left_layout.addWidget(self.favorites_widget, 1)
        
        recents_label = QLabel("Recent Files")
        recents_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(recents_label)
        left_layout.addWidget(self.recents_widget, 1)
        
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.setSizes([300, 1100])
        
    def setup_system_tray(self):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay))
            
            tray_menu = QMenu()
            
            self.show_hide_action = QAction("Hide", self)
            self.show_hide_action.triggered.connect(self.toggle_window_visibility)
            tray_menu.addAction(self.show_hide_action)
            
            tray_menu.addSeparator()
            
            exit_action = QAction("Exit", self)
            exit_action.triggered.connect(self.close_application)
            tray_menu.addAction(exit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            self.tray_icon.show()
        else:
            self.tray_icon = None
            
    def connect_signals(self):
        self.favorites_widget.itemRequested.connect(self.play_file)
        self.recents_widget.itemRequested.connect(self.play_file)

        self.fileOpened.connect(self.player_widget.change_path)
        if hasattr(self.explorer_dock, 'visibilityChanged'):
            self.explorer_dock.visibilityChanged.connect(self.update_explorer_menu)
        if hasattr(self.player_dock, 'visibilityChanged'):
            self.player_dock.visibilityChanged.connect(self.update_player_menu)
        if hasattr(self.playlists_dock, 'visibilityChanged'):
            self.playlists_dock.visibilityChanged.connect(self.update_playlists_menu)
            
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Media File", "", 
            "Media Files (*.mp4 *.avi *.mkv *.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)"
        )
        if file_path:
            self.play_file(file_path)
            
    def open_url_dialog(self):
        url, ok = QInputDialog.getText(self, "Open URL", "Enter media URL:")
        if ok and url:
            self.play_url(url)
            
    def play_file(self, file_path: str):
        self.status_label.setText(f"Loading: {os.path.basename(file_path)}")
        self.media_info_label.setText(file_path)
        self.add_to_recents(file_path)
        self.update_recent_files_menu()
        self.fileOpened.emit(file_path)
        
    def play_url(self, url: str):
        self.status_label.setText(f"Loading URL: {url}")
        self.media_info_label.setText(url)
        self.urlOpened.emit(url)
        
    def add_to_favorites(self, file_path: str):
        self.favorites_widget.add_favorite(file_path)
        
    def add_to_recents(self, file_path: str):
        self.recents_widget.add_recent(file_path)
        
    def add_to_playlist(self, file_path: str):

        playlist_manager = self.playlists_widget.playlist_manager
        
        if not playlist_manager.list_playlists():
            reply = QMessageBox.question(
                self, "No Playlists",
                "No playlists exist. Would you like to create a new playlist?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.create_new_playlist_with_file(file_path)
            return
        
        dialog = PlaylistSelectionDialog(playlist_manager, self)
        dialog.playlist_selected.connect(
            lambda playlist_name: self.add_file_to_playlist(file_path, playlist_name)
        )
        dialog.exec()
        
    def create_playlist_from_folder(self, folder_path: str):

        if not os.path.isdir(folder_path):
            messageBox("Error", "Selected path is not a directory")
            return
            
        audio_formats = [ext.lower() for ext in formats.get("audio", [])]
        video_formats = [ext.lower() for ext in formats.get("video", [])]
        
        media_files = get_media_files_from_directory(folder_path, audio_formats, video_formats)
        
        if not media_files:
            messageBox("No Media Files", "No supported media files found in the selected folder")
            return
            
        folder_name = os.path.basename(folder_path)
        playlist_name = f"Playlist from {folder_name}"
        
        playlist = Playlist(title=playlist_name)
        for file_path in media_files:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            
        self.playlists_widget.playlist_manager.playlists[playlist_name] = playlist
        self.playlists_widget.add_playlist_to_list(playlist_name)
        self.playlists_widget.save_playlists_data()
        

        self.player_widget.load_playlist(playlist, start_index=0, auto_play=True)
        
        self.status_label.setText(f"Created and loaded playlist '{playlist_name}' with {len(media_files)} tracks")
        
    def add_file_to_playlist(self, file_path: str, playlist_name: str):

        playlist = self.playlists_widget.playlist_manager.get_playlist(playlist_name)
        if playlist:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            self.playlists_widget.save_playlists_data()
            
            filename = os.path.basename(file_path)
            self.status_label.setText(f"Added '{filename}' to playlist '{playlist_name}'")
        else:
            messageBox("Error", f"Playlist '{playlist_name}' not found")
            
    def create_new_playlist_with_file(self, file_path: str):

        dialog = PlaylistCreateDialog(self)
        dialog.tracks = [file_path]
        dialog.tracks_list.addItem(os.path.basename(file_path))
        
        dialog.playlist_created.connect(
            lambda name, playlist: self.handle_new_playlist_created(name, playlist)
        )
        dialog.exec()
        
    def handle_new_playlist_created(self, name: str, playlist: Playlist):

        self.playlists_widget.playlist_manager.playlists[name] = playlist
        self.playlists_widget.add_playlist_to_list(name)
        self.playlists_widget.save_playlists_data()
        self.status_label.setText(f"Created new playlist '{name}'")
        
    def update_recent_files_menu(self):
        self.recent_files_menu.clear()
        recent_files = self.recents_widget.get_recent_files_list()
        
        if not recent_files:
            no_recent_action = QAction("No recent files", self)
            no_recent_action.setEnabled(False)
            self.recent_files_menu.addAction(no_recent_action)
        else:
            for file_path in recent_files:
                action = QAction(os.path.basename(file_path), self)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked, path=file_path: self.play_file(path))
                self.recent_files_menu.addAction(action)
                
    def toggle_play_pause(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    state = self.player_widget.player.primary_instance.get_playback_state()
                    if state == "playing":
                        self.player_widget.player.primary_instance.pause()
                        self.status_label.setText("Paused")
                    else:
                        self.player_widget.player.primary_instance.play()
                        self.status_label.setText("Playing")
            except Exception as e:
                self.status_label.setText("No media loaded")
                
    def stop_playback(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    self.player_widget.player.primary_instance.stop()
                    self.status_label.setText("Stopped")
            except Exception as e:
                self.status_label.setText("No media loaded")
                
    def toggle_mute(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    self.status_label.setText("Mute toggled")
            except Exception as e:
                self.status_label.setText("No media loaded")
                
    def seek_forward(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    current_pos = self.player_widget.player.primary_instance.get_position()
                    self.player_widget.player.primary_instance.set_position(current_pos + 10)
            except Exception as e:
                pass
                
    def seek_backward(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    current_pos = self.player_widget.player.primary_instance.get_position()
                    self.player_widget.player.primary_instance.set_position(max(0, current_pos - 10))
            except Exception as e:
                pass
                
    def previous_track(self):
        self.status_label.setText("Previous track")
        
    def next_track(self):
        self.status_label.setText("Next track")

    def volume_down(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            instance = self.player_widget.player.primary_instance
            if instance and hasattr(instance, "get_volume") and hasattr(instance, "set_volume"):
                current_volume = instance.get_volume()
                instance.set_volume(max(0, current_volume - 5))

    def volume_up(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            instance = self.player_widget.player.primary_instance
            if instance and hasattr(instance, "get_volume") and hasattr(instance, "set_volume"):
                current_volume = instance.get_volume()
                instance.set_volume(min(100, current_volume + 5))
    
    def open_batch_converter(self):
        self.open_tool_dialog("batch_converter", BatchConverterUI(), "Batch Converter")
        
    def open_extractor(self):
        self.open_tool_dialog("extractor", ExtractorUI(), "Media Extractor")
        
    def open_tag_editor(self):
        self.open_tool_dialog("tag_editor", TagEditorUI(), "Tag Editor")
        
    def open_thumbnail_generator(self):
        self.open_tool_dialog("thumbnail_generator", ThumbnailGeneratorUI(), "Thumbnail Generator")
        
    def open_tool_dialog(self, tool_name, tool_widget, title):
        if tool_name in self.tool_dialogs and self.tool_dialogs[tool_name].isVisible():

            self.tool_dialogs[tool_name].raise_()
            self.tool_dialogs[tool_name].activateWindow()
        else:

            dialog = ToolDialog(tool_widget, title, self)
            self.tool_dialogs[tool_name] = dialog
            dialog.show()
            self.status_label.setText(f"Opened {title}")
        
    def toggle_repeat(self):
        self.is_repeat_enabled = not self.is_repeat_enabled
        prefs.prefs['repeat'] = self.is_repeat_enabled
        prefs.save()
        
        repeat_text = "Toggle Repeat: On" if self.is_repeat_enabled else "Toggle Repeat: Off"
        self.repeat_action.setText(repeat_text)
        self.status_label.setText(f"Repeat: {'On' if self.is_repeat_enabled else 'Off'}")
        
    def toggle_explorer(self, checked):
        self.explorer_dock.setVisible(checked)
        
    def toggle_player_minimize(self, checked):
        if checked:
            self.player_dock.hide()
        else:
            self.player_dock.show()
            
    def toggle_playlists(self, checked):
        self.playlists_dock.setVisible(checked)
        
    def update_explorer_menu(self, visible):
        self.show_explorer_action.setChecked(visible)
        
    def update_player_menu(self, visible):
        self.minimize_player_action.setChecked(not visible)
        
    def update_playlists_menu(self, visible):
        self.show_playlists_action.setChecked(visible)
        
    def apply_audio_device(self, device_name):

        try:

            if hasattr(self.player_widget, 'player') and self.player_widget.player:

                device_count = self.player_widget.player.get_devices()
                for i in range(device_count):
                    device_info = self.player_widget.player.get_device(i)
                    if device_info and device_info.name == device_name:
                        self.player_widget.player.set_device(i)
                        break
        except Exception as e:
            print(f"Error applying audio device to player: {e}")
        
        try:

            if hasattr(self.explorer_widget, '_player') and self.explorer_widget._player:

                device_count = self.explorer_widget._player.get_devices()
                for i in range(device_count):
                    device_info = self.explorer_widget._player.get_device(i)
                    if device_info and device_info.name == device_name:
                        self.explorer_widget._player.set_device(i)
                        break
        except Exception as e:
            print(f"Error applying audio device to explorer: {e}")
    
    def open_preferences(self):

        audio_devices = ["auto"]
        try:
            if hasattr(self.player_widget, 'player') and self.player_widget.player:

                device_count = self.player_widget.player.get_devices()
                for i in range(device_count):
                    device_info = self.player_widget.player.get_device(i)
                    if device_info and device_info.name:
                        audio_devices.append(device_info.name)
        except Exception:
            pass
        
        dialog = PreferencesDialog(self, audio_devices, self.apply_audio_device)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.status_label.setText("Preferences saved")
            
    def open_hotkeys(self):
        dialog = HotkeysDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.status_label.setText("Hotkeys updated")
            
    def hide_to_tray(self):
        if self.tray_icon:
            self.hide()
            self.show_hide_action.setText("Show")
            if hasattr(self.tray_icon, 'showMessage'):
                self.tray_icon.showMessage(
                    "PlayForm Media Player",
                    "Application was minimized to tray",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            self.showMinimized()
            
    def toggle_window_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
            self.show_hide_action.setText("Show")
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.show_hide_action.setText("Hide")
            
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_visibility()
            
    def close_application(self):
        self.save_window_state()

        for dialog in self.tool_dialogs.values():
            if dialog.isVisible():
                dialog.close()
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()
        
    def save_window_state(self):
        prefs.prefs['window_geometry'] = self.saveGeometry().data().hex()
        prefs.prefs['window_state'] = self.saveState().data().hex()
        prefs.save()
        
    def restore_window_state(self):
        if 'window_geometry' in prefs.prefs and prefs.prefs['window_geometry']:
            try:
                geometry = bytes.fromhex(prefs.prefs['window_geometry'])
                self.restoreGeometry(geometry)
            except:
                pass
                
        if 'window_state' in prefs.prefs and prefs.prefs['window_state']:
            try:
                state = bytes.fromhex(prefs.prefs['window_state'])
                self.restoreState(state)
            except:
                pass
                
    def closeEvent(self, event):
        if self.tray_icon and self.tray_icon.isVisible():
            event.ignore()
            self.hide_to_tray()
        else:
            self.close_application()
            event.accept()



    def cli_load_file(self, ipc_msg_data:dict[str, str]):
        self.play_file(ipc_msg_data["msg_data"])
```

#### File: `gui\prefs_dialog.py`

```python
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QWidget, QLabel, QComboBox, QSpinBox, QPushButton,
                               QFormLayout, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_config import prefs
from app_constance.misc import screenshot_formats, app_languages

class PreferencesDialog(QDialog):
    preferences_saved = Signal(dict)
    
    def __init__(self, parent=None, audio_devices=None, audio_device_callback=None):
        super().__init__(parent)
        self.audio_devices = audio_devices or ["auto"]
        self.audio_device_callback = audio_device_callback
        self.setWindowTitle("Preferences")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumSize(400, 300)
        self.setup_ui()
        self.load_preferences()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        self.setup_general_tab()
        self.setup_media_tab()
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def setup_general_tab(self):
        general_widget = QWidget()
        layout = QFormLayout(general_widget)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(app_languages)
        layout.addRow("Language:", self.language_combo)
        
        self.screenshot_format_combo = QComboBox()
        self.screenshot_format_combo.addItems(screenshot_formats)
        layout.addRow("Screenshot Format:", self.screenshot_format_combo)
        
        self.tab_widget.addTab(general_widget, "General")
        
    def setup_media_tab(self):
        media_widget = QWidget()
        layout = QFormLayout(media_widget)
        
        self.volume_offset_spin = QSpinBox()
        self.volume_offset_spin.setRange(1, 20)
        layout.addRow("Volume Offset:", self.volume_offset_spin)
        
        self.seek_offset_spin = QSpinBox()
        self.seek_offset_spin.setRange(1, 60)
        layout.addRow("Seek Offset:", self.seek_offset_spin)
        
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.addItems(self.audio_devices)
        layout.addRow("Audio Device:", self.audio_device_combo)
        
        self.tab_widget.addTab(media_widget, "Media")
        
    def load_preferences(self):
        current_prefs = prefs.prefs
        
        if current_prefs["language"].upper() in app_languages:
            self.language_combo.setCurrentText(current_prefs["language"].upper())
        
        if current_prefs["image_format"] in screenshot_formats:
            self.screenshot_format_combo.setCurrentText(current_prefs["image_format"])
            
        self.volume_offset_spin.setValue(current_prefs["offset"]["volume"])
        self.seek_offset_spin.setValue(current_prefs["offset"]["seek"])
        
        if current_prefs["device"] in self.audio_devices:
            self.audio_device_combo.setCurrentText(current_prefs["device"])
            
    def save_preferences(self):
        prefs.prefs["language"] = self.language_combo.currentText().lower()
        prefs.prefs["image_format"] = self.screenshot_format_combo.currentText()
        prefs.prefs["offset"]["volume"] = self.volume_offset_spin.value()
        prefs.prefs["offset"]["seek"] = self.seek_offset_spin.value()
        prefs.prefs["device"] = self.audio_device_combo.currentText()
        
        prefs.save()
        
        # Call audio device callback if provided
        if self.audio_device_callback:
            self.audio_device_callback(prefs.prefs["device"])
        
        self.preferences_saved.emit(prefs.prefs.copy())
        
    def accept(self):
        self.save_preferences()
        super().accept()
```

#### File: `gui\recents.py`

```python
from PySide6.QtWidgets import QListWidget, QMenu, QMessageBox
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from app_db import UserFiles
from utilities.util_gui import contextMenu, messageBox


class RecentsWidget(QListWidget):
    itemRequested = Signal(str)
    
    def __init__(self, user_db: UserFiles, parent=None):
        super().__init__(parent)
        self.user_db = user_db
        self.max_recent_files = 50
        self.setAccessibleName("Recent files list")
        self.setAccessibleDescription("List of recently opened media files")
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        
        contextMenu(self, self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_activated)
        
        self.load_recents()
        
    def load_recents(self):
        self.clear()
        try:
            recents = self.user_db.get_recents(self.max_recent_files)
            for recent_path in recents:
                self.addItem(recent_path)
        except Exception as e:
            print(f"Error loading recents: {e}")
    
    def add_recent(self, file_path: str):
        try:
            self.user_db.add_recent(file_path)
            for i in range(self.count()):
                if self.item(i).text() == file_path:
                    self.takeItem(i)
                    break
            
            self.insertItem(0, file_path)
            
            while self.count() > self.max_recent_files:
                self.takeItem(self.count() - 1)
                
        except Exception as e:
            messageBox("Error", f"Failed to add recent file: {e}")
    
    def clear_recents(self):
        reply = QMessageBox.question(self, "Clear Recent Files", 
                                   "Are you sure you want to clear all recent files?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.user_db.clear_recents()
                self.clear()
            except Exception as e:
                messageBox("Error", f"Failed to clear recent files: {e}")
    
    def show_context_menu(self, position):
        menu = QMenu(self)
        
        clear_action = QAction("Clear All Recent Files", self)
        clear_action.triggered.connect(self.clear_recents)
        menu.addAction(clear_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def on_item_activated(self, item):
        if item:
            self.itemRequested.emit(item.text())
    
    def get_recent_files_list(self):
        return [self.item(i).text() for i in range(min(10, self.count()))]
```

<a name="directory-gui_controls"></a>
### Directory: `gui_controls`


#### File: `gui_controls\__init__.py`

```python

```

#### File: `gui_controls\common_controls.py`

```python
from PySide6.QtWidgets import QLabel, QToolTip, QPushButton, QToolButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer, QRect
from PySide6.QtCore import Qt as qt


class TextLabel(QLabel):


    def __init__(self,text,parent):
        super().__init__(parent)
        self.setText(text)
        self.setFocusPolicy(qt.FocusPolicy.TabFocus)

class ConfirmButton(QToolButton):


    def __init__(self,label,parent=None):
        super().__init__(parent)
        self.setText(label)
        self.setIcon(QIcon.fromTheme("dialog-ok"))

class CancelButton(QToolButton):


    def __init__(self,label,parent=None):
        super().__init__(parent)
        self.setText(label)
        self.setIcon(QIcon.fromTheme("dialog-cancel"))

class ToolTip(QToolTip):


    def __init__(self,text,pos,duration,widget,parent=None):
        super().__init__()
        self.parent = parent
        self.text = text
        self.duration = duration
        self.position = pos
        self.show_text(self.position,self.text,self.duration)

    def show_text(self,position,txt,dur):
        self.showText(position,txt,self.parent,QRect(15,30,40,60),dur)
        QTimer.singleShot(self.duration,self.deleteInstance)

    def deleteInstance(self):
        del self

```

#### File: `gui_controls\dialogs.py`

```python
import os
from PySide6.QtWidgets import (QDialog, QFileDialog, QVBoxLayout, QHBoxLayout,
QLabel, QPushButton, QPlainTextEdit, QListWidget, QToolButton)
from PySide6.QtCore import Qt as qt
from common_controls import CancelButton, ConfirmButton


class InfoDialog(QDialog):


    def __init__(self,title,text,parent):
       super().__init__(parent)
       self.text = text
       self.setWindowModality(qt.WindowModality.WindowModal)
       self.setWindowTitle(title)
       self.ui()
       self.Layout()

    def ui(self):
       self.text_field = QPlainTextEdit(self)
       self.close_button = QPushButton("Close",self)
       self.text_field.setReadOnly(True)
       self.text_field.setTabChangesFocus(True)
       self.text_field.setPlainText(self.text)
       self.close_button.clicked.connect(self.close)
       self.close_button.setShortcut("Alt+C")

    def Layout(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.addWidget(self.text_field)
        self.mainLayout.addWidget(self.close_button)

class FileDialog(QDialog):


    def __init__(self,title, flags, parent=None):
        self.title = title
        self.files = []
        self.flags = flags
        self.fd = QFileDialog()

        self.fd.setFileMode(QFileDialog.fileMode.ExistingFiles)
        self.fd.setNameFilter(self.flags)

        super().__init__(parent)
        self.setWindowTitle(self.title)
        self.setWindowModality(qt.WindowModality.WindowModal)
        self.ui()
        self.Layout()
        self.setLayout(self.mainLayout)


    def ui(self):
        self.files_list = QListWidget(self)
        self.browse_btn = QToolButton(self)
        self.browse_btn.setText("browse")
        self.confirm_btn = ConfirmButton("Confirm",self)
        self.cancel_btn = CancelButton("Cancel",)
        self.browse_btn.clicked.connect(self.onbrowse)
        self.confirm_btn.clicked.connect(self.onConfirm)
        self.cancel_btn.clicked.connect(self.close)

    def Layout(self):
        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(self.files_list)
        self.mainLayout.addWidget(self.browse_btn)
        bottom_btn_layout = QHBoxLayout()
        bottom_btn_layout.addWidget(self.confirm_btn)
        bottom_btn_layout.addWidget(self.cancel_btn)
        self.mainLayout.addLayout(bottom_btn_layout)


    def onbrowse(self):
        if self.fd.exec() == QDialog.DialogCode.Accepted:
            selected = self.fd.selectedFiles()
            if len(selected) >0:
                for file in selected:
                    self.files.append(file)
                self.updateList()
            self.fd.selectedFiles().clear()

    def updateList(self):
        self.files_list.clear()
        for file in self.files:
            self.files_list.addItem(os.path.basename(file))

    def onConfirm(self):
        self.close()
```

#### File: `gui_controls\key_event_filter.py`

```python
from PySide6.QtCore import QObject, Qt, QEvent
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QApplication, QPushButton, QListWidget, QTreeWidget, QLineEdit, QTextEdit, QPlainTextEdit, 
                               QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QRadioButton, QSlider, QScrollBar, 
                               QListView, QTreeView, QTableWidget, QTableView, QAbstractItemView, QAbstractSpinBox,
                               QDial, QProgressBar, QTabWidget, QTabBar, QSplitter, QGroupBox, QFrame)
from typing import Dict, Callable, Union, List, Optional, Set
import logging

class ShortcutScope:
    GLOBAL = "global"
    CONTEXT_AWARE = "context_aware" 
    WIDGET_LOCAL = "widget_local"

class ShortcutManager(QObject):


    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.shortcuts: Dict[str, Dict] = {}
        self.widget_local_shortcuts: Dict[QObject, Dict[str, Callable]] = {}
        
        self.enabled = True
        self.debug_mode = False
        self.logger = logging.getLogger(__name__)
        
        self.input_widgets = {
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox
        }
        
        self.navigation_widgets = {
            QListWidget, QTreeWidget, QListView, QTreeView, 
            QTableWidget, QTableView, QAbstractItemView
        }
        
        self.clickable_widgets = {
            QPushButton, QCheckBox, QRadioButton
        }
        
        self.value_widgets = {
            QSpinBox, QDoubleSpinBox, QAbstractSpinBox,
            QSlider, QScrollBar, QDial
        }
        
        self.tab_widgets = {
            QTabWidget, QTabBar
        }
        
        self.container_widgets = {
            QSplitter
        }

    def add_global_shortcut(self, key_combination: str, callback: Callable, description: str = ""):
        normalized_combo = self._normalize_key_combination(key_combination)
        self.shortcuts[normalized_combo] = {
            'callback': callback,
            'scope': ShortcutScope.GLOBAL,
            'description': description
        }

    def add_context_shortcut(self, key_combination: str, callback: Callable, description: str = ""):
        normalized_combo = self._normalize_key_combination(key_combination)
        self.shortcuts[normalized_combo] = {
            'callback': callback,
            'scope': ShortcutScope.CONTEXT_AWARE,
            'description': description
        }

    def add_widget_shortcut(self, widget: QObject, key_combination: str, callback: Callable):
        if widget not in self.widget_local_shortcuts:
            self.widget_local_shortcuts[widget] = {}
        
        normalized_combo = self._normalize_key_combination(key_combination)
        self.widget_local_shortcuts[widget][normalized_combo] = callback

    def remove_shortcut(self, key_combination: str) -> bool:
        normalized_combo = self._normalize_key_combination(key_combination)
        if normalized_combo in self.shortcuts:
            del self.shortcuts[normalized_combo]
            return True
        return False

    def remove_widget_shortcut(self, widget: QObject, key_combination: str = None):
        if widget in self.widget_local_shortcuts:
            if key_combination:
                normalized_combo = self._normalize_key_combination(key_combination)
                self.widget_local_shortcuts[widget].pop(normalized_combo, None)
            else:
                del self.widget_local_shortcuts[widget]

    def clear_shortcuts(self):
        self.shortcuts.clear()
        self.widget_local_shortcuts.clear()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def set_debug_mode(self, debug: bool):
        self.debug_mode = debug
        if debug:
            logging.basicConfig(level=logging.INFO)

    def install_on_application(self):
        QApplication.instance().installEventFilter(self)

    def uninstall_from_application(self):
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event):
        if not self.enabled or event.type() != QEvent.KeyPress:
            return False

        return self._handle_key_press(event)

    def _handle_key_press(self, event) -> bool:
        key = event.key()
        modifiers = event.modifiers()

        if self._is_modifier_key(key):
            return False

        key_combo = self._create_key_combination(modifiers, key)
        focused_widget = QApplication.focusWidget()

        if self.debug_mode:
            widget_name = focused_widget.__class__.__name__ if focused_widget else "None"
            self.logger.info(f"Key: {key_combo}, Focused: {widget_name}")

        if focused_widget and focused_widget in self.widget_local_shortcuts:
            if key_combo in self.widget_local_shortcuts[focused_widget]:
                try:
                    self.widget_local_shortcuts[focused_widget][key_combo]()
                    return True
                except Exception as e:
                    if self.debug_mode:
                        self.logger.error(f"Error in widget shortcut: {e}")

        if key_combo in self.shortcuts:
            shortcut_info = self.shortcuts[key_combo]
            scope = shortcut_info['scope']
            
            if scope == ShortcutScope.GLOBAL:
                try:
                    shortcut_info['callback']()
                    return True
                except Exception as e:
                    if self.debug_mode:
                        self.logger.error(f"Error in global shortcut: {e}")
                        
            elif scope == ShortcutScope.CONTEXT_AWARE:
                if self._should_allow_context_shortcut(key_combo, focused_widget):
                    try:
                        shortcut_info['callback']()
                        return True
                    except Exception as e:
                        if self.debug_mode:
                            self.logger.error(f"Error in context shortcut: {e}")

        return False

    def _should_allow_context_shortcut(self, key_combo: str, focused_widget) -> bool:
        if not focused_widget:
            return True

        key_without_modifiers = key_combo.split('+')[-1]
        widget_type = type(focused_widget)

        if key_without_modifiers == "Space":
            if widget_type in self.clickable_widgets:
                return False
            if widget_type in self.tab_widgets:
                return False

        if key_without_modifiers == "Return" or key_without_modifiers == "Enter":
            if widget_type in self.clickable_widgets:
                return False

        if key_without_modifiers in ["Up", "Down"]:
            if widget_type in self.navigation_widgets:
                return False
            if widget_type in self.value_widgets:
                return False
            if widget_type in self.input_widgets and isinstance(focused_widget, QComboBox):
                return False
            if widget_type in self.tab_widgets:
                return False

        if key_without_modifiers in ["Left", "Right"]:
            if widget_type in self.navigation_widgets:
                return False
            if widget_type in self.value_widgets:
                return False
            if widget_type in self.tab_widgets:
                return False
            if widget_type in self.container_widgets:
                return False

        if key_without_modifiers in ["Home", "End"]:
            if widget_type in self.navigation_widgets:
                return False
            if widget_type in self.input_widgets:
                return False
            if widget_type in self.value_widgets:
                return False

        if key_without_modifiers in ["PageUp", "PageDown"]:
            if widget_type in self.navigation_widgets:
                return False
            if widget_type in self.value_widgets:
                return False

        if key_without_modifiers == "Tab":
            return False

        if key_without_modifiers == "Escape":
            if widget_type in self.input_widgets and isinstance(focused_widget, QComboBox):
                return False

        if key_without_modifiers in ["Plus", "Minus", "+", "-"]:
            if widget_type in self.value_widgets:
                return False

        if widget_type in self.input_widgets:
            if key_without_modifiers in ["Space", "Home", "End", "Left", "Right", "Backspace", "Delete"]:
                if not isinstance(focused_widget, QComboBox):
                    return False

        return True

    def _is_modifier_key(self, key) -> bool:
        modifier_keys = {
            Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta,
            Qt.Key_AltGr, Qt.Key_CapsLock, Qt.Key_NumLock, Qt.Key_ScrollLock
        }
        return key in modifier_keys

    def _create_key_combination(self, modifiers, key) -> str:
        parts = []
        
        if modifiers & Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.MetaModifier:
            parts.append("Win")
        
        key_name = self._get_key_name(key)
        if key_name:
            parts.append(key_name)
        
        return "+".join(parts)

    def _normalize_key_combination(self, key_combination: str) -> str:
        if not key_combination:
            return ""
        
        parts = [part.strip() for part in key_combination.split('+')]
        normalized_parts = []
        
        modifier_order = ["Ctrl", "Alt", "Shift", "Win"]
        found_modifiers = []
        main_key = None
        
        for part in parts:
            part_lower = part.lower()
            
            if part_lower in ["ctrl", "control"]:
                found_modifiers.append("Ctrl")
            elif part_lower == "alt":
                found_modifiers.append("Alt")
            elif part_lower == "shift":
                found_modifiers.append("Shift")
            elif part_lower in ["win", "meta", "cmd", "super"]:
                found_modifiers.append("Win")
            else:
                if part in ["[", "]"]:
                    main_key = part
                elif part.lower() == "backspace":
                    main_key = "Backspace"
                elif len(part) == 1:
                    main_key = part.upper()
                else:
                    main_key = part.title()
        
        for modifier in modifier_order:
            if modifier in found_modifiers:
                normalized_parts.append(modifier)
        
        if main_key:
            normalized_parts.append(main_key)
        
        return "+".join(normalized_parts)

    def _get_key_name(self, key) -> str:
        special_keys = {
            Qt.Key_Escape: "Escape",
            Qt.Key_Tab: "Tab",
            Qt.Key_Backtab: "Backtab",
            Qt.Key_Backspace: "Backspace",
            Qt.Key_Return: "Return",
            Qt.Key_Enter: "Enter",
            Qt.Key_Insert: "Insert",
            Qt.Key_Delete: "Delete",
            Qt.Key_Pause: "Pause",
            Qt.Key_Print: "Print",
            Qt.Key_SysReq: "SysReq",
            Qt.Key_Clear: "Clear",
            Qt.Key_Home: "Home",
            Qt.Key_End: "End",
            Qt.Key_Left: "Left",
            Qt.Key_Up: "Up",
            Qt.Key_Right: "Right",
            Qt.Key_Down: "Down",
            Qt.Key_PageUp: "PageUp",
            Qt.Key_PageDown: "PageDown",
            Qt.Key_Space: "Space",
            Qt.Key_BracketLeft: "[",
            Qt.Key_BracketRight: "]",
        }
        
        if key in special_keys:
            return special_keys[key]
        
        if Qt.Key_F1 <= key <= Qt.Key_F35:
            return f"F{key - Qt.Key_F1 + 1}"
        
        if 32 <= key <= 126:
            return chr(key).upper()
        
        if Qt.Key_0 <= key <= Qt.Key_9:
            return chr(key)
        
        try:
            sequence = QKeySequence(key)
            return sequence.toString()
        except:
            return f"Key_{key}"

```

#### File: `gui_controls\list_control.py`

```python
from PySide6.QtWidgets import (QLabel, QListWidget, QListWidgetItem, QWidget,
QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QSpacerItem
, QListView, QAbstractItemView)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class HeaderWidget(QWidget):


    def __init__(self, parent=None):

        super().__init__(parent)
        self.headers = []
        self.labels = {}
        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(10)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self.setStyleSheet("""
            background-color: #3498db;
            color: #fff;
            padding: 10px;
            font-weight: bold;
            border-bottom: 2px solid #2980b9;
        """)
        self.headerStyle = """
            color: #fff;
            font-weight: bold;
        """


class ListHeader(QListWidgetItem):


    def __init__(self, parent=None):
        self.parent = parent
        super().__init__()
        self.Widget = HeaderWidget()
        if self.parent:
            self.parent.addItem(self)
            self.parent.setItemWidget(self, self.Widget)
        self.setSizeHint(self.Widget.sizeHint())
        self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self.Widget.setMinimumHeight(50)
        self.Widget.setMinimumWidth(200)

    def insertHeader(self, index, name):
        self.Widget.headers.insert(int(index), name)
        label = QLabel(name)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setFont(QFont("Arial", 12))
        label.setStyleSheet(self.Widget.headerStyle)
        self.Widget._layout.addWidget(label)
        self.Widget.labels[f"{name}_label"] = label

    def removeHeader(self, index):
        header = self.Widget.headers.pop(int(index))
        label = self.Widget.labels.pop(f"{header}_label")
        self.Widget._layout.removeWidget(label)
        label.deleteLater()


class ItemWidget(QWidget):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.columns = []
        self.labels = {}
        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(10)
        self._layout.setContentsMargins(5, 5, 5, 5)

        self.setStyleSheet("""
            background-color: #ecf0f1;
            padding: 10px;
            border-left: 1px solid lightgray;
            border-right: 1px solid lightgray;
            border-top: 1px solid lightgray;
            border-bottom: 1px solid #bdc3c7;
        """)
        self.columnStyle = """
            color: #333;
            font-weight: bold;
        """


class ListItem(QListWidgetItem):


    def __init__(self, parent=None):

        self.parent = parent
        super().__init__()
        self.Widget = ItemWidget()
        self.setSizeHint(self.Widget.sizeHint())
        if self.parent:
            self.parent.addItem(self)
            self.parent.setItemWidget(self, self.Widget)
        self.Widget.setMinimumHeight(50)
        self.Widget.setMinimumWidth(200)

    def insertColumn(self, index, name):
        self.Widget.columns.insert(int(index), name)
        label = QLabel(name)
        label.setStyleSheet(self.Widget.columnStyle)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setFont(QFont("Arial", 12))
        self.Widget._layout.addWidget(label)
        self.Widget._layout.update()
        self.Widget.labels[f"{name}_label"] = label

    def editColumn(self,index,text):
        column = self.Widget.columns[index]
        label = self.Widget.labels[f"{column}_label"]
        self.Widget.labels[f"{text}_label"] = label
        del self.Widget.labels[f"{column}_label"]
        self.Widget.columns[index] = text

        label.setText(text)
        print(label.text())

    def removeColumn(self, index):
        column = self.Widget.columns.pop(index)
        label = self.Widget.labels.pop(f"{column}_label")
        self.Widget._layout.removeWidget(label)
        self.Widget._layout.update()
        label.deleteLater()


class Listctrl(QListWidget):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = ListHeader(self)
        self.setViewMode(QListView.ViewMode.ListMode)

    def viewOptions(self):
        return super().viewOptions() # type:ignore

    def column(self, index, name):
        self.headers.insertHeader(index, name)
        self.updateDiscription()

    def removeColumn(self, index):
        count = self.count() - 1
        self.headers.removeHeader(index)
        for n in range(1, count + 1):
            item = self.item(n)
            if item and isinstance(item, ListItem):
                item.removeColumn(index)
        self.updateDiscription()

    def editColumn(self,row,column,text):
        item = self.item(row)
        if item and isinstance(item, ListItem):
            item.editColumn(column,text)
            text_desc = ""
            for col in self.headers.Widget.headers:
                text_desc+=f"{item.Widget.columns[self.headers.Widget.headers.index(col)]}, "
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, text_desc[0:len(text_desc) - 2])

    def appendRow(self, columns):
        text = ""
        item = ListItem(self)
        for column in columns:
            item.insertColumn(column, columns[column])
            text += f"{self.headers.Widget.headers[int(column)]}: {columns[column]},"
        item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, text[0:len(text) - 1])
        self.updateDiscription()
        return item

    def removeRow(self, index):
        item = self.item(index)
        widget = self.itemWidget(item)
        self.removeItemWidget(item)
        self.takeItem(index)
        del item
        self.updateDiscription()

    def clearAll(self):
        column_count = len(self.headers.Widget.headers)
        row_count = self.count()
        if column_count>0:
            for n in range(0, column_count):
                    self.headers.removeHeader(column_count-1-n)
        if self.getRowCount()>0:
            for n in range(1, row_count+1):
                index = row_count-n
                if index == 0: break
                self.removeRow(index)
        self.updateDiscription()

    def indexFromColumn(self, name):
        current_item = self.currentItem()
        if current_item and isinstance(current_item, ListItem):
            return current_item.Widget.columns.index(name)
        return -1

    def columnFromIndex(self, index):
        current_item = self.currentItem()
        if current_item and isinstance(current_item, ListItem):
            return current_item.Widget.columns[index]
        return ""

    def getCurrentRowIndex(self):
        return self.row(self.currentItem())

    def getColumnCount(self):
        return len(self.headers.Widget.headers)

    def getRowCount(self):
        return self.count() - 1

    def updateDiscription(self):
        self.setAccessibleDescription(f"list view with {self.getColumnCount()} columns and {self.getRowCount()} rows")
```

#### File: `gui_controls\list_tab.py`

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                               QListWidgetItem, QFrame, QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

class TabInfo(QListWidgetItem):


    def __init__(self, name, widget, parent=None):
        super().__init__(parent)
        self.name = name
        self.widget = widget
        self._activated = False
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(Qt.Unchecked)
        self.setTabLabel(self.name)
        
    def setTabLabel(self, text):
        self.name = text
        self.setText(self.name)
        
    def tabLabel(self):
        return self.name
        
    def setActivated(self, state):
        if isinstance(state, bool):
            if state:
                self.setCheckState(Qt.Checked)
            else:
                self.setCheckState(Qt.Unchecked)
            self._activated = state
        else:
            raise TypeError("state must be bool")
            
    def is_activated(self):
        return self._activated

class ListTabCtrl(QWidget):
    tabChanged = Signal(object, object)
    tabActivated = Signal()

    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels = []
        self.current_widget = None
        self.ui()
        self.layout_widgets()
        self.setLayout(self.main_layout)
        
    def ui(self):
        self.tabLabels = QListWidget(self)
        self.tabLabels.setViewMode(QListWidget.ListMode)
        self.tabLabels.setFlow(QListWidget.LeftToRight)
        self.tabLabels.setMovement(QListWidget.Static)
        
        self.tabLabels.setWrapping(False)
        self.tabLabels.setResizeMode(QListWidget.Adjust)
        
        self.tabLabels.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabLabels.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tabLabels.setFixedHeight(60)
        
        self.tabLabels.setSpacing(2)
        self.tabLabels.setGridSize(self.tabLabels.sizeHint())
        
        self.tabLabels.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.tabLabels.itemChanged.connect(self.onState)
        self.tabLabels.currentItemChanged.connect(self.onTabChange)
        
        self.line = QFrame(self)
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setFixedHeight(2)
        
        self.tabView = QWidget(self)
        self.tabView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def layout_widgets(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        
        self.main_layout.addWidget(self.tabLabels)
        self.main_layout.addWidget(self.line)
        self.main_layout.addWidget(self.tabView, 1)
        
        self.tabLayout = QVBoxLayout(self.tabView)
        self.tabLayout.setContentsMargins(0, 0, 0, 0)
        
    def onState(self, item):
        if item is not None:
            if item.checkState() == Qt.CheckState.Checked:
                item.setActivated(True)
                if hasattr(item, 'widget') and item.widget:
                    self.showTabWidget(item.widget)
            elif item.checkState() == Qt.CheckState.Unchecked:
                item.setActivated(False)
                if hasattr(item, 'widget') and item.widget:
                    self.hideTabWidget(item.widget)
            self.tabActivated.emit()
            
    def showTabWidget(self, widget):
        self.clearTabLayout()
        self.tabLayout.addWidget(widget)
        widget.show()
        self.current_widget = widget
        
    def hideTabWidget(self, widget):
        if widget == self.current_widget:
            self.clearTabLayout()
            self.current_widget = None
            
    def clearTabLayout(self):
        while self.tabLayout.count():
            child = self.tabLayout.takeAt(0)
            if child.widget():
                child.widget().hide()
                
    def onTabChange(self, current, previous):
        if current is not None and current.checkState() == Qt.Checked:
            self.showTabWidget(current.widget)
        elif current is None or current.checkState() == Qt.Unchecked:
            if self.current_widget:
                self.hideTabWidget(self.current_widget)
                
        self.tabChanged.emit(current, previous)
        
    def currentTab(self):
        return self.tabLabels.currentItem()
        
    def tabCount(self):
        return self.tabLabels.count()
        
    def addTab(self, label, widget):
        tab = TabInfo(label, widget, self.tabLabels)
        widget.setParent(self.tabView)
        widget.hide()
        self.labels.append(label)
        self.tabLabels.addItem(tab)
        
        item_size = self.tabLabels.sizeHintForIndex(self.tabLabels.indexFromItem(tab))
        tab.setSizeHint(item_size)
        
    def removeTab(self, index):
        if 0 <= index < self.tabCount():
            tab = self.tabLabels.item(index)
            if tab:
                if tab.name in self.labels:
                    self.labels.remove(tab.name)
                
                if hasattr(tab, 'widget') and tab.widget:
                    if tab.widget == self.current_widget:
                        self.current_widget = None
                    tab.widget.deleteLater()
                
                self.tabLabels.takeItem(index)
                
    def deleteTabs(self):
        if self.tabCount() > 0:
            for i in range(self.tabCount() - 1, -1, -1):
                self.removeTab(i)
            self.labels.clear()
            self.current_widget = None
            
    def indexOfTab(self, name):
        try:
            return self.labels.index(name)
        except ValueError:
            return -1
            
    def getTab(self, index):
        if 0 <= index < self.tabCount():
            return self.tabLabels.item(index)
        return None
        
    def sizeHint(self):
        from PySide6.QtCore import QSize
        return self.tabLabels.sizeHint() + self.tabView.sizeHint()
        
    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(300, 150)
```

#### File: `gui_controls\toggle_button.py`

```python
from PySide6.QtWidgets import QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve, QRect, Qt, QParallelAnimationGroup
from PySide6.QtGui import QFont

class ToggleButton(QPushButton):
    actuated = Signal(bool)
    

    def __init__(self, text=None, parent=None):
        super().__init__(parent)
        
        self.activated = False
        
        self.setupAnimations()
        
        self.setupStyle()
        
        self.clicked.connect(self.onActuate)
        
        self.setCursor(Qt.PointingHandCursor)
        
        if text and text.strip():
            self.setText(text)
        
        self.updateAccessibility()
        self.updateStyle()
        
        self.setMinimumSize(100, 35)
        
    def setupAnimations(self):
        self.animationGroup = QParallelAnimationGroup(self)
        
        self.opacityEffect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacityEffect)
        
        self.opacityAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.opacityAnimation.setDuration(200)
        self.opacityAnimation.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.sizeAnimation = QPropertyAnimation(self, b"minimumSize")
        self.sizeAnimation.setDuration(250)
        self.sizeAnimation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.animationGroup.addAnimation(self.opacityAnimation)
        self.animationGroup.addAnimation(self.sizeAnimation)
        
    def setupStyle(self):
        self.base_style = """
            QPushButton {
                background-color: transparent;
                border: 2px solid rgba(46, 204, 113, 0.6);
                border-radius: 8px;
                padding: 8px 16px;
                font-family: "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
                font-weight: 500;
                color: #2c3e50;
                text-align: center;
                transition: all 0.3s ease;
            }
            
            QPushButton:hover {
                border-color: rgba(46, 204, 113, 0.8);
                background-color: rgba(46, 204, 113, 0.05);
                transform: translateY(-1px);
            }
            
            QPushButton:pressed {
                transform: translateY(0px);
            }
        """
        
        self.activated_style = """
            QPushButton {
                background-color: #2ecc71;
                border: 2px solid #27ae60;
                border-radius: 8px;
                padding: 8px 16px;
                font-family: "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
                font-weight: 600;
                color: white;
                text-align: center;
                transition: all 0.3s ease;
            }
            
            QPushButton:hover {
                background-color: #27ae60;
                border-color: #229954;
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(46, 204, 113, 0.3);
            }
            
            QPushButton:pressed {
                background-color: #229954;
                transform: translateY(0px);
            }
        """
        
    def updateStyle(self):
        if self.activated:
            self.setStyleSheet(self.activated_style)
            self.setProperty("toggled", True)
        else:
            self.setStyleSheet(self.base_style)
            self.setProperty("toggled", False)
        
        self.style().unpolish(self)
        self.style().polish(self)
        
    def updateAccessibility(self):
        if self.activated:
            self.setAccessibleDescription("Toggle button activated - Press to deactivate")
            self.setAccessibleName(f"{self.text()} - Active")
        else:
            self.setAccessibleDescription("Toggle button not activated - Press to activate")
            self.setAccessibleName(f"{self.text()} - Inactive")
            
    def setActuated(self, state):
        if isinstance(state, bool) and state != self.activated:
            self.activated = state
            self.actuatedChange()
            self.updateStyle()
            self.updateAccessibility()
            self.actuated.emit(self.activated)
        elif not isinstance(state, bool):
            raise TypeError("State must be boolean")
            
    def isActuated(self):
        return self.activated
        
    def onActuate(self):
        self.activated = not self.activated
        self.actuatedChange()
        self.updateStyle()
        self.updateAccessibility()
        self.actuated.emit(self.activated)
        
    def actuatedChange(self):
        if self.animationGroup.state() == QParallelAnimationGroup.Running:
            self.animationGroup.stop()
            
        self.opacityAnimation.setStartValue(1.0)
        self.opacityAnimation.setKeyValueAt(0.5, 0.7)
        self.opacityAnimation.setEndValue(1.0)
        
        current_size = self.minimumSize()
        
        if self.activated:
            target_size = self.size() if self.size().isValid() else current_size
            target_size.setWidth(max(target_size.width(), current_size.width() + 10))
            target_size.setHeight(max(target_size.height(), current_size.height() + 2))
        else:
            target_size = current_size
            
        self.sizeAnimation.setStartValue(current_size)
        self.sizeAnimation.setEndValue(target_size)
        
        self.animationGroup.start()
        
    def enterEvent(self, event):
        super().enterEvent(event)
        if hasattr(self, 'opacityEffect'):
            pass
            
    def leaveEvent(self, event):
        super().leaveEvent(event)
        if hasattr(self, 'opacityEffect'):
            pass
            
    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(max(hint.width(), 100))
        hint.setHeight(max(hint.height(), 35))
        return hint
        
    def setText(self, text):
        super().setText(text)
        self.updateAccessibility()
        
    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        if not enabled and hasattr(self, 'animationGroup'):
            self.animationGroup.stop()
            
    def __del__(self):
        if hasattr(self, 'animationGroup'):
            self.animationGroup.stop()
```

<a name="directory-player"></a>
### Directory: `player`


#### File: `player\__init__.py`

```python

```

#### File: `player\filters_widget.py`

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSpinBox, QDoubleSpinBox, QComboBox, QFrame,
                               QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from gui_controls.toggle_button import ToggleButton
from gui_controls.list_tab import ListTabCtrl


class FilterParameter(QWidget):
    valueChanged = Signal(str, object)
    
    def __init__(self, param_name, param_config, parent=None):
        super().__init__(parent)
        self.param_name = param_name
        self.param_config = param_config
        self.control_widget = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        self.name_label = QLabel(self.param_name, self)
        self.name_label.setFixedWidth(100)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.name_label)
        
        param_type = self.param_config[0]
        param_data = self.param_config[1]
        
        if param_type == 'str':
            self.control_widget = QComboBox(self)
            self.control_widget.addItems(param_data)
            self.control_widget.currentTextChanged.connect(self.on_value_changed)
            
        elif param_type == 'int':
            min_val, max_val, offset, default = param_data
            self.control_widget = QSpinBox(self)
            self.control_widget.setMinimum(min_val)
            self.control_widget.setMaximum(max_val)
            self.control_widget.setSingleStep(offset)
            self.control_widget.setValue(default)
            self.control_widget.valueChanged.connect(self.on_value_changed)
            
        elif param_type == 'float':
            min_val, max_val, offset, default = param_data
            self.control_widget = QDoubleSpinBox(self)
            self.control_widget.setMinimum(min_val)
            self.control_widget.setMaximum(max_val)
            self.control_widget.setSingleStep(offset)
            self.control_widget.setValue(default)
            self.control_widget.setDecimals(2)
            self.control_widget.valueChanged.connect(self.on_value_changed)
            
        if self.control_widget:
            self.control_widget.setAccessibleName(f"{self.param_name} control")
            layout.addWidget(self.control_widget, 1)
            
    def on_value_changed(self, value):
        self.valueChanged.emit(self.param_name, value)
        
    def get_value(self):
        if isinstance(self.control_widget, QComboBox):
            return self.control_widget.currentText()
        elif isinstance(self.control_widget, (QSpinBox, QDoubleSpinBox)):
            return self.control_widget.value()
        return None
        
    def set_value(self, value):
        if isinstance(self.control_widget, QComboBox):
            index = self.control_widget.findText(str(value))
            if index >= 0:
                self.control_widget.setCurrentIndex(index)
        elif isinstance(self.control_widget, (QSpinBox, QDoubleSpinBox)):
            self.control_widget.setValue(value)

class FilterWidget(QWidget):
    filterActivated = Signal(str, bool)
    parameterChanged = Signal(str, str, object)
    
    def __init__(self, filter_name, filter_config, activate_callback=None, 
                 parameter_callback=None, parent=None):
        super().__init__(parent)
        
        self.filter_name = filter_name
        self.filter_config = filter_config
        self.activate_callback = activate_callback
        self.parameter_callback = parameter_callback
        self.is_active = False
        
        self.parameter_widgets = {}
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        self.filter_label = QLabel(self.filter_name, self)
        self.filter_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(self.filter_label)
        
        header_layout.addStretch()
        
        self.activate_toggle = ToggleButton("Activate", self)
        self.activate_toggle.setFixedSize(80, 25)
        header_layout.addWidget(self.activate_toggle)
        
        layout.addLayout(header_layout)
        
        separator = QFrame(self)
        separator.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Sunken)

        layout.addWidget(separator)
        
        self.parameters_widget = QWidget(self)
        self.parameters_layout = QVBoxLayout(self.parameters_widget)
        self.parameters_layout.setContentsMargins(0, 0, 0, 0)
        self.parameters_layout.setSpacing(3)
        
        for param_name, param_config in self.filter_config.items():
            param_widget = FilterParameter(param_name, param_config, self)
            param_widget.valueChanged.connect(self.on_parameter_changed)
            self.parameter_widgets[param_name] = param_widget
            self.parameters_layout.addWidget(param_widget)
            
        layout.addWidget(self.parameters_widget)
        
        self.parameters_widget.setEnabled(False)
        
    def connect_signals(self):
        self.activate_toggle.actuated.connect(self.on_filter_toggled)
        
    def on_filter_toggled(self, activated):
        self.is_active = activated
        self.parameters_widget.setEnabled(activated)
        
        if self.activate_callback:
            self.activate_callback(activated)
            
        self.filterActivated.emit(self.filter_name, activated)
        
    def on_parameter_changed(self, param_name, value):
        if self.parameter_callback:
            self.parameter_callback(param_name, value)
            
        self.parameterChanged.emit(self.filter_name, param_name, value)
        
    def get_parameter_value(self, param_name):
        if param_name in self.parameter_widgets:
            return self.parameter_widgets[param_name].get_value()
        return None
        
    def set_parameter_value(self, param_name, value):
        if param_name in self.parameter_widgets:
            self.parameter_widgets[param_name].set_value(value)
            
    def get_all_parameters(self):
        return {name: widget.get_value() 
                for name, widget in self.parameter_widgets.items()}
                
    def set_filter_active(self, active):
        self.activate_toggle.setActuated(active)

class FiltersWidget(QWidget):
    filterActivated = Signal(str, bool)
    parameterChanged = Signal(str, str, object)
    filtersToggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.filter_widgets = {}
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Filters", self)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setAccessibleName("Filters section")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.toggle_btn = ToggleButton("Show", self)
        self.toggle_btn.setFixedSize(60, 25)
        self.toggle_btn.setActuated(True)
        header_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(header_layout)
        
        self.filters_tab = ListTabCtrl(self)
        self.filters_tab.setAccessibleName("Filters list")
        self.filters_tab.setAccessibleDescription("List of available video filters")
        self.filters_tab.setVisible(False)
        layout.addWidget(self.filters_tab, 1)
        
    def connect_signals(self):
        self.toggle_btn.actuated.connect(self.toggle_filters)
        
    def toggle_filters(self, hidden):
        self.filters_tab.setVisible(not hidden)
        
        if hidden:
            self.toggle_btn.setText("Show")
        else:
            self.toggle_btn.setText("Hide")
            
        self.filtersToggled.emit(not hidden)
        
    def add_filter(self, filter_name, filter_config, activate_callback=None, 
                   parameter_callback=None):
        if filter_name in self.filter_widgets:
            print(f"Filter '{filter_name}' already exists")
            return
            
        filter_widget = FilterWidget(
            filter_name, filter_config, activate_callback, parameter_callback, self
        )
        
        filter_widget.filterActivated.connect(self.filterActivated.emit)
        filter_widget.parameterChanged.connect(self.parameterChanged.emit)
        
        self.filters_tab.addTab(filter_name, filter_widget)
        
        self.filter_widgets[filter_name] = filter_widget
        
    def remove_filter(self, filter_name):
        if filter_name not in self.filter_widgets:
            return
            
        index = self.filters_tab.indexOfTab(filter_name)
        if index >= 0:
            self.filters_tab.removeTab(index)
            
        del self.filter_widgets[filter_name]
        
    def get_filter_widget(self, filter_name):
        return self.filter_widgets.get(filter_name)
        
    def get_active_filters(self):
        return [name for name, widget in self.filter_widgets.items() 
                if widget.is_active]
                
    def clear_filters(self):
        self.filters_tab.deleteTabs()
        self.filter_widgets.clear()
        
    def set_filter_active(self, filter_name, active):
        if filter_name in self.filter_widgets:
            self.filter_widgets[filter_name].set_filter_active(active)
            
    def get_filter_parameters(self, filter_name):
        if filter_name in self.filter_widgets:
            return self.filter_widgets[filter_name].get_all_parameters()
        return {}
        
    def set_filter_parameter(self, filter_name, param_name, value):
        if filter_name in self.filter_widgets:
            self.filter_widgets[filter_name].set_parameter_value(param_name, value)
```

#### File: `player\player_controls.py`

```python
import os
import json

from typing import Optional, Callable, Dict, List, Tuple
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                               QSlider, QLabel, QSizePolicy, QFrame, QDialog, QListWidget, QDialogButtonBox, QMenu)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QFont, QShortcut

from gui_controls.toggle_button import ToggleButton
from gui_controls.key_event_filter import ShortcutManager
from app_config import key_config, prefs
from app_constance.misc import video_resolutions, video_speeds
from utilities.functions import get_app_path


class BookmarksDialog(QDialog):


    def __init__(self, bookmarks: List[float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bookmarks")
        self.setModal(True)
        self.resize(300, 400)
        
        layout = QVBoxLayout(self)
        
        self.bookmarks_list = QListWidget(self)
        for i, bookmark in enumerate(bookmarks):
            minutes = int(bookmark // 60)
            seconds = int(bookmark % 60)
            self.bookmarks_list.addItem(f"Mark {i+1}: {minutes:02d}:{seconds:02d}")
        
        layout.addWidget(self.bookmarks_list)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_selected_bookmark_index(self):
        current_row = self.bookmarks_list.currentRow()
        return current_row if current_row >= 0 else None


class PlayerControls(QWidget):
    fullscreenToggled = Signal(bool)
    speedChanged = Signal(float)
    resolutionChanged = Signal(object)
    playPauseClicked = Signal()
    muteUnmuteClicked = Signal()
    forwardClicked = Signal()
    backwardClicked = Signal()
    previousClicked = Signal()
    nextClicked = Signal()
    repeatClicked = Signal()
    shuffleClicked = Signal()
    
    seekChanged = Signal(int)
    seekPressed = Signal()
    seekReleased = Signal()
    volumeChanged = Signal(int)
    volumeUpRequested = Signal()
    volumeDownRequested = Signal()
    
    controlsToggled = Signal(bool)
    timeUpdateRequested = Signal()
    jumpToBeginningRequested = Signal()
    jumpToEndRequested = Signal()
    stopRequested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.last_position:Optional[int] = None
        self.is_minimized = False
        self.is_playing = False
        self.is_muted = False
        self.is_repeat_on = False
        self.is_shuffle_on = False
        self.is_fullscreen = False
        
        self._current_file: Optional[str] = None
        self._bookmarks: Dict[str, List[float]] = {}
        self._last_positions: Dict[str, float] = {}
        self._repeat_loops: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        self._data_dir = os.path.join(get_app_path(), "data")
        os.makedirs(self._data_dir, exist_ok=True)
        
        self._shortcut_manager: ShortcutManager = ShortcutManager(self)
        
        self.setup_ui()
        self.layout_widgets()
        self.connect_signals()
        self.apply_styles()
        self.set_shortcuts()
        self.load_bookmarks()
        self.load_last_positions()
        self.load_repeat_loops()
        
        self.time_update_timer = QTimer(self)
        self.time_update_timer.setInterval(700)
        self.time_update_timer.timeout.connect(self.timeUpdateRequested.emit)
        self.time_update_timer.timeout.connect(self._check_current_position)
        self.time_update_timer.start()
        
    def setup_ui(self):
        self.toggle_controls_btn = ToggleButton("◀", self)
        self.toggle_controls_btn.setFixedSize(30, 30)
        self.toggle_controls_btn.setToolTip("Minimize/Maximize Controls")
        
        self.previous_btn = QPushButton("⏮Previous", self)
        self.backward_btn = QPushButton("⏪Rewind", self)
        self.play_pause_btn = QPushButton("▶", self)
        self.forward_btn = QPushButton("⏩Forward", self)
        self.next_btn = QPushButton("⏭Next", self)
        self.repeat_btn = QPushButton("🔁Repeat", self)
        self.shuffle_btn = QPushButton("🔀Shuffle", self)
        
        for btn in [self.previous_btn, self.backward_btn, self.play_pause_btn,
                   self.forward_btn, self.next_btn, self.repeat_btn, self.shuffle_btn]:
            btn.setFixedSize(40, 40)
            
        self.play_pause_btn.setFixedSize(50, 50)
        
        self.previous_btn.setToolTip("Previous Track")
        self.backward_btn.setToolTip("Backward")
        self.play_pause_btn.setToolTip("Play/Pause")
        self.forward_btn.setToolTip("Forward")
        self.next_btn.setToolTip("Next Track")
        self.repeat_btn.setToolTip("Repeat")
        self.shuffle_btn.setToolTip("Shuffle")
        
        self.seek_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(100)
        self.seek_slider.setSingleStep(prefs.prefs["offset"]["seek"])
        self.seek_slider.setValue(0)
        self.seek_slider.setAccessibleName("Seek")

        
        self.mute_btn = QPushButton("🔊", self)
        self.mute_btn.setFixedSize(35, 35)
        self.mute_btn.setToolTip("Mute/Unmute")
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setSingleStep(prefs.prefs["offset"]["volume"])
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setAccessibleName("Volume")

        
        self.time_label = QLabel("00:00 / 00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setMinimumWidth(100)
        self.time_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        
        self.more_btn = QPushButton("⋯", self)
        self.more_btn.setFixedSize(35, 35)
        self.more_btn.setToolTip("More Options")


        
        self.current_track_label = QLabel("No media loaded", self)
        self.current_track_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.current_track_label.setAccessibleName("Currently Playing")
        
        self.separator1 = QFrame(self)
        self.separator1.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Sunken)
        
        self.separator2 = QFrame(self)
        self.separator2.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Sunken)
        
    def layout_widgets(self):

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        self.track_layout = QHBoxLayout()
        self.track_layout.addWidget(self.current_track_label)
        self.track_layout.addStretch()
        
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(15)
        
        self.transport_layout = QHBoxLayout()
        self.transport_layout.setSpacing(5)
        self.transport_layout.addWidget(self.previous_btn)
        self.transport_layout.addWidget(self.backward_btn)
        self.transport_layout.addWidget(self.play_pause_btn)
        self.transport_layout.addWidget(self.forward_btn)
        self.transport_layout.addWidget(self.next_btn)
        self.transport_layout.addWidget(self.repeat_btn)
        self.transport_layout.addWidget(self.shuffle_btn)
        
        self.volume_layout = QHBoxLayout()
        self.volume_layout.setSpacing(5)
        self.volume_layout.addWidget(self.mute_btn)
        self.volume_layout.addWidget(self.volume_slider)
        
        self.controls_layout.addLayout(self.transport_layout)
        self.controls_layout.addWidget(self.separator1)
        self.controls_layout.addWidget(self.seek_slider, 1)
        self.controls_layout.addWidget(self.separator2)
        self.controls_layout.addLayout(self.volume_layout)
        self.controls_layout.addWidget(self.time_label)
        self.controls_layout.addWidget(self.more_btn)
        self.controls_layout.addWidget(self.toggle_controls_btn)


        self.main_layout.addLayout(self.track_layout)
        self.main_layout.addLayout(self.controls_layout)
        
        self.expandable_widgets = [
            self.previous_btn, self.backward_btn, self.forward_btn, 
            self.next_btn, self.repeat_btn, self.separator1,
            self.seek_slider, self.separator2, self.mute_btn,
            self.volume_slider, self.time_label, self.current_track_label, self.shuffle_btn, 
            self.more_btn
        ]
        
    def connect_signals(self):
        self.play_pause_btn.clicked.connect(self.playPauseClicked.emit)
        self.mute_btn.clicked.connect(self.muteUnmuteClicked.emit)
        self.forward_btn.clicked.connect(self.forwardClicked.emit)
        self.backward_btn.clicked.connect(self.backwardClicked.emit)
        self.previous_btn.clicked.connect(self.previousClicked.emit)
        self.next_btn.clicked.connect(self.nextClicked.emit)
        self.repeat_btn.clicked.connect(self.repeatClicked.emit)
        self.shuffle_btn.clicked.connect(self.shuffleClicked.emit)
        
        self.seek_slider.valueChanged.connect(self.seekChanged.emit)
        self.seek_slider.sliderPressed.connect(self.seekPressed.emit)
        self.seek_slider.sliderReleased.connect(self.seekReleased.emit)
        self.volume_slider.valueChanged.connect(self.volumeChanged.emit)
        
        self.volumeUpRequested.connect(self.volume_up)
        self.volumeDownRequested.connect(self.volume_down)
        
        self.more_btn.clicked.connect(self.show_more_menu)
        
        self.toggle_controls_btn.actuated.connect(self.toggle_controls)

    def apply_styles(self):
        self.setStyleSheet("background-color: transparent;")
        button_style = """
            QPushButton {
                background-color: #3498db; border: none; border-radius: 20px;
                color: white; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #21618c; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """
        
        slider_style = """
            QSlider::groove:horizontal { border: 1px solid #bbb; background: white; height: 8px; border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #3498db; border: 1px solid #777; height: 8px; border-radius: 4px; }
            QSlider::add-page:horizontal { background: #fff; border: 1px solid #777; height: 8px; border-radius: 4px; }
            QSlider::handle:horizontal { background: #3498db; border: 2px solid #777; width: 18px; margin: -2px 0; border-radius: 9px; }
            QSlider::handle:horizontal:hover { background: #2980b9; }
        """
        
        for btn in [self.play_pause_btn, self.previous_btn, self.backward_btn,
                   self.forward_btn, self.next_btn, self.repeat_btn, self.mute_btn, self.more_btn]:
            btn.setStyleSheet(button_style)
            
        self.seek_slider.setStyleSheet(slider_style)
        self.volume_slider.setStyleSheet(slider_style)
        
        self.time_label.setStyleSheet("QLabel { color: #2c3e50; font-weight: bold; }")
        self.current_track_label.setStyleSheet("QLabel { color: #34495e; font-size: 14px; }")
        
    def toggle_controls(self, minimized):
        self.is_minimized = minimized
        
        for widget in self.expandable_widgets:
            widget.setVisible(not minimized)
            
        if minimized:
            self.toggle_controls_btn.setText("▶")
            self.toggle_controls_btn.setToolTip("Maximize Controls")
        else:
            self.toggle_controls_btn.setText("◀")
            self.toggle_controls_btn.setToolTip("Minimize Controls")
            
        self.controlsToggled.emit(not minimized)
    
    def show_more_menu(self):
        menu = QMenu(self)
        
        speed_menu = menu.addMenu("⚡ Speed")
        for speed in video_speeds:
            speed_text = f"{speed}x"
            action = speed_menu.addAction(speed_text)
            action.triggered.connect(self._create_speed_handler(speed))
        
        resolution_menu = menu.addMenu("📺 Resolution")
        action = resolution_menu.addAction("Original")
        action.triggered.connect(lambda: self.resolutionChanged.emit(None))
        
        for key, value in video_resolutions.items():
            display_name = f"{value['width']}x{value['height']}"
            action = resolution_menu.addAction(display_name)
            action.triggered.connect(self._create_resolution_handler((value['width'], value['height'])))
        
        fullscreen_action = menu.addAction("⛶ Fullscreen")
        fullscreen_action.setCheckable(True)
        fullscreen_action.setChecked(self.is_fullscreen)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        
        menu.exec(self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft()))
    
    def _create_speed_handler(self, speed):
        return lambda: self.speedChanged.emit(speed)
    
    def _create_resolution_handler(self, resolution):
        return lambda: self.resolutionChanged.emit(resolution)
    
    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.fullscreenToggled.emit(self.is_fullscreen)
    
    def set_fullscreen_state(self, is_fullscreen):
        self.is_fullscreen = is_fullscreen
        
    def set_play_pause_state(self, is_playing):
        if self.is_playing == is_playing: return
        self.is_playing = is_playing
        if is_playing:
            self.play_pause_btn.setText("⏸")
            self.play_pause_btn.setToolTip("Pause")
        else:
            self.play_pause_btn.setText("▶")
            self.play_pause_btn.setToolTip("Play")
            
    def set_mute_state(self, is_muted):
        if self.is_muted == is_muted: return
        self.is_muted = is_muted
        if is_muted:
            self.mute_btn.setText("🔇")
            self.mute_btn.setToolTip("Unmute")
        else:
            self.mute_btn.setText("🔊")
            self.mute_btn.setToolTip("Mute")
            
    def set_repeat_state(self, is_repeat_on):
        if self.is_repeat_on == is_repeat_on: return
        self.is_repeat_on = is_repeat_on
        base_style = self.play_pause_btn.styleSheet()
        if is_repeat_on:
            self.repeat_btn.setStyleSheet(base_style + "QPushButton { background-color: #e74c3c; }")
        else:
            self.repeat_btn.setStyleSheet(base_style)
            
    def set_shuffle_state(self, is_shuffle_on):
        if self.is_shuffle_on == is_shuffle_on: return
        self.is_shuffle_on = is_shuffle_on
        base_style = self.play_pause_btn.styleSheet()
        if is_shuffle_on:
            self.shuffle_btn.setStyleSheet(base_style + "QPushButton { background-color: #e74c3c; }")
        else:
            self.shuffle_btn.setStyleSheet(base_style)
            
    def set_seek_range(self, minimum, maximum):
        self.seek_slider.setRange(minimum, maximum)
        
    def set_seek_position(self, position):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(position)
        self.seek_slider.blockSignals(False)
        
    def set_volume(self, volume):
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)
        
    def set_time_text(self, time_text):
        self.time_label.setText(time_text)
        
    def set_current_track(self, track_name):
        self.current_track_label.setText(track_name)
        
    def get_seek_position(self):
        return self.seek_slider.value()
        
    def get_volume(self):
        return self.volume_slider.value()
        
    def set_controls_enabled(self, enabled):
        for widget in [self.play_pause_btn, self.previous_btn, self.backward_btn,
                      self.forward_btn, self.next_btn, self.repeat_btn, self.shuffle_btn,
                      self.mute_btn, self.seek_slider, self.volume_slider]:
            widget.setEnabled(enabled)
    
    def set_shortcuts(self):
        hotkeys = key_config.key_config["Player"]
        
        shortcuts: Dict[str, Callable] = {
            hotkeys["Play/Pause"]: self.playPauseClicked.emit,
            hotkeys["Backward"]: self.backwardClicked.emit,
            hotkeys["Forward"]: self.forwardClicked.emit,
            hotkeys["Stop"]: self.stopRequested.emit,
            hotkeys["Mute/Unmute"]: self.muteUnmuteClicked.emit,
            hotkeys["Previous"]: lambda: print("sucksuck"),# self.previousClicked.emit(),
            hotkeys["Next"]: self.nextClicked.emit,
            hotkeys["Jump to beginning"]: self.jumpToBeginningRequested.emit,
            hotkeys["Jump to the end"]: self.jumpToEndRequested.emit,
            hotkeys["Toggle repeat"]: self.repeatClicked.emit,
            hotkeys["Volume up"]: self.volume_up,
            hotkeys["Volume down"]: self.volume_down,
            hotkeys["Bookmarks list"]: self.show_bookmarks_dialog,
            hotkeys["New mark at current position"]: self.add_bookmark_at_current_position,
            hotkeys["Repeat loop start"]: self.set_loop_start,
            hotkeys["Repeat loop end"]: self.set_loop_end,
            hotkeys["Clear repeat loop"]: self.clear_repeat_loop,
            hotkeys["Mark1 position"]: lambda: self.jump_to_mark(0),
            hotkeys["Mark2 position"]: lambda: self.jump_to_mark(1),
            hotkeys["Mark3 position"]: lambda: self.jump_to_mark(2),
            hotkeys["Mark4 position"]: lambda: self.jump_to_mark(3),
            hotkeys["Mark5 position"]: lambda: self.jump_to_mark(4),
            hotkeys["Mark6 position"]: lambda: self.jump_to_mark(5),
            hotkeys["Mark7 position"]: lambda: self.jump_to_mark(6),
            hotkeys["Mark8 position"]: lambda: self.jump_to_mark(7),
            hotkeys["Mark9 position"]: lambda: self.jump_to_mark(8),
            hotkeys["Mark10 position"]: lambda: self.jump_to_mark(9),
        }
        
        self._shortcut_manager.clear_shortcuts()
        for shortcut, callback in shortcuts.items():
            #sh = QShortcut(shortcut, self)
            #sh.activated.connect(callback)
            #sh.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self._shortcut_manager.add_widget_shortcut(self, shortcut, callback)


    def reset_shortcuts(self):
        self.set_shortcuts()
    
    def set_current_file(self, file_path: str):
        if self._current_file:
            self.save_last_position()
        
        self._current_file = file_path
    
    def show_bookmarks_dialog(self):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        
        bookmarks = self._bookmarks[self._current_file]
        if not bookmarks:
            return
        
        dialog = BookmarksDialog(bookmarks, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_index = dialog.get_selected_bookmark_index()
            if selected_index is not None:
                self.jump_to_mark(selected_index)
    
    def add_bookmark_at_current_position(self):
        if not self._current_file:
            return
        
        current_pos = self.get_seek_position()
        
        if self._current_file not in self._bookmarks:
            self._bookmarks[self._current_file] = []
        
        self._bookmarks[self._current_file].append(current_pos)
        self._bookmarks[self._current_file].sort()
        self.save_bookmarks()
    
    def jump_to_mark(self, mark_index: int):
        if not self._current_file or self._current_file not in self._bookmarks:
            return
        
        bookmarks = self._bookmarks[self._current_file]
        if mark_index < len(bookmarks):
            position = bookmarks[mark_index]
            self.set_seek_position(int(position))
            self.seekChanged.emit(int(position))
    
    def set_loop_start(self):
        if not self._current_file:
            return
        
        current_pos = float(self.get_seek_position())
        
        if self._current_file not in self._repeat_loops:
            self._repeat_loops[self._current_file] = (None, None)
        
        loop_start, loop_end = self._repeat_loops[self._current_file]
        self._repeat_loops[self._current_file] = (current_pos, loop_end)
        self.save_repeat_loops()
    
    def set_loop_end(self):
        if not self._current_file:
            return
        
        current_pos = float(self.get_seek_position())
        
        if self._current_file not in self._repeat_loops:
            self._repeat_loops[self._current_file] = (None, None)
        
        loop_start, loop_end = self._repeat_loops[self._current_file]
        self._repeat_loops[self._current_file] = (loop_start, current_pos)
        self.save_repeat_loops()
    
    def clear_repeat_loop(self):
        if self._current_file and self._current_file in self._repeat_loops:
            self._repeat_loops[self._current_file] = (None, None)
            self.save_repeat_loops()
    
    def get_current_loop(self) -> Tuple[Optional[float], Optional[float]]:
        if not self._current_file or self._current_file not in self._repeat_loops:
            return (None, None)
        return self._repeat_loops[self._current_file]
    
    def should_loop_playback(self, current_position: float) -> Optional[float]:
        if not self._current_file or self._current_file not in self._repeat_loops:
            return None
        
        loop_start, loop_end = self._repeat_loops[self._current_file]
        if loop_start is not None and loop_end is not None:
            if current_position >= loop_end:
                return loop_start
        return None
    
    def get_bookmarks(self) -> List[float]:
        if not self._current_file or self._current_file not in self._bookmarks:
            return []
        return self._bookmarks[self._current_file].copy()
    
    def clear_bookmarks(self):
        if self._current_file and self._current_file in self._bookmarks:
            del self._bookmarks[self._current_file]
            self.save_bookmarks()
    
    def save_bookmarks(self):
        bookmarks_file = os.path.join(self._data_dir, "bookmarks.json")
        try:
            with open(bookmarks_file, 'w') as f:
                json.dump(self._bookmarks, f, indent=2)
        except Exception:
            pass
    
    def load_bookmarks(self):
        bookmarks_file = os.path.join(self._data_dir, "bookmarks.json")
        try:
            if os.path.exists(bookmarks_file):
                with open(bookmarks_file, 'r') as f:
                    self._bookmarks = json.load(f)
        except Exception:
            self._bookmarks = {}
    
    def save_repeat_loops(self):
        loops_file = os.path.join(self._data_dir, "repeat_loops.json")
        try:
            with open(loops_file, 'w') as f:
                json.dump(self._repeat_loops, f, indent=2)
        except Exception:
            pass
    
    def load_repeat_loops(self):
        loops_file = os.path.join(self._data_dir, "repeat_loops.json")
        try:
            if os.path.exists(loops_file):
                with open(loops_file, 'r') as f:
                    self._repeat_loops = json.load(f)
        except Exception:
            self._repeat_loops = {}
    
    def save_last_position(self):
        if not self._current_file:
            return
        
        current_pos = self.get_seek_position()
        self._last_positions[self._current_file] = current_pos
        
        positions_file = os.path.join(self._data_dir, "last_positions.json")
        try:
            with open(positions_file, 'w') as f:
                json.dump(self._last_positions, f, indent=2)
        except Exception:
            pass
    
    def load_last_positions(self):
        positions_file = os.path.join(self._data_dir, "last_positions.json")
        try:
            if os.path.exists(positions_file):
                with open(positions_file, 'r') as f:
                    self._last_positions = json.load(f)
        except Exception:
            self._last_positions = {}
    
    def load_last_position(self):
        if not self._current_file:
            return
        
        if self._current_file in self._last_positions:
            try:
                last_pos = self._last_positions[self._current_file]
                if isinstance(last_pos, (int, float)) and last_pos >= 0:
                    #max_duration = self.seek_slider.maximum()
                    #if max_duration > 0 and last_pos <= max_duration:
                    self.last_position = int(last_pos)
                        #self.set_seek_position(int(last_pos))
                        #self.seekChanged.emit(int(last_pos))
            except Exception as e:
                pass
    
    def volume_up(self):
        current_volume = self.get_volume()
        volume_offset = prefs.prefs["offset"]["volume"]
        new_volume = min(100, current_volume + volume_offset)
        self.set_volume(new_volume)
        self.volumeChanged.emit(new_volume)
    
    def volume_down(self):
        current_volume = self.get_volume()
        volume_offset = prefs.prefs["offset"]["volume"]
        new_volume = max(0, current_volume - volume_offset)
        self.set_volume(new_volume)
        self.volumeChanged.emit(new_volume)
    
    def check_loop_position(self, current_position: float):
        loop_position = self.should_loop_playback(current_position)
        if loop_position is not None:
            self.set_seek_position(int(loop_position))
            self.seekChanged.emit(int(loop_position))
    
    def _check_current_position(self):
        if self._current_file:
            current_pos = float(self.get_seek_position())
            self.check_loop_position(current_pos)
    
    def install_shortcuts(self):
        self._shortcut_manager.install_on_application()
    
    def uninstall_shortcuts(self):
        self._shortcut_manager.uninstall_from_application()
```

#### File: `player\player_widget.py`

```python
import os
import time
import av_play

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QLabel, QListWidget, QListWidgetItem, QMessageBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, Signal, QTimer, QSize

from app_config import prefs
from .player_controls import PlayerControls
from .filters_widget import FiltersWidget

from gui_controls.toggle_button import ToggleButton
from .subtitles import SubtitleManager
from utilities.functions import get_app_path, get_parent_dir
from utilities.media_utils import format_time, seconds_to_microseconds, get_media_files_from_directory


class SubtitlesWidget(QWidget):
    subtitlesToggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Subtitles", self)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setAccessibleName("Subtitles section")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.toggle_btn = ToggleButton("Hide", self)
        self.toggle_btn.setFixedSize(60, 25)
        header_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(header_layout)
        
        self.subtitles_list = QListWidget(self)
        self.subtitles_list.setAccessibleName("Subtitles display")
        self.subtitles_list.setAccessibleDescription("Current video subtitles")
        self.subtitles_list.setAlternatingRowColors(True)
        self.subtitles_list.setMaximumHeight(150)
        
        self.subtitles_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
        """)
        
        layout.addWidget(self.subtitles_list)
        
    def connect_signals(self):
        self.toggle_btn.actuated.connect(self.toggle_subtitles)
        
    def toggle_subtitles(self, hidden):
        self.subtitles_list.setVisible(not hidden)
        
        if hidden:
            self.toggle_btn.setText("Show")
        else:
            self.toggle_btn.setText("Hide")
            
        self.subtitlesToggled.emit(not hidden)
        
    def add_subtitle_line(self, text, timestamp=None):
        item = QListWidgetItem(text)
        if timestamp:
            item.setData(Qt.ItemDataRole.UserRole, timestamp)

        self.subtitles_list.addItem(item)
        
    def clear_subtitles(self):
        self.subtitles_list.clear()
        
    def highlight_subtitle_at_time(self, timestamp):
        for i in range(self.subtitles_list.count()):
            item = self.subtitles_list.item(i)
            item_timestamp = item.data(Qt.ItemDataRole.UserRole)
            if item_timestamp and item_timestamp <= timestamp:
                self.subtitles_list.setCurrentItem(item)
            else:
                break

class VideoDisplayWidget(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.placeholder_label = QLabel("Video Display Area", self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border: 2px dashed #34495e;
            }
        """)
        self.placeholder_label.setMinimumSize(640, 360)
        self.placeholder_label.setAccessibleName("Video display area")
        self.placeholder_label.setAccessibleDescription("Main video playback area")
        
        layout.addWidget(self.placeholder_label)

class PlayerWidget(QWidget):


    def _on_fullscreen_toggled(self, enabled):

        self.player.set_fullscreen(enabled)

    def _on_speed_changed(self, speed):

        self.player.set_playback_speed(speed)

    def _on_resolution_changed(self, resolution):

        if resolution:
            self.player.set_resolution(*resolution)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_seeking = False
        self._last_known_state = av_play.AVPlaybackState.AV_STATE_NOTHING
        self._active_filters = {}
        self._session_filters = {}

        self.setup_ui()
        self.layout_widgets()

        self.player:av_play.MPVVideoPlayer = av_play.MPVVideoPlayer()
        self.subtitle_manager = SubtitleManager()
        self.loading = False

        self._init_player()
        self._populate_filters()

        self.connect_signals()
        self.apply_styles()
        
    def setup_ui(self):
        self.video_display = VideoDisplayWidget(self)
        self.player_controls = PlayerControls(self)
        self.filters_widget = FiltersWidget(self)
        self.subtitles_widget = SubtitlesWidget(self)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        
    def layout_widgets(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        left_layout.addWidget(self.video_display, 1)
        left_layout.addWidget(self.player_controls)
        left_layout.addWidget(self.subtitles_widget)
        
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(self.filters_widget)
        self.main_splitter.setSizes([800, 300])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        
        self.main_layout.addWidget(self.main_splitter)

    def _init_player(self):
        yt_dlp_path = os.path.join(get_parent_dir(), "bin", "yt-dlp.exe" if os.name == 'nt' else "yt-dlp")
        try:
            self.player.init(window=self.video_display.winId(), ytdl_path = yt_dlp_path)
            self.player.set_auto_play(prefs.prefs["autoplay"]) 
            self.player.set_start_file_callback(self.seek_to_last_pos)
        except av_play.AVError as e:
            self.player_controls.set_controls_enabled(False)

    def _populate_filters(self):
        self.available_filters = {
            "Echo": av_play.MPVEchoFilter,
            "Low Pass": av_play.MPVLowPassFilter, "High Pass": av_play.MPVHighPassFilter,
            "Compressor": av_play.MPVCompressorFilter, "Flanger": av_play.MPVFlangerFilter,
            "Chorus": av_play.MPVChorusFilter, "Pitch Shift": av_play.MPVPitchShiftFilter,
            "Band Pass": av_play.MPVBandPassFilter, "Gate": av_play.MPVGateFilter
        }
        for name, filter_class in self.available_filters.items():
            try:
                instance = filter_class()
                params = instance.get_parameters()
                config = {}
                for param_name, default_value in params.items():
                    param_info = instance.info.get("mpv_param_map", {}).get(param_name)
                    if param_info:
                        _, p_type, p_range = param_info
                        if p_type == str and len(p_range) > 0:
                            config[param_name] = ('str', p_range)
                        elif p_type in (int, float) and len(p_range) > 0:
                            config[param_name] = (p_type.__name__, p_range)
                self.filters_widget.add_filter(name, config)
            except Exception:
                continue

    def connect_signals(self):
        self.player_controls.playPauseClicked.connect(self._on_play_pause_clicked)
        self.player_controls.muteUnmuteClicked.connect(self._on_mute_unmute_clicked)
        self.player_controls.forwardClicked.connect(self._on_forward_clicked)
        self.player_controls.backwardClicked.connect(self._on_backward_clicked)
        self.player_controls.previousClicked.connect(self._on_previous_clicked)
        self.player_controls.nextClicked.connect(self._on_next_clicked)
        self.player_controls.repeatClicked.connect(self._on_repeat_clicked)
        self.player_controls.shuffleClicked.connect(self._on_shuffle_clicked)
        
        self.player_controls.seekChanged.connect(self._on_seek_changed)
        self.player_controls.seekPressed.connect(self._on_seek_pressed)
        self.player_controls.seekReleased.connect(self._on_seek_released)
        self.player_controls.volumeChanged.connect(self._on_volume_changed)
        
        self.player_controls.volumeUpRequested.connect(self._on_volume_up)
        self.player_controls.volumeDownRequested.connect(self._on_volume_down)
        self.player_controls.jumpToBeginningRequested.connect(self._on_jump_to_beginning)
        self.player_controls.jumpToEndRequested.connect(self._on_jump_to_end)
        self.player_controls.stopRequested.connect(self._on_stop)
        
        self.player_controls.speedChanged.connect(self._on_speed_changed)
        self.player_controls.resolutionChanged.connect(self._on_resolution_changed)
        self.player_controls.fullscreenToggled.connect(self._on_fullscreen_toggled)

        self.player_controls.timeUpdateRequested.connect(self._update_player_state)
        
        self.filters_widget.filterActivated.connect(self._on_filter_activated)
        self.filters_widget.parameterChanged.connect(self._on_filter_parameter_changed)
        
        self.player_controls.install_shortcuts()

    def apply_styles(self):
        self.setStyleSheet("""
            PlayerWidget { background-color: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 8px; }
        """)

    def _on_play_pause_clicked(self):
        instance = self.player.primary_instance
        if not instance:
            QMessageBox.warning(self, "Playback Error", "No media instance available.")
            return
        try:
            state = instance.get_playback_state()
            if state == av_play.AVPlaybackState.AV_STATE_PLAYING:
                instance.pause()
                self.player_controls.save_last_position()
            else:
                if state == av_play.AVPlaybackState.AV_STATE_STOPPED or av_play.AVPlaybackState.AV_STATE_PAUSED:
                    instance.play()
        except av_play.AVError as e:
            msg = f"Playback error: {getattr(e, 'message', str(e))}"
            QMessageBox.critical(self, "Playback Error", msg)
        
    def _on_mute_unmute_clicked(self):
        instance = self.player.primary_instance
        if not instance:
            QMessageBox.warning(self, "Mute Error", "No media instance available.")
            return
        try:
            state = instance.get_mute_state()
            if state == av_play.AVMuteState.AV_AUDIO_MUTED:
                instance.unmute()
            else:
                instance.mute()
        except av_play.AVError as e:
            msg = f"Mute error: {getattr(e, 'message', str(e))}"
            QMessageBox.critical(self, "Mute Error", msg)
        
    def _on_forward_clicked(self):
        if self.player: self.player.forward(prefs.prefs["offset"]["seek"])
        
    def _on_backward_clicked(self):
        if self.player: self.player.backward(prefs.prefs["offset"]["seek"])
        
    def _on_previous_clicked(self):
        if self.player: self.player.previous()
        
    def _on_next_clicked(self):
        if self.player: self.player.next()
        
    def _on_repeat_clicked(self):
        current_mode = self.player.get_playlist_mode()
        is_shuffle_mode = current_mode == av_play.AVPlaylistMode.SHUFFLE
        
        if current_mode == av_play.AVPlaylistMode.REPEAT_ALL:
            new_mode = av_play.AVPlaylistMode.REPEAT_ONE
            self.player_controls.set_repeat_state(True)
        elif current_mode == av_play.AVPlaylistMode.REPEAT_ONE:
            if is_shuffle_mode:
                new_mode = av_play.AVPlaylistMode.SHUFFLE
            else:
                new_mode = av_play.AVPlaylistMode.SEQUENTIAL
            self.player_controls.set_repeat_state(False)
        else:
            if is_shuffle_mode:
                new_mode = av_play.AVPlaylistMode.SHUFFLE
            else:
                new_mode = av_play.AVPlaylistMode.REPEAT_ALL
            self.player_controls.set_repeat_state(True)
        self.player.set_playlist_mode(new_mode)
        
    def _on_shuffle_clicked(self):
        current_mode = self.player.get_playlist_mode()
        if current_mode == av_play.AVPlaylistMode.SHUFFLE:
            if self.player_controls.is_repeat_on:
                new_mode = av_play.AVPlaylistMode.REPEAT_ALL
            else:
                new_mode = av_play.AVPlaylistMode.SEQUENTIAL
            self.player_controls.set_shuffle_state(False)
        else:
            new_mode = av_play.AVPlaylistMode.SHUFFLE
            self.player_controls.set_shuffle_state(True)
        self.player.set_playlist_mode(new_mode)
        
    def _on_seek_changed(self, position):
        if self.player.primary_instance is not None:
            self.player_controls.set_time_text(f"{format_time(position)} / {format_time(self.player.primary_instance.get_length())}")
            self.is_seeking = True
            self.set_position()
            self.is_seeking = False

    def _on_seek_pressed(self):
        self.is_seeking = True
        
    def _on_seek_released(self):
        self.is_seeking = False
        self.set_position()

    def set_position(self):
        instance = self.player.primary_instance
        if instance:
            try:
                position = self.player_controls.get_seek_position()
                instance.set_position(position)
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Seek Error", msg)
        
    def _on_volume_changed(self, volume):
        instance = self.player.primary_instance
        if instance:
            try:
                instance.set_volume(float(volume))
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Volume Error", msg)

    def _on_volume_up(self):
        instance = self.player.primary_instance
        if instance:
            try:
                current_volume = instance.get_volume()
                new_volume = min(100, current_volume + prefs.prefs["offset"]["volume"])
                instance.set_volume(new_volume)
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Volume Error", msg)
    
    def _on_volume_down(self):
        instance = self.player.primary_instance
        if instance:
            try:
                current_volume = instance.get_volume()
                new_volume = max(0, current_volume - prefs.prefs["offset"]["volume"])
                instance.set_volume(new_volume)
            except av_play.AVError as e:
                msg = f"Volume error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Volume Error", msg)
    
    def _on_jump_to_beginning(self):
        instance = self.player.primary_instance
        if instance:
            try:
                instance.set_position(0)
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Seek Error", msg)
    
    def _on_jump_to_end(self):
        instance = self.player.primary_instance
        if instance:
            try:
                length = instance.get_length()
                instance.set_position(length -1)
            except av_play.AVError as e:
                msg = f"Seek error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Seek Error", msg)
    
    def _on_stop(self):
        instance = self.player.primary_instance
        if instance:
            try:
                self.player_controls.save_last_position()
                instance.stop()
            except av_play.AVError as e:
                msg = f"Stop error: {getattr(e, 'message', str(e))}"
                QMessageBox.critical(self, "Stop Error", msg)

    def _on_filter_activated(self, filter_name, activated):
        instance = self.player.primary_instance
        if not instance:
            return
        try:
            if activated:
                if filter_name in self.available_filters and filter_name not in self._active_filters:
                    filter_class = self.available_filters[filter_name]
                    filter_instance = filter_class()
                    gui_params = self.filters_widget.get_filter_parameters(filter_name)
                    filter_instance.set_parameters(gui_params)
                    filter_id = instance.apply_filter(filter_instance)
                    self._active_filters[filter_name] = filter_id
                    self._session_filters[filter_name] = gui_params.copy()
            else:
                if filter_name in self._active_filters:
                    filter_id = self._active_filters.pop(filter_name)
                    instance.remove_filter(filter_id)
                    if filter_name in self._session_filters:
                        del self._session_filters[filter_name]
        except av_play.AVError:
            pass

    def _on_filter_parameter_changed(self, filter_name, param_name, value):
        instance = self.player.primary_instance
        if not instance or filter_name not in self._active_filters:
            return
        
        try:
            filter_id = self._active_filters[filter_name]
            instance.set_parameter(filter_id, param_name, value)
        except av_play.AVError:
            pass

    def _update_player_state(self):
        instance = self.player.primary_instance
        if not instance:
            self._reset_ui_to_default()
            return
        
        try:
            state = instance.get_playback_state()
            pos = instance.get_position()
            length = instance.get_length()
            
            if state == av_play.AVPlaybackState.AV_STATE_NOTHING and self._last_known_state == av_play.AVPlaybackState.AV_STATE_PLAYING:
                self._last_known_state = state
                self.player.next()
                self._load_subtitles_for_current_track()
                self._update_current_file()
                return

            self._last_known_state = state
            
            self.player_controls.set_play_pause_state(state == av_play.AVPlaybackState.AV_STATE_PLAYING)
            self.player_controls.set_mute_state(instance.get_mute_state() == av_play.AVMuteState.AV_AUDIO_MUTED)
            self.player_controls.set_volume(int(instance.get_volume()))
            self.player_controls.set_current_track(os.path.basename(instance.file_path))
            
            if length > 0:
                self.player_controls.set_controls_enabled(True)
                self.player_controls.set_seek_range(0, length)
                
                if not self.is_seeking:
                    self.player_controls.set_seek_position(pos)
                    self.player_controls.check_loop_position(pos)
                
                self.player_controls.set_time_text(f"{format_time(pos)} / {format_time(length)}")
            
            current_subtitle = self.subtitle_manager.get_subtitle_at(seconds_to_microseconds(pos))
            if current_subtitle:
                self.subtitles_widget.subtitles_list.clear()
                self.subtitles_widget.subtitles_list.addItem(QListWidgetItem(current_subtitle))

        except (av_play.AVError, Exception):
            pass

    def _update_current_file(self):
        instance = self.player.primary_instance
        if instance:
            self.player_controls.set_current_file(instance.file_path)

    def seek_to_last_pos(self, event:object):
        self.seek_to_last()
        #QTimer.singleShot(1, self.seek_to_last)

    def seek_to_last(self):
        instance = self.player.primary_instance
        if not instance:
            return

        try:
            self.player_controls.load_last_position()
            self.loading = False
            if self.player_controls.last_position and self.player_controls.last_position > 0:
                #length = instance.get_length()
                #if length > 0 and self.player_controls.last_position <= length:

                #self.player_controls.seek_slider.blockSignals(True)
                #self.is_seeking = True
                instance.set_position(self.player_controls.last_position)
                #self.player_controls.seek_slider.blockSignals(False)
                #self.is_seeking = False
        except av_play.AVError:
            pass

    def _load_subtitles_for_current_track(self):
        self.subtitles_widget.clear_subtitles()
        instance = self.player.primary_instance
        if instance and av_play.is_path(instance.file_path):
            self.subtitle_manager.load_for_video(instance.file_path)

    def _reset_ui_to_default(self):
        self.player_controls.set_current_track("No media loaded")
        self.player_controls.set_time_text("00:00 / 00:00")
        self.player_controls.set_seek_range(0, 100)
        self.player_controls.set_seek_position(0)
        self.player_controls.set_play_pause_state(False)
        self.player_controls.set_controls_enabled(False)
        self.subtitles_widget.clear_subtitles()

    def load_file(self, file_path: str):
        if self.loading: return
        self.loading = True
        try:
            if self.player:
                self.player.stop_playlist()
                instance = self.player.primary_instance
                if instance:
                    instance.stop()
                    instance.release()
            self.player_controls.set_current_file(file_path)
            dir_path = os.path.dirname(file_path)
            media_files = get_media_files_from_directory(dir_path, av_play.formats["audio"], av_play.formats["video"])
            
            playlist = av_play.Playlist(title=os.path.basename(dir_path))
            start_index = 0
            for i, media_file in enumerate(media_files):
                playlist.add_entry(av_play.PlaylistEntry(location=media_file, title=os.path.basename(media_file)))
                if media_file == file_path:
                    start_index = i

            self.load_playlist(playlist, start_index=start_index)
            #self.player_controls.load_last_position()
        except Exception:
            self._reset_ui_to_default()

    def load_url(self, url: str):
        try:
            playlist = av_play.Playlist(title=url)
            playlist.add_entry(av_play.PlaylistEntry(location=url, title="Streaming URL"))
            self.load_playlist(playlist)
        except Exception:
            self._reset_ui_to_default()

    def load_playlist(self, playlist: av_play.Playlist, start_index: int = 0, auto_play: bool = True):
        try:
            if self.player.primary_instance is not None:
                try:
                    self.player.primary_instance.release()
                    self.player._primary_instance = None
                except Exception:
                    pass
            self.player.stop_playlist()
            self.player.load_playlist(playlist, auto_play=auto_play)
            self._active_filters.clear()
            instance = self.player.primary_instance
            if instance and self._session_filters:
                for filter_name, params in self._session_filters.items():
                    if filter_name in self.available_filters:
                        filter_class = self.available_filters[filter_name]
                        filter_instance = filter_class()
                        filter_instance.set_parameters(params)
                        filter_id = instance.apply_filter(filter_instance)
                        self._active_filters[filter_name] = filter_id
            if 0 <= start_index < len(playlist) and start_index != 0:
                try:
                    jump_method = getattr(self.player, 'jump_to_track', None)
                    if jump_method and callable(jump_method):
                        jump_method(start_index)
                    else:
                        self.player._current_playlist_index = start_index
                        if auto_play:
                            self.player._play_playlist_track()
                except Exception:
                    self.player._current_playlist_index = start_index
                    if auto_play:
                        self.player._play_playlist_track()

            self._load_subtitles_for_current_track()
            self._update_current_file()
            self._update_player_state()
        except Exception as e:
            self._reset_ui_to_default()

    def change_path(self, path: str):
        if not path: return
        try:
            if av_play.is_url(path):
                self.load_url(path)
            elif os.path.isfile(path):
                ext = path.split('.')[-1].lower()
                if ext in ['m3u', 'm3u8', 'pls', 'xspf', 'json']:
                    playlist = av_play.Playlist().load(path)
                    self.load_playlist(playlist)
                else:
                    self.load_file(path)
        except Exception:
            self._reset_ui_to_default()
            
    def sizeHint(self):
        return QSize(1200, 800)
        
    def minimumSizeHint(self):
        return QSize(800, 600)

    def closeEvent(self, event):
        try:
            self.player_controls.save_last_position()
            
            self.player_controls.uninstall_shortcuts()
            if self.player.primary_instance is not None:
                try:
                    self.player.primary_instance.release()
                except Exception:
                    pass
            self.player.release()
        except Exception:
            pass
        super().closeEvent(event)
```

#### File: `player\subtitles.py`

```python
import os
import cchardet
from pycaption import detect_format, CaptionNode
from pycaption.base import CaptionList
from typing import List, Optional

class SubtitleEntry:

    
    def __init__(self, text: str, start_usec: int, end_usec: int):
        self.text = text
        self.start = start_usec
        self.end = end_usec

class SubtitleManager:


    def __init__(self):
        self.subtitles: List[SubtitleEntry] = []
        self.supported_formats = ["srt", "vtt", "smi", "sami", "scc", "dfxp", "ttml", "sub", "ass"]
        self.current_subtitle_path: Optional[str] = None

    def _find_subtitle_file(self, video_path: str) -> Optional[str]:
        try:
            if not os.path.isfile(video_path):
                return None
            dir_path = os.path.dirname(video_path)
            filename = os.path.splitext(os.path.basename(video_path))[0]
            for fmt in self.supported_formats:
                sub_path = os.path.join(dir_path, f"{filename}.{fmt}")
                if os.path.exists(sub_path):
                    return sub_path
        except Exception:
            pass
        return None

    def _get_encoding(self, path: str) -> str:
        try:
            with open(path, "rb") as fp:
                detection = cchardet.detect(fp.read())
                return detection["encoding"] if detection else 'utf-8'
        except Exception:
            return 'utf-8'

    def load_for_video(self, video_path: str, language: str = 'en-US') -> bool:
        self.clear()
        self.current_subtitle_path = self._find_subtitle_file(video_path)
        if not self.current_subtitle_path:
            return False

        try:
            encoding = self._get_encoding(self.current_subtitle_path)
            with open(self.current_subtitle_path, "r", encoding=encoding, errors='ignore') as f:
                content = f.read()

            reader_class = detect_format(content)
            if not reader_class:
                return False
            
            caption_set = reader_class().read(content)
            
            available_langs = caption_set.get_languages()
            if not available_langs:
                return False

            lang_to_use = language if language in available_langs else available_langs[0]
                
            captions: CaptionList = caption_set.get_captions(lang_to_use)
            
            for caption in captions:
                text = ' '.join([node.content for node in caption.nodes if node.type_ == CaptionNode.TEXT]).strip()
                if text:
                    self.subtitles.append(SubtitleEntry(text.replace('\n', ' '), caption.start, caption.end))
            
            return len(self.subtitles) > 0
        except Exception:
            self.clear()
            return False

    def get_subtitle_at(self, position_usec: int) -> Optional[str]:
        for sub in self.subtitles:
            if sub.start <= position_usec <= sub.end:
                return sub.text
        return None

    def clear(self):
        self.subtitles.clear()
        self.current_subtitle_path = None
```

<a name="directory-playlist_manager"></a>
### Directory: `playlist_manager`


#### File: `playlist_manager\__init__.py`

```python

```

#### File: `playlist_manager\playlist_create_dialog.py`

```python
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QLabel, QPushButton, QListWidget, QFileDialog,
                               QMessageBox, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from av_play import Playlist, PlaylistEntry
import os


class PlaylistCreateDialog(QDialog):
    playlist_created = Signal(str, Playlist)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Playlist")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(600, 400)
        self.tracks = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter playlist name")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        tracks_layout = QVBoxLayout()
        tracks_label = QLabel("Tracks:")
        tracks_layout.addWidget(tracks_label)
        
        self.tracks_list = QListWidget()
        self.tracks_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tracks_layout.addWidget(self.tracks_list)
        
        browse_button = QPushButton("Browse & Add Tracks")
        browse_button.clicked.connect(self.browse_tracks)
        tracks_layout.addWidget(browse_button)
        
        layout.addLayout(tracks_layout)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        confirm_button = QPushButton("Create")
        confirm_button.clicked.connect(self.confirm_creation)
        confirm_button.setDefault(True)
        buttons_layout.addWidget(confirm_button)
        
        layout.addLayout(buttons_layout)
        
        self.name_edit.setFocus()
        
    def browse_tracks(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            for file_path in files:
                if file_path not in self.tracks:
                    self.tracks.append(file_path)
                    filename = os.path.basename(file_path)
                    self.tracks_list.addItem(filename)
                    
    def confirm_creation(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a playlist name")
            self.name_edit.setFocus()
            return
            
        playlist = Playlist(title=name)
        for track_path in self.tracks:
            entry = PlaylistEntry(location=track_path)
            playlist.add_entry(entry)
            
        self.playlist_created.emit(name, playlist)
        self.accept()
```

#### File: `playlist_manager\playlist_edit_dialog.py`

```python
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QLabel, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal
from av_play import Playlist


class PlaylistEditDialog(QDialog):
    playlist_updated = Signal(str, str)
    
    def __init__(self, playlist_name, playlist, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Playlist")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(400, 150)
        self.original_name = playlist_name
        self.playlist = playlist
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter playlist name")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        layout.addStretch()
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.confirm_update)
        confirm_button.setDefault(True)
        buttons_layout.addWidget(confirm_button)
        
        layout.addLayout(buttons_layout)
        
    def load_data(self):
        self.name_edit.setText(self.original_name)
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        
    def confirm_update(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a playlist name")
            self.name_edit.setFocus()
            return
            
        self.playlist.title = name
        
        self.playlist_updated.emit(self.original_name, name)
        self.accept()
```

#### File: `playlist_manager\playlist_selection_dialog.py`

```python
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QPushButton, QLabel, QMessageBox)
from PySide6.QtCore import Qt, Signal
from av_play import PlaylistManager


class PlaylistSelectionDialog(QDialog):
    playlist_selected = Signal(str)
    
    def __init__(self, playlist_manager: PlaylistManager, parent=None):
        super().__init__(parent)
        self.playlist_manager = playlist_manager
        self.setWindowTitle("Select Playlist")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(400, 300)
        self.setup_ui()
        self.load_playlists()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("Select a playlist to add the file to:")
        layout.addWidget(label)
        
        self.playlists_list = QListWidget()
        self.playlists_list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.playlists_list)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        select_button = QPushButton("Select")
        select_button.clicked.connect(self.accept_selection)
        select_button.setDefault(True)
        buttons_layout.addWidget(select_button)
        
        layout.addLayout(buttons_layout)
        
    def load_playlists(self):
        self.playlists_list.clear()
        playlists = self.playlist_manager.list_playlists()
        
        if not playlists:
            no_playlists_label = QLabel("No playlists available. Create a playlist first.")
            no_playlists_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_playlists_label.setStyleSheet("color: gray; font-style: italic;")
        else:
            for playlist_name in playlists:
                self.playlists_list.addItem(playlist_name)
                
    def accept_selection(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            playlist_name = current_item.text()
            self.playlist_selected.emit(playlist_name)
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "Please select a playlist")
            
    def get_selected_playlist(self):
        current_item = self.playlists_list.currentItem()
        return current_item.text() if current_item else None
```

#### File: `playlist_manager\playlist_view.py`

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QMenu, QApplication,
                               QMessageBox, QFileDialog)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from gui_controls.list_control import Listctrl
from av_play import Playlist, PlaylistEntry


class PlaylistView(QWidget):
    play_playlist_signal = Signal(Playlist)
    
    def __init__(self, parent=None, play_callback=None):
        super().__init__(parent)
        self.play_callback = play_callback
        self.current_playlist = None
        self.setup_ui()
        self.setup_context_menu()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.list_ctrl = Listctrl(self)
        self.list_ctrl.column(0, "File Name")
        self.list_ctrl.column(1, "Title")
        self.list_ctrl.column(2, "Artist")
        self.list_ctrl.column(3, "Album")
        
        self.list_ctrl.itemDoubleClicked.connect(self.on_item_activated)
        self.list_ctrl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_ctrl.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.list_ctrl)
        
    def setup_context_menu(self):
        self.context_menu = QMenu(self)
        
        add_tracks_action = QAction("Add Tracks", self)
        add_tracks_action.triggered.connect(self.add_tracks)
        self.context_menu.addAction(add_tracks_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected)
        self.context_menu.addAction(delete_action)
        
        self.context_menu.addSeparator()
        
        clear_action = QAction("Clear Tracks", self)
        clear_action.triggered.connect(self.clear_tracks)
        self.context_menu.addAction(clear_action)
        
    def show_context_menu(self, position):
        self.context_menu.exec(self.list_ctrl.mapToGlobal(position))
        
    def set_playlist(self, playlist):
        self.current_playlist = playlist
        self.refresh_view()
        
    def refresh_view(self):
        self.list_ctrl.clearAll()
        
        if not self.current_playlist:
            return
            
        self.list_ctrl.column(0, "File Name")
        self.list_ctrl.column(1, "Title")
        self.list_ctrl.column(2, "Artist")
        self.list_ctrl.column(3, "Album")
        
        for entry in self.current_playlist.entries:
            import os
            filename = os.path.basename(entry.location)
            title = entry.title or ""
            artist = entry.artist or ""
            album = entry.album or ""
            
            self.list_ctrl.appendRow({
                "0": filename,
                "1": title,
                "2": artist,
                "3": album
            })
            
    def on_item_activated(self, item):
        if self.current_playlist and self.play_callback:
            self.play_callback(self.current_playlist)
        elif self.current_playlist:
            self.play_playlist_signal.emit(self.current_playlist)
            
    def add_tracks(self):
        if not self.current_playlist:
            QMessageBox.warning(self, "Warning", "No playlist selected")
            return
            
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            for file_path in files:
                entry = PlaylistEntry(location=file_path)
                self.current_playlist.add_entry(entry)
            self.refresh_view()
            
    def delete_selected(self):
        if not self.current_playlist:
            return
            
        current_row = self.list_ctrl.getCurrentRowIndex()
        if current_row > 0:
            index = current_row - 1
            self.current_playlist.remove_entry(index)
            self.refresh_view()
            
    def clear_tracks(self):
        if not self.current_playlist:
            return
            
        reply = QMessageBox.question(self, "Confirm", "Clear all tracks?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.current_playlist.clear()
            self.refresh_view()
```

#### File: `playlist_manager\playlists_widget.py`

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QSplitter, QLabel, QMessageBox,
                               QListWidgetItem)
from PySide6.QtCore import Qt, Signal
from .playlist_view import PlaylistView
from .playlist_create_dialog import PlaylistCreateDialog
from .playlist_edit_dialog import PlaylistEditDialog
from av_play import Playlist, PlaylistManager
import os
import json

from utilities.functions import get_app_path


class PlaylistsWidget(QWidget):
    playlist_selected = Signal(Playlist)
    
    def __init__(self, parent=None, play_callback=None):
        super().__init__(parent)
        self.play_callback = play_callback
        self.playlist_manager = PlaylistManager()
        self.setup_ui()
        self.setup_data_paths()
        self.load_playlists_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Playlists"))
        header_layout.addStretch()
        
        self.create_button = QPushButton("Create Playlist")
        self.create_button.clicked.connect(self.create_playlist)
        header_layout.addWidget(self.create_button)
        
        layout.addLayout(header_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.playlists_list = QListWidget()
        self.playlists_list.setMaximumWidth(250)
        self.playlists_list.itemClicked.connect(self.on_playlist_selected)
        self.playlists_list.itemDoubleClicked.connect(self.edit_playlist)
        splitter.addWidget(self.playlists_list)
        
        self.playlist_view = PlaylistView(play_callback=self.play_callback)
        splitter.addWidget(self.playlist_view)
        
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
    def setup_data_paths(self):
        app_dir = get_app_path()
        self.data_dir = os.path.join(app_dir, "data")
        self.playlists_dir = os.path.join(self.data_dir, "playlists")
        self.playlists_json_path = os.path.join(self.data_dir, "playlists.json")
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.playlists_dir, exist_ok=True)
        
    def load_playlists_data(self):
        if os.path.exists(self.playlists_json_path):
            try:
                with open(self.playlists_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for playlist_info in data.get("playlists", []):
                    name = playlist_info.get("name")
                    file_path = playlist_info.get("file_path")
                    
                    if name and file_path and os.path.exists(file_path):
                        try:
                            playlist = self.playlist_manager.load_playlist(name, file_path)
                            self.add_playlist_to_list(name)
                        except Exception as e:
                            print(f"Error loading playlist {name}: {e}")
                            
            except Exception as e:
                print(f"Error loading playlists data: {e}")
                
    def save_playlists_data(self):
        try:
            playlists_data = []
            
            for i in range(self.playlists_list.count()):
                item = self.playlists_list.item(i)
                name = item.text()
                playlist = self.playlist_manager.get_playlist(name)
                
                if playlist:
                    file_path = os.path.join(self.playlists_dir, f"{name}.json")
                    self.playlist_manager.save_playlist(name, file_path)
                    
                    playlist_info = {
                        "name": name,
                        "file_path": file_path
                    }
                    playlists_data.append(playlist_info)
                    
            data = {"playlists": playlists_data}
            
            with open(self.playlists_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving playlists data: {e}")
            
    def add_playlist_to_list(self, name):
        item = QListWidgetItem(name)
        self.playlists_list.addItem(item)
        
    def create_playlist(self):
        dialog = PlaylistCreateDialog(self)
        dialog.playlist_created.connect(self.on_playlist_created)
        dialog.exec()
        
    def on_playlist_created(self, name, playlist):
        if name in [self.playlists_list.item(i).text() for i in range(self.playlists_list.count())]:
            QMessageBox.warning(self, "Warning", f"Playlist '{name}' already exists")
            return
            
        self.playlist_manager.playlists[name] = playlist
        self.add_playlist_to_list(name)
        self.save_playlists_data()
        
        for i in range(self.playlists_list.count()):
            if self.playlists_list.item(i).text() == name:
                self.playlists_list.setCurrentRow(i)
                self.on_playlist_selected(self.playlists_list.item(i))
                break
                
    def edit_playlist(self, item):
        name = item.text()
        playlist = self.playlist_manager.get_playlist(name)
        
        if playlist:
            dialog = PlaylistEditDialog(name, playlist, self)
            dialog.playlist_updated.connect(self.on_playlist_updated)
            dialog.exec()
            
    def on_playlist_updated(self, old_name, new_name):
        if old_name != new_name:
            if new_name in [self.playlists_list.item(i).text() for i in range(self.playlists_list.count())]:
                QMessageBox.warning(self, "Warning", f"Playlist '{new_name}' already exists")
                return
                
            playlist = self.playlist_manager.get_playlist(old_name)
            if playlist:
                self.playlist_manager.playlists[new_name] = playlist
                del self.playlist_manager.playlists[old_name]
                
                for i in range(self.playlists_list.count()):
                    if self.playlists_list.item(i).text() == old_name:
                        self.playlists_list.item(i).setText(new_name)
                        break
                        
        self.save_playlists_data()
        
    def on_playlist_selected(self, item):
        if item:
            name = item.text()
            playlist = self.playlist_manager.get_playlist(name)
            if playlist:
                self.playlist_view.set_playlist(playlist)
                self.playlist_selected.emit(playlist)
                
    def get_current_playlist(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            name = current_item.text()
            return self.playlist_manager.get_playlist(name)
        return None
        
    def refresh_current_playlist(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            self.on_playlist_selected(current_item)
```

<a name="directory-tools"></a>
### Directory: `tools`


#### File: `tools\__init__.py`

```python

```

#### File: `tools\batch_converter_ui.py`

```python
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QComboBox, QProgressDialog, QMessageBox, QListWidget,
    QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from .ffmpeg_handler import FFmpegHandler
from ffmpeg import FFmpegError, Progress
from .utils import (
    get_common_sample_rates, get_common_audio_bitrates, get_common_video_bitrates,
    get_audio_formats_map, get_video_formats_map, get_container_from_format
)

class FFmpegBatchThread(QThread):
    file_progress = Signal(str)
    overall_progress = Signal(int, int, str)
    finished = Signal()
    error = Signal(str, str)

    def __init__(self, files, output_dir, conversion_options):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.options = conversion_options
        self._is_running = True

    def run(self):
        total_files = len(self.files)
        for i, input_file in enumerate(self.files):
            if not self._is_running:
                break
            
            try:
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                self.overall_progress.emit(i, total_files, base_name)
                
                codec = self.options['codec']
                extension = self.options['extension']
                output_file = os.path.join(self.output_dir, f"{base_name}{extension}")

                ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
                
                output_opts = {}
                if self.options['type'] == 'video':
                    output_opts['codec:v'] = codec
                else: # audio
                    output_opts['codec:a'] = codec
                    if self.options.get('sample_rate'):
                        output_opts['ar'] = self.options['sample_rate']
                
                if self.options.get('bitrate'):
                    bitrate_key = 'b:v' if self.options['type'] == 'video' else 'b:a'
                    output_opts[bitrate_key] = self.options['bitrate']

                ffmpeg.input(input_file).output(output_file, **output_opts)

                @ffmpeg.on("progress")
                def on_progress(progress: Progress):
                    self.file_progress.emit(f"Time: {progress.time}, Speed: {progress.speed:.2f}x")

                ffmpeg.execute()
            except FFmpegError as e:
                self.error.emit(input_file, e.message)
                continue
            except Exception as e:
                self.error.emit(input_file, str(e))
                continue
        
        if self._is_running:
            self.overall_progress.emit(total_files, total_files, "Done")
            self.finished.emit()

    def stop(self):
        self._is_running = False


class BatchConverterUI(QWidget):
    def __init__(self):
        super().__init__()
        self.thread: FFmpegBatchThread | None = None
        self.progress_dialog: QProgressDialog | None = None
        
        self.main_layout = QVBoxLayout(self)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.main_layout.addWidget(self.file_list)

        button_layout = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files")
        self.add_files_button.clicked.connect(self.add_files)
        self.remove_files_button = QPushButton("Remove Selected")
        self.remove_files_button.clicked.connect(self.remove_files)
        button_layout.addWidget(self.add_files_button)
        button_layout.addWidget(self.remove_files_button)
        self.main_layout.addLayout(button_layout)

        self.setup_conversion_options()

        self.start_button = QPushButton("Start Batch Conversion")
        self.start_button.clicked.connect(self.start_conversion)
        self.main_layout.addWidget(self.start_button)

    def setup_conversion_options(self):
        options_group = QGroupBox("Conversion Options")
        options_layout = QVBoxLayout()

        self.type_combo = QComboBox()
        self.type_combo.setAccessibleName("Conversion type (audio or video)")
        self.type_combo.addItems(["Audio", "Video"])
        self.type_combo.currentIndexChanged.connect(self.update_format_combo)
        options_layout.addWidget(QLabel("Conversion Type:"))
        options_layout.addWidget(self.type_combo)

        self.format_combo = QComboBox()
        self.format_combo.setAccessibleName("Target format")
        options_layout.addWidget(QLabel("Target Format:"))
        options_layout.addWidget(self.format_combo)

        self.samplerate_combo = QComboBox()
        self.samplerate_combo.setAccessibleName("Audio sample rate")
        self.samplerate_combo.setEditable(True)
        self.samplerate_combo.addItems(get_common_sample_rates())
        self.samplerate_combo.setCurrentText("44100")
        options_layout.addWidget(QLabel("Sample Rate (Audio):"))
        options_layout.addWidget(self.samplerate_combo)

        self.bitrate_combo = QComboBox()
        self.bitrate_combo.setAccessibleName("Target bitrate")
        self.bitrate_combo.setEditable(True)
        options_layout.addWidget(QLabel("Bitrate:"))
        options_layout.addWidget(self.bitrate_combo)
        
        options_group.setLayout(options_layout)
        self.main_layout.addWidget(options_group)
        self.update_format_combo(0)

    def update_format_combo(self, index):
        self.format_combo.clear()
        self.bitrate_combo.clear()
        if index == 0: # Audio
            self.audio_formats = get_audio_formats_map()
            self.format_combo.addItems(list(self.audio_formats.keys()))
            self.bitrate_combo.addItems(get_common_audio_bitrates())
            self.bitrate_combo.setCurrentText("192k")
            self.samplerate_combo.setEnabled(True)
        else: # Video
            self.video_formats = get_video_formats_map()
            self.format_combo.addItems(list(self.video_formats.keys()))
            self.bitrate_combo.addItems(get_common_video_bitrates())
            self.bitrate_combo.setCurrentText("4000k")
            self.samplerate_combo.setEnabled(False)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to convert")
        self.file_list.addItems(files)

    def remove_files(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def start_conversion(self):
        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not files:
            QMessageBox.warning(self, "Warning", "No files to convert.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return

        conv_type = self.type_combo.currentText().lower()
        format_name = self.format_combo.currentText()
        
        options = {'type': conv_type}
        if conv_type == 'audio':
            options['codec'] = self.audio_formats[format_name]
            options['sample_rate'] = self.samplerate_combo.currentText()
            options['bitrate'] = self.bitrate_combo.currentText()
        else:
            options['codec'] = self.video_formats[format_name]
            options['bitrate'] = self.bitrate_combo.currentText()
        options['extension'] = get_container_from_format(format_name)

        self.progress_dialog = QProgressDialog("Batch Converting...", "Cancel", 0, len(files), self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

        self.thread = FFmpegBatchThread(files, output_dir, options)
        self.thread.overall_progress.connect(self.update_progress)
        self.thread.file_progress.connect(self.update_file_progress)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.progress_dialog.canceled.connect(self.thread.stop)
        self.thread.start()
        self.progress_dialog.show()

    def update_progress(self, value, total, filename):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(f"Converting file {value+1} of {total}: {filename}")
            self.progress_dialog.setValue(value)

    def update_file_progress(self, progress_str):
        if self.progress_dialog:
            current_text = self.progress_dialog.labelText()
            base_text = current_text.split("...")[0]
            self.progress_dialog.setLabelText(f"{base_text}... {progress_str}")

    def on_finished(self):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.setValue(self.progress_dialog.maximum())
            QMessageBox.information(self, "Success", "Batch conversion completed.")
            self.progress_dialog.close()

    def on_error(self, filename, message):
        error_msg = f"Failed to convert {os.path.basename(filename)}:\n{message}"
        QMessageBox.warning(self, "Conversion Error", error_msg)
```

#### File: `tools\extractor_ui.py`

```python
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QComboBox, QProgressDialog, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from .ffmpeg_handler import FFmpegHandler
from ffmpeg import FFmpegError, Progress
from .utils import get_audio_formats_map, get_container_from_format

class FFmpegTaskThread(QThread):
    progress = Signal(Progress)
    stderr = Signal(str)
    finished = Signal(bytes)
    error = Signal(str)

    def __init__(self, ffmpeg_instance):
        super().__init__()
        self.ffmpeg = ffmpeg_instance

    def run(self):
        try:
            @self.ffmpeg.on("progress")
            def on_progress(prog: Progress):
                self.progress.emit(prog)
            
            @self.ffmpeg.on("stderr")
            def on_stderr(line: str):
                self.stderr.emit(line)

            output = self.ffmpeg.execute()
            self.finished.emit(output)
        except FFmpegError as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(str(e))

class ExtractorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.thread: FFmpegTaskThread | None = None
        self.progress_dialog: QProgressDialog | None = None

        self.main_layout = QVBoxLayout(self)

        self.input_path = QLineEdit()
        self.input_path.setAccessibleName("Video file for extraction")
        self.browse_button = QPushButton("Browse Video")
        self.browse_button.clicked.connect(self.browse_video)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Video File:"))
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(self.browse_button)
        self.main_layout.addLayout(input_layout)

        self.setup_audio_extraction_group()
        self.setup_image_extraction_group()

        self.main_layout.addStretch()

    def setup_audio_extraction_group(self):
        audio_group = QGroupBox("Audio Extraction")
        audio_layout = QVBoxLayout()

        self.audio_format_combo = QComboBox()
        self.audio_format_combo.setAccessibleName("Audio output format")
        self.audio_formats = get_audio_formats_map()
        self.audio_format_combo.addItems(list(self.audio_formats.keys()))
        audio_layout.addWidget(QLabel("Output Format:"))
        audio_layout.addWidget(self.audio_format_combo)

        time_layout = QHBoxLayout()
        self.audio_start_time = QLineEdit("00:00:00")
        self.audio_start_time.setAccessibleName("Audio extraction start time")
        self.audio_end_time = QLineEdit()
        self.audio_end_time.setPlaceholderText("e.g., 00:01:30 or 90")
        self.audio_end_time.setAccessibleName("Audio extraction end time or duration")
        time_layout.addWidget(QLabel("Start Time (HH:MM:SS):"))
        time_layout.addWidget(self.audio_start_time)
        time_layout.addWidget(QLabel("End Time or Duration (optional):"))
        time_layout.addWidget(self.audio_end_time)
        audio_layout.addLayout(time_layout)

        self.extract_audio_button = QPushButton("Extract Audio")
        self.extract_audio_button.clicked.connect(self.extract_audio)
        audio_layout.addWidget(self.extract_audio_button)
        
        audio_group.setLayout(audio_layout)
        self.main_layout.addWidget(audio_group)

    def setup_image_extraction_group(self):
        image_group = QGroupBox("Image Extraction")
        image_layout = QVBoxLayout()

        self.image_mode_combo = QComboBox()
        self.image_mode_combo.setAccessibleName("Image extraction mode")
        self.image_mode_combo.addItems(["Extract All Frames", "Extract Range", "Extract 1 Image Per Second"])
        image_layout.addWidget(QLabel("Extraction Mode:"))
        image_layout.addWidget(self.image_mode_combo)

        time_layout = QHBoxLayout()
        self.image_start_time = QLineEdit("00:00:00")
        self.image_start_time.setAccessibleName("Image extraction start time")
        self.image_duration = QLineEdit("5")
        self.image_duration.setAccessibleName("Image extraction duration in seconds")
        time_layout.addWidget(QLabel("Start Time (HH:MM:SS):"))
        time_layout.addWidget(self.image_start_time)
        time_layout.addWidget(QLabel("Duration (seconds):"))
        time_layout.addWidget(self.image_duration)
        image_layout.addLayout(time_layout)

        self.extract_images_button = QPushButton("Extract Images")
        self.extract_images_button.clicked.connect(self.extract_images)
        image_layout.addWidget(self.extract_images_button)

        image_group.setLayout(image_layout)
        self.main_layout.addWidget(image_group)

    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File")
        if file_path:
            self.input_path.setText(file_path)

    def run_ffmpeg_task(self, ffmpeg_instance, title):
        self.progress_dialog = QProgressDialog(title, "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

        self.thread = FFmpegTaskThread(ffmpeg_instance)
        self.thread.progress.connect(self.update_progress)
        self.thread.stderr.connect(self.update_stderr)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.progress_dialog.canceled.connect(self.thread.terminate)
        self.thread.start()
        self.progress_dialog.show()

    def extract_audio(self):
        input_video = self.input_path.text()
        if not input_video or not os.path.exists(input_video):
            QMessageBox.warning(self, "Warning", "Please select a valid input video file.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return

        format_name = self.audio_format_combo.currentText()
        codec = self.audio_formats[format_name]
        extension = get_container_from_format(format_name)
        output_path = os.path.join(output_dir, f"extracted_audio{extension}")

        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        
        input_options = {}
        start_time = self.audio_start_time.text()
        if start_time and start_time != "00:00:00":
            input_options['ss'] = start_time
        
        output_options = {'codec:a': codec, 'vn': None}
        end_time_or_duration = self.audio_end_time.text()
        if end_time_or_duration:
            if ':' in end_time_or_duration:
                output_options['to'] = end_time_or_duration
            else:
                output_options['t'] = end_time_or_duration

        ffmpeg.input(input_video, **input_options).output(output_path, **output_options)
        self.run_ffmpeg_task(ffmpeg, "Extracting Audio...")

    def extract_images(self):
        input_video = self.input_path.text()
        if not input_video or not os.path.exists(input_video):
            QMessageBox.warning(self, "Warning", "Please select a valid input video file.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory for Images")
        if not output_dir:
            return

        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        mode = self.image_mode_combo.currentIndex()
        output_pattern = os.path.join(output_dir, "frame-%04d.png")

        input_options = {}
        output_options = {}

        if mode == 0: # All
            ffmpeg.input(input_video).output(output_pattern, **output_options)
        elif mode == 1: # Range
            start = self.image_start_time.text()
            duration = self.image_duration.text()
            input_options['ss'] = start
            output_options['t'] = duration
            ffmpeg.input(input_video, **input_options).output(output_pattern, **output_options)
        elif mode == 2: # 1 image per second
            output_options['vf'] = 'fps=1'
            ffmpeg.input(input_video).output(output_pattern, **output_options)

        self.run_ffmpeg_task(ffmpeg, "Extracting Images...")

    def update_progress(self, progress: Progress):
        if self.progress_dialog:
            progress_text = (
                f"Frame: {progress.frame} | "
                f"Time: {progress.time} | "
                f"Bitrate: {progress.bitrate:.2f} kbps | "
                f"Speed: {progress.speed:.2f}x"
            )
            self.progress_dialog.setLabelText(progress_text)
    
    def update_stderr(self, line: str):
        if self.progress_dialog and "frame=" not in self.progress_dialog.labelText():
             self.progress_dialog.setLabelText(line)

    def on_finished(self, output):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.information(self, "Success", "Extraction completed successfully.")

    def on_error(self, message):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.critical(self, "Error", f"An error occurred: {message}")
```

#### File: `tools\ffmpeg_handler.py`

```python
import os
import shutil
from pyffmpeg import FFmpeg as FFmpegDownloader
from ffmpeg import FFmpeg
from ffmpeg.asyncio import FFmpeg as AsyncFFmpeg

from utilities.functions import get_app_path, get_parent_dir

class FFmpegHandler:
    _ffmpeg_path: str | None = None
    _ffprobe_path: str | None = None

    @staticmethod
    def get_ffmpeg_binary():
        if FFmpegHandler._ffmpeg_path is not None:
            return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path


        base_dir = get_parent_dir()
        bin_dir = os.path.join(base_dir, 'bin')
        ffmpeg_exe_name = 'ffmpeg' + ('.exe' if os.name == 'nt' else '')
        ffprobe_exe_name = 'ffprobe' + ('.exe' if os.name == 'nt' else '')
        local_ffmpeg_path = os.path.join(bin_dir, ffmpeg_exe_name)
        local_ffprobe_path = os.path.join(bin_dir, ffprobe_exe_name)

        if not os.path.exists(local_ffmpeg_path):
            os.makedirs(bin_dir, exist_ok=True)
            
            try:
                downloader = FFmpegDownloader()
                temp_ffmpeg_path = downloader.get_ffmpeg_bin()
                shutil.copy2(temp_ffmpeg_path, local_ffmpeg_path)

                temp_dir = os.path.dirname(temp_ffmpeg_path)
                temp_ffprobe_path = os.path.join(temp_dir, ffprobe_exe_name)
                if os.path.exists(temp_ffprobe_path):
                    shutil.copy2(temp_ffprobe_path, local_ffprobe_path)

            except Exception as e:
                FFmpegHandler._ffmpeg_path = "ffmpeg"
                FFmpegHandler._ffprobe_path = "ffprobe"
                return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

        FFmpegHandler._ffmpeg_path = local_ffmpeg_path
        FFmpegHandler._ffprobe_path = local_ffprobe_path
        
        return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

    @staticmethod
    def create_ffmpeg_instance():
        ffmpeg_path, _ = FFmpegHandler.get_ffmpeg_binary()
        return FFmpeg(executable=str(ffmpeg_path))

    @staticmethod
    def create_ffprobe_instance():
        _, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        if not ffprobe_path or not os.path.exists(ffprobe_path):
             return FFmpeg(executable="ffprobe")
        return FFmpeg(executable=str(ffprobe_path))

    @staticmethod
    def create_async_ffmpeg_instance():
        ffmpeg_path, _ = FFmpegHandler.get_ffmpeg_binary()
        return AsyncFFmpeg(executable=str(ffmpeg_path))
```

#### File: `tools\tag_editor_ui.py`

```python
import os
import music_tag
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QListWidget, QGridLayout, QMessageBox, QTextEdit
)

class TagEditorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.opened_files = {}
        self.current_file = None

        self.main_layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        self.file_list = QListWidget()
        self.file_list.currentItemChanged.connect(self.display_tags)
        left_panel.addWidget(self.file_list)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Files")
        self.add_button.clicked.connect(self.add_files)
        self.remove_button = QPushButton("Remove File")
        self.remove_button.clicked.connect(self.remove_file)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        left_panel.addLayout(button_layout)

        self.save_button = QPushButton("Save Current File")
        self.save_button.clicked.connect(self.save_current)
        self.save_all_button = QPushButton("Save All Files")
        self.save_all_button.clicked.connect(self.save_all)
        left_panel.addWidget(self.save_button)
        left_panel.addWidget(self.save_all_button)

        right_panel = QVBoxLayout()
        self.grid_layout = QGridLayout()
        self.tag_widgets = {}
        
        tags_to_display = [
            'tracktitle', 'artist', 'album', 'albumartist', 'composer',
            'tracknumber', 'totaltracks', 'discnumber', 'totaldiscs',
            'genre', 'year', 'comment'
        ]

        row = 0
        for tag in tags_to_display:
            label = QLabel(tag.replace('_', ' ').title() + ":")
            edit = QLineEdit()
            edit.setAccessibleName(f"{tag.replace('_', ' ').title()} tag editor")
            self.grid_layout.addWidget(label, row, 0)
            self.grid_layout.addWidget(edit, row, 1)
            self.tag_widgets[tag] = edit
            edit.textChanged.connect(self.update_tag_data)
            row += 1

        self.lyrics_edit = QTextEdit()
        self.lyrics_edit.setAccessibleName("Lyrics tag editor")
        self.grid_layout.addWidget(QLabel("Lyrics:"), row, 0)
        self.grid_layout.addWidget(self.lyrics_edit, row, 1)
        self.tag_widgets['lyrics'] = self.lyrics_edit
        self.lyrics_edit.textChanged.connect(self.update_tag_data)

        right_panel.addLayout(self.grid_layout)

        self.main_layout.addLayout(left_panel, 1)
        self.main_layout.addLayout(right_panel, 2)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Audio Files",
            filter="Audio Files (*.mp3 *.flac *.m4a *.aac *.aiff *.dsf *.ogg *.opus *.wav *.wv)")
        for file_path in files:
            if file_path not in self.opened_files:
                try:
                    self.opened_files[file_path] = music_tag.load_file(file_path)
                    self.file_list.addItem(os.path.basename(file_path))
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not load {file_path}: {e}")

    def remove_file(self):
        current_item = self.file_list.currentItem()
        if current_item:
            file_path_to_remove = self.get_path_from_item(current_item)
            if file_path_to_remove in self.opened_files:
                del self.opened_files[file_path_to_remove]
            self.file_list.takeItem(self.file_list.row(current_item))
            self.clear_display()

    def get_path_from_item(self, item):
        if not item:
            return None
        filename = item.text()
        for path, file_obj in self.opened_files.items():
            if os.path.basename(path) == filename:
                # This is a fallback, but a more robust way is needed if filenames are not unique
                # For this app, we assume they are unique in the list
                return path
        return None

    def display_tags(self, current_item, previous_item):
        if not current_item:
            self.clear_display()
            return
            
        file_path = self.get_path_from_item(current_item)
        if file_path:
            self.current_file = self.opened_files[file_path]
            for tag, widget in self.tag_widgets.items():
                if self.current_file.get(tag):
                    value = self.current_file[tag].value
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QTextEdit):
                        widget.setPlainText(str(value))
                else:
                    if isinstance(widget, QLineEdit):
                        widget.clear()
                    elif isinstance(widget, QTextEdit):
                        widget.clear()

    def clear_display(self):
        self.current_file = None
        for widget in self.tag_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QTextEdit):
                widget.clear()
    
    def update_tag_data(self):
        if not self.current_file:
            return

        sender = self.sender()
        for tag, widget in self.tag_widgets.items():
            if widget is sender:
                if isinstance(widget, QLineEdit):
                    self.current_file[tag] = widget.text()
                elif isinstance(widget, QTextEdit):
                    self.current_file[tag] = widget.toPlainText()
                break

    def save_current(self):
        if self.current_file:
            try:
                self.current_file.save()
                QMessageBox.information(self, "Success", "Tags saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save tags: {e}")

    def save_all(self):
        try:
            for f in self.opened_files.values():
                f.save()
            QMessageBox.information(self, "Success", "All files saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving all files: {e}")
```

#### File: `tools\thumbnail_generator_ui.py`

```python
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QComboBox, QProgressDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from .ffmpeg_handler import FFmpegHandler
from ffmpeg import FFmpegError, Progress

class FFmpegTaskThread(QThread):
    progress = Signal(Progress)
    finished = Signal(bytes)
    error = Signal(str)

    def __init__(self, ffmpeg_instance):
        super().__init__()
        self.ffmpeg = ffmpeg_instance

    def run(self):
        try:
            @self.ffmpeg.on("progress")
            def on_progress(prog: Progress):
                self.progress.emit(prog)

            output = self.ffmpeg.execute()
            self.finished.emit(output)
        except FFmpegError as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(str(e))

class ThumbnailGeneratorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.thread: FFmpegTaskThread | None = None
        self.progress_dialog: QProgressDialog | None = None
        
        self.main_layout = QVBoxLayout(self)

        self.input_path = QLineEdit()
        self.input_path.setAccessibleName("Video file input path")
        self.browse_button = QPushButton("Browse Video")
        self.browse_button.clicked.connect(self.browse_video)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Video File:"))
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(self.browse_button)
        self.main_layout.addLayout(input_layout)

        self.mode_combo = QComboBox()
        self.mode_combo.setAccessibleName("Thumbnail generation mode")
        self.mode_combo.addItems([
            "Manual Frame Selection",
            "Automatic Thumbnail Filter",
            "Select from Scene Changes"
        ])
        self.mode_combo.currentIndexChanged.connect(self.update_options)
        self.main_layout.addWidget(QLabel("Generation Mode:"))
        self.main_layout.addWidget(self.mode_combo)

        self.manual_options_widget = QWidget()
        manual_layout = QVBoxLayout(self.manual_options_widget)
        manual_layout.setContentsMargins(0,0,0,0)
        manual_layout.addWidget(QLabel("Timestamp (HH:MM:SS):"))
        self.timestamp_edit = QLineEdit("00:00:15")
        self.timestamp_edit.setAccessibleName("Timestamp for manual frame selection")
        manual_layout.addWidget(self.timestamp_edit)
        self.main_layout.addWidget(self.manual_options_widget)

        self.scene_options_widget = QWidget()
        scene_layout = QVBoxLayout(self.scene_options_widget)
        scene_layout.setContentsMargins(0,0,0,0)
        scene_layout.addWidget(QLabel("Number of Images to Generate:"))
        self.num_frames_edit = QLineEdit("5")
        self.num_frames_edit.setAccessibleName("Number of images to generate from scene changes")
        scene_layout.addWidget(self.num_frames_edit)
        scene_layout.addWidget(QLabel("Scene Change Threshold (0.0-1.0):"))
        self.scene_threshold_edit = QLineEdit("0.4")
        self.scene_threshold_edit.setAccessibleName("Scene change detection threshold")
        scene_layout.addWidget(self.scene_threshold_edit)
        self.main_layout.addWidget(self.scene_options_widget)

        self.generate_button = QPushButton("Generate Thumbnail(s)")
        self.generate_button.clicked.connect(self.generate_thumbnail)
        self.main_layout.addWidget(self.generate_button)

        self.main_layout.addStretch()

        self.update_options(0)

    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File")
        if file_path:
            self.input_path.setText(file_path)

    def update_options(self, index):
        self.manual_options_widget.setVisible(index == 0)
        self.scene_options_widget.setVisible(index == 2)

    def generate_thumbnail(self):
        input_video = self.input_path.text()
        if not input_video or not os.path.exists(input_video):
            QMessageBox.warning(self, "Warning", "Please select a valid input video file.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return

        ffmpeg = FFmpegHandler.create_ffmpeg_instance()
        ffmpeg.option("y")

        mode = self.mode_combo.currentIndex()
        
        try:
            output_options = {}
            if mode == 0: # Manual
                timestamp = self.timestamp_edit.text()
                output_path = os.path.join(output_dir, "thumbnail.png")
                output_options['frames:v'] = 1
                ffmpeg.input(input_video, ss=timestamp).output(output_path, **output_options)
            elif mode == 1: # Auto
                output_path = os.path.join(output_dir, "thumbnail_auto.png")
                output_options['vf'] = "thumbnail"
                output_options['frames:v'] = 1
                ffmpeg.input(input_video).output(output_path, **output_options)
            elif mode == 2: # Scene
                num_frames = self.num_frames_edit.text()
                threshold = self.scene_threshold_edit.text()
                output_pattern = os.path.join(output_dir, "scene-%02d.png")
                output_options['vf'] = f"select=gt(scene\\,{threshold})"
                output_options['vsync'] = "vfr"
                output_options['frames:v'] = int(num_frames)
                ffmpeg.input(input_video).output(output_pattern, **output_options)

            self.progress_dialog = QProgressDialog("Starting generation...", "Cancel", 0, 0, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            
            self.thread = FFmpegTaskThread(ffmpeg)
            self.thread.progress.connect(self.update_progress)
            self.thread.finished.connect(self.on_finished)
            self.thread.error.connect(self.on_error)
            self.progress_dialog.canceled.connect(self.thread.terminate)
            self.thread.start()
            self.progress_dialog.show()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start process: {e}")

    def update_progress(self, progress: Progress):
        if self.progress_dialog:
            progress_text = (
                f"Frame: {progress.frame} | "
                f"Time: {progress.time} | "
                f"Bitrate: {progress.bitrate:.2f} kbps | "
                f"Speed: {progress.speed:.2f}x"
            )
            self.progress_dialog.setLabelText(progress_text)

    def on_finished(self, output):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.information(self, "Success", "Thumbnail generation completed successfully.")

    def on_error(self, message):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.critical(self, "Error", f"An error occurred: {message}")
```

#### File: `tools\utils.py`

```python
def get_common_sample_rates():
    return ["8000", "11025", "16000", "22050", "32000", "44100", "48000", "96000"]

def get_common_audio_bitrates():
    return ["64k", "96k", "128k", "192k", "256k", "320k"]

def get_common_video_bitrates():
    return ["500k", "1000k", "2000k", "4000k", "6000k", "8000k"]

def get_pcm_formats():
    return ["pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le"]

def get_audio_formats_map():
    return {
        "MP3": "libmp3lame",
        "AAC": "aac",
        "FLAC": "flac",
        "WAV": "pcm_s16le",
        "Opus": "libopus",
        "Vorbis": "libvorbis",
    }

def get_video_formats_map():
    return {
        "MP4 (H.264)": "libx264",
        "MKV (H.264)": "libx264",
        "WEBM (VP9)": "libvpx-vp9",
        "AVI (MPEG-4)": "mpeg4",
        "MOV (H.264)": "libx264",
    }

def get_container_from_format(format_name):
    containers = {
        "MP4 (H.264)": ".mp4",
        "MKV (H.264)": ".mkv",
        "WEBM (VP9)": ".webm",
        "AVI (MPEG-4)": ".avi",
        "MOV (H.264)": ".mov",
        "MP3": ".mp3",
        "AAC": ".aac",
        "FLAC": ".flac",
        "WAV": ".wav",
        "Opus": ".opus",
        "Vorbis": ".ogg",
    }
    return containers.get(format_name, "")
```

<a name="directory-utilities"></a>
### Directory: `utilities`


#### File: `utilities\__init__.py`

```python
from utilities.functions import *

```

#### File: `utilities\functions.py`

```python
import platform as pform
import ctypes
import binascii
import os, sys
import time, datetime as dt
import py_youtube, httpx
import subprocess as sp
import validators as vl
import pyperclip

from PySide6.QtCore import Qt as qt
from PySide6.QtCore import QUrl
from pathlib import Path

from utilities.util_structs import time_struct
from pynotifier import NotificationClient, Notification
from pynotifier.backends import platform



def copyText(text):
    if text != "":
        pyperclip.copy(text)


def convertSize(size):
    if int(size) >= 1048576: 
        cs =  size/1024 /1024
        return float(str(cs)[0:5])
    elif size <27:
        pass
    elif size >= 27 and size < 1048576:
        cs = size/1024
        return float(str(cs)[0:4])

def converttime(seconds):
    hours = int(seconds/3600)
    minutes = int((seconds - hours*3600) / 60)
    seconds = int(seconds - (hours*3600 + minutes*60))
    
    time_string = ""
    if hours != 0:
        time_string += "0" + str(hours) + ":" if hours < 10 else str(hours) + ":"
    if minutes != 0:
        time_string += "0" + str(minutes) + ":" if minutes <10 else str(minutes) + ":"
    if seconds != 0:
        time_string += "0" + str(seconds) if seconds < 10 else str(seconds)
    
    return time_string

def timeFrom(seconds):
    hours = int(seconds/3600)
    minutes = int((seconds - hours*3600) / 60)
    seconds = int(seconds - (hours*3600 + minutes*60))
    t = time_struct(hours,minutes,seconds)
    return t

def getFormat(path):
    return os.path.splitext(path)[1]


def datetime(time):
    from datetime import datetime as dt
    return dt.fromtimestamp(time)


def hexify(data):
    str_data = data.encode("utf-8")  # Encoded before hexlify
    hexData = binascii.hexlify(str_data).decode("utf-8")
    return hexData

def dehexify(data):
    byte_data = data#bytes.fromhex(data)  # Converted hex string to bytes
    str_data = binascii.unhexlify(byte_data).decode("utf-8")
    return str_data

def user_path():
    from os import path
    return path.expanduser("~")

def get_user_directories():
    userpath = user_path()
    folders = ["Desktop","Documents","Downloads","Music","Videos"]
    return [f"{userpath}/{folder}" for folder in folders if os.path.exists(f"{userpath}/{folder}")]


def fileProperties(filepath):
    pf = pform.system()
    if pf == "Windows":
        ctypes.windll.shell32.ShellExecuteW(None, "properties", filepath, None, None, 2)
    elif pf == "Linux":
        import subprocess
        subprocess.run(["xdg-open", filepath])
    import subprocess
    subprocess.Popen(["explorer", "/select,", filepath])


def notifyer(msg_title,msg):
    c = NotificationClient()
    c.register_backend(platform.Backend())
    notification = Notification(title=msg_title,message=msg)
    c.notify_all(notification)

def numberList(minx,maxx,mode):
    numlist = []
    for i in range(minx,maxx+1):
#        if i>=10 and mode=="1":
        if mode=="1":
            numlist.append(str(i))

        elif i<10 and mode=="2":
            numlist.append(str(0)+str(i))
        elif i>=10 and mode=="2":
            numlist.append(str(i))
    return numlist


def media_url(url):
    #return str(urllib.request.urlopen(urllib.request.Request(url)).info().get_filename)
    link = httpx.head(url,follow_redirects=True)
    return QUrl(str(link.url)).fileName()

def youtube_url(url):
    return py_youtube.Data(url).data()["title"]

def isValidURL(url):
    return  vl.url() == True

def network_check():
    return sp.call(['ping','-n','1','8.8.8.8'])


def open_explorer(path):
    sp.Popen(fr'explorer /select,"{path}"')

def is_frozen():
    return getattr(sys, 'frozen', False) or hasattr(sys, '__compiled__') or 'nuitka' in sys.executable.lower()

def get_app_path() -> str:
    if is_frozen():
        BASE_DIR = Path(sys.executable).parent
    else:
        BASE_DIR = Path(__file__).parent.parent
    return str(BASE_DIR)

def get_script_parent_dir():
    return Path(__file__).parent.parent.parent

def get_exe_parent_dir():
    return Path(sys.executable).parent

def get_parent_dir():
    return str(get_exe_parent_dir() if is_frozen() else get_script_parent_dir())
```

#### File: `utilities\media_utils.py`

```python
import os

def format_time(seconds: int) -> str:
    if not isinstance(seconds, (int, float)) or seconds < 0:
        seconds = 0
    
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    else:
        return f"{m:02d}:{s:02d}"

def seconds_to_microseconds(seconds: float) -> int:
    return int(seconds * 1_000_000)

def get_media_files_from_directory(directory: str, audio_formats: list, video_formats: list) -> list:
    media_files = []
    supported_exts = set(audio_formats + video_formats)
    
    try:
        for filename in sorted(os.listdir(directory)):
            ext = filename.split('.')[-1].lower()
            if ext in supported_exts:
                media_files.append(os.path.join(directory, filename))
    except (FileNotFoundError, PermissionError):
        pass
        
    return media_files
```

#### File: `utilities\util_gui.py`

```python
from PySide6.QtWidgets import QApplication, QWidget, QMenu, QMessageBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt as qt

def menuItem(menu:QMenu, item:str, method,parent:QWidget):
    menu_item = QAction(item,parent)
    menu_item.triggered.connect(method)
    menu.addAction(menu_item)

def contextMenu(widget:QWidget,method):
    widget.setContextMenuPolicy(qt.ContextMenuPolicy.CustomContextMenu)
    widget.customContextMenuRequested.connect(method)

def messageBox(title,message):
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec()

def hasFocus(object): return QApplication.focusObject() == object
```

#### File: `utilities\util_structs.py`

```python

class Segment:

    def __init__(self):
        self.beginning = -1
        self.end = ""
        self.active = False

    def erase(self):
        self.beginning,self.end = -1,""
        self.active = False

    def mark_start(self,value):
        self.beginning = int(value)
        if self.end != "": self.active = True
        if self.end != "" and self.beginning > self.end: self.erase()

    def mark_end(self,value):
        self.end= int(value)
        if self.beginning != -1: self.active = True
        if self.end < self.beginning: self.erase()


class time_struct:


    def __init__(self, hours, minutes, seconds):
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
```
