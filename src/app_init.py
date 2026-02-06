import os
import sys
import threading
import locale

from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont

def setup_environment():
    from utilities.functions import get_parent_dir
    os.environ["VLC_LIB_PATH"] = os.path.join(get_parent_dir(), "lib")
    os.environ["USE_VLC"] = "1"
    
    if getattr(sys, 'frozen', False):
        BASE_DIR = Path(sys.executable).parent
        os.environ['QT_PLUGIN_PATH'] = str(BASE_DIR / "PySide6" / "qt-plugins")
    else:
        BASE_DIR = Path(__file__).parent
    
    return BASE_DIR

def setup_application_style(app):
    from utilities.theme_manager import setup_theme
    app.setStyle('Fusion')
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    setup_theme(app)

def initialize_app_guard(cli_args):
    import app_guard
    app_instance = app_guard.AppGuard()
    app_instance.init("PlayForm", lambda: None, False)
    
    if not app_instance.is_primary_instance():
        if cli_args and len(cli_args) > 1:
            app_instance.send_msg_request("cli-args", cli_args[1])
        app_instance.focus_window("Play Form")
        app_instance.release()
        return None, True
    
    return app_instance, False

def initialize_modules(splash):
    splash.update_message("Loading configuration...")
    import app_config
    from app_config import key_config
    
    splash.update_message("Loading database...")
    import app_db
    
    splash.update_message("Initializing locale...")
    locale.setlocale(locale.LC_NUMERIC, 'C')
    
    splash.update_message("Loading key configuration...")
    key_config.load_keys()
    
    splash.update_message("Initializing speech engine...")
    from utilities.speech import speech_manager
    threading.Thread(target=speech_manager.init, daemon=True).start()
    
    splash.update_message("Loading speech configuration...")
    from app_config import load_speech_config
    load_speech_config()
    
    return app_db, key_config

def create_main_window(splash, cli_args):
    splash.update_message("Creating main window...")
    from gui.main_window import MainWindow
    window = MainWindow()
    
    if len(cli_args) > 1:
        QTimer.singleShot(100, lambda: window.play_file(cli_args[1]))
    
    return window

def setup_ipc_handlers(app_instance, window):
    import app_guard
    cli_args_msg = app_instance.create_ipc_msg(
        "cli-args",
        lambda data: QTimer.singleShot(0, lambda: window.cli_load_file(data))
    )
    app_instance.register_msg(cli_args_msg)

def setup_cleanup(app, app_instance, app_db):
    from utilities.functions import get_restart_flag, set_restart_flag, restart_app
    
    def release():
        if get_restart_flag():
            set_restart_flag(False)
            restart_app()
        
        try:
            app_db.user_db.close_connection()
        except Exception:
            pass
        app_instance.release()
    
    app.aboutToQuit.connect(release)