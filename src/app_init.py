import os
import sys
import threading
import locale

from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from utilities.i18n import install_translation


def _log(msg: str) -> None:
    """Write to stdout if available (None in windowed frozen builds)."""
    out = sys.__stdout__
    if out is not None:
        out.write(msg)
        out.flush()

LOCAL_SERVER_NAME = "PlayFormLocalIPC"


def _clean_path_arg(raw_arg: str) -> str:
    arg = raw_arg.strip().strip('"').strip("'").strip()
    if not arg:
        return arg
    import av_play
    if not av_play.is_url(arg):
        arg = os.path.abspath(arg)
    return arg


def _send_via_local_socket(path: str) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(LOCAL_SERVER_NAME)
    if not socket.waitForConnected(3000):
        return False
    socket.write(path.encode("utf-8"))
    if not socket.waitForBytesWritten(3000):
        socket.disconnectFromServer()
        return False
    socket.flush()
    socket.disconnectFromServer()
    return True


def setup_environment():
    import app_info
    app_info.setup_env()

    from utilities.functions import get_parent_dir

    bin_dir = os.path.join(get_parent_dir(), "bin")
    if os.path.isdir(bin_dir):
        existing = os.environ.get("PATH", "")
        os.environ["PATH"] = bin_dir + os.pathsep + existing

    if getattr(sys, 'frozen', False):
        BASE_DIR = Path(sys.executable).parent
        os.environ['QT_PLUGIN_PATH'] = str(BASE_DIR / "PySide6" / "qt-plugins")
    else:
        BASE_DIR = Path(__file__).parent

    return BASE_DIR


BASE_FONT_POINT_SIZE = 9
MIN_UI_ZOOM_LEVEL = -4
MAX_UI_ZOOM_LEVEL = 10


def apply_ui_zoom(app, zoom_level=None):
    from app_config import prefs
    if zoom_level is None:
        zoom_level = prefs.prefs.get("ui_zoom_level", 0)
    zoom_level = max(MIN_UI_ZOOM_LEVEL, min(MAX_UI_ZOOM_LEVEL, zoom_level))
    app.setFont(QFont("Segoe UI", BASE_FONT_POINT_SIZE + zoom_level))
    return zoom_level


def setup_application_style(app):
    from utilities.theme_manager import setup_theme
    app.setStyle('Fusion')
    apply_ui_zoom(app)
    setup_theme(app)


def initialize_app_guard(cli_args):
    import app_guard
    app_instance = app_guard.AppGuard()
    app_instance.init("PlayForm", lambda: None, False)

    if not app_instance.is_primary_instance():
        if cli_args and len(cli_args) > 1:
            path = _clean_path_arg(cli_args[1])
            _log(f"[PlayForm IPC] Secondary sending: {path}\n")
            if not _send_via_local_socket(path):
                app_instance.send_msg_request("cli-args", path)
        app_instance.focus_window("PlayForm")
        app_instance.release()
        return None, True

    return app_instance, False


def initialize_modules(splash):
    splash.update_message(_("Loading configuration..."))
    import app_config
    from app_config import key_config
    install_translation(app_config.prefs.prefs.get("language"))
    if app_config.prefs.prefs.get("should_restart"):
        app_config.prefs.prefs["should_restart"] = False
        app_config.prefs.save()

    splash.update_message(_("Loading database..."))
    import app_db

    splash.update_message(_("Initializing locale..."))
    locale.setlocale(locale.LC_NUMERIC, 'C')
    key_config.load_keys()
    from utilities.speech import speech_manager
    threading.Thread(target=speech_manager.init, daemon=True).start()
    from app_config import load_speech_config
    load_speech_config()
    return app_db, key_config


def create_main_window(splash, cli_args):
    from gui.main_window import MainWindow
    window = MainWindow()

    if len(cli_args) > 1:
        path = _clean_path_arg(cli_args[1])
        QTimer.singleShot(100, lambda: window.load_external_path(path))

    from update_checker import UpdateChecker
    UpdateChecker.instance(parent=window)
    return window


def start_local_server(window):
    QLocalServer.removeServer(LOCAL_SERVER_NAME)
    server = QLocalServer()
    if not server.listen(LOCAL_SERVER_NAME):
        _log("[PlayForm IPC] Primary: failed to start local server\n")
        return None

    def on_new_connection():
        client = server.nextPendingConnection()
        if not client:
            return
        client.readyRead.connect(lambda c=client: _read_client(c, window))

    server.newConnection.connect(on_new_connection)
    _log(f"[PlayForm IPC] Primary: local server started\n")
    return server


def _read_client(client, window):
    data = client.readAll()
    if not data:
        return
    path = data.data().decode("utf-8").strip()
    _log(f"[PlayForm IPC] Primary local: received '{path}'\n")
    client.disconnectFromServer()
    QTimer.singleShot(0, lambda p=path: window.load_external_path(p))


def setup_ipc_handlers(app_instance, window):
    import app_guard

    def handle_cli_args(data):
        _log(f"[PlayForm IPC] AppGuard received: {data}\n")
        path = data.get("msg_data", "") if isinstance(data, dict) else ""
        if path:
            QTimer.singleShot(0, lambda p=path: window.load_external_path(p))

    cli_args_msg = app_instance.create_ipc_msg("cli-args", handle_cli_args)
    app_instance.register_msg(cli_args_msg)
    _log("[PlayForm IPC] AppGuard handler registered\n")


def setup_cleanup(app, app_instance, app_db):
    from utilities.speech import speech_manager

    def release():
        try:
            speech_manager.stop_queue()
        except Exception:
            pass

        try:
            app_db.user_db.close_connection()
        except Exception:
            pass

        try:
            app_db.media_db.close_connection()
        except Exception:
            pass
        app_instance.release()

    app.aboutToQuit.connect(release)
