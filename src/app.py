import os, sys, logging
import threading
#import PySide6

from utilities.functions import get_app_path, get_parent_dir, get_restart_flag, set_restart_flag, restart_app

#qt_path= os.path.dirname(PySide6.__file__)
#os.environ['QT_PLUGIN_PATH'] = os.path.join(qt_path, "qt-plugins")
os.environ["VLC_LIB_PATH"] = os.path.join(get_parent_dir(), "lib")
os.environ["USE_VLC"] = "1"

if sys.platform == "win32":
    import ctypes
    import pythoncom
    try:
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
    except:
        pass

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QFont, QPalette, QColor
from pathlib import Path

import app_guard
import av_play
import app_config
import app_db

from app_config import key_config, load_speech_config
from app_constance.styles import get_dark_palette
from gui.main_window import MainWindow
from utilities.speech import speech_manager


def setup_application_style(app: QApplication):
    app.setStyle('Fusion')
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    app.setPalette(get_dark_palette())


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
            app_instance.focus_window("Play Form")
            app_instance.release()
            sys.exit(0)

        def release():
            if get_restart_flag():
                set_restart_flag(False)
                restart_app()

            try:
                app_db.user_db.close_connection()
            except Exception:
                pass
            app_instance.release()

        app.setApplicationName("PlayForm")
        app.setApplicationVersion("1.0.0")
        app.aboutToQuit.connect(release)
        setup_application_style(app)
        import locale
        locale.setlocale(locale.LC_NUMERIC, 'C')
        key_config.load_keys()
        threading.Thread(target=speech_manager.init, daemon=True).start()
        load_speech_config()

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
        #log_error(f"Critical error in main application{e}", )
        exit_code = 1

    #finally:
        #cleanup_logging()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()