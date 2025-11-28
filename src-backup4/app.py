import os, sys, logging
import PySide6

from utilities.functions import get_app_path, get_parent_dir

#qt_path= os.path.dirname(PySide6.__file__)
#os.environ['QT_PLUGIN_PATH'] = os.path.join(qt_path, "qt-plugins")
os.environ["VLC_LIB_PATH"] = os.path.join(get_parent_dir(), "lib")
os.environ["USE_VLC"] = "1"

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