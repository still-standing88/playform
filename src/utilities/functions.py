import platform as pform
import ctypes
import binascii
import os, sys
import time, datetime as dt
import py_youtube, httpx
import subprocess as sp
import validators as vl
import pyperclip
import shlex
import tempfile

from PySide6.QtCore import Qt as qt
from PySide6.QtCore import QUrl
from pathlib import Path

from utilities.util_structs import time_struct
#from pynotifier import NotificationClient, Notification
#from pynotifier.backends import platform

_dll_dir_handles = []


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
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()

    app._tray_icon.showMessage(
        msg_title,
        msg,
        QSystemTrayIcon.MessageIcon.Information,
        5000
    )
"""
    c = NotificationClient()
    c.register_backend(platform.Backend())
    notification = Notification(title=msg_title,message=msg)
    c.notify_all(notification)
"""

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
    return vl.url(url) == True

def network_check():
    return sp.call(['ping','-n','1','8.8.8.8'])


def open_explorer(path):
    sp.Popen(fr'explorer /select,"{path}"')

def is_frozen():
    return getattr(sys, 'frozen', False) or "__compiled__" in globals()

def is_dev_mode():
    return not is_frozen()

def get_app_path() -> str:
    if is_frozen():
        BASE_DIR = Path(sys.argv[0]).resolve().parent
    else:
        BASE_DIR = Path(__file__).parent.parent
    return str(BASE_DIR)

def get_script_parent_dir():
    return Path(__file__).parent.parent.parent

def get_exe_parent_dir():
    return Path(sys.argv[0]).resolve().parent if is_frozen() else Path(sys.executable).parent

def get_parent_dir():
    return str(get_exe_parent_dir() if is_frozen() else get_script_parent_dir())

def get_debug_level() -> int:
    from app_config import prefs
    debug_level = prefs.prefs.get("debug_level", 2)
    return debug_level

def get_logs_dir() -> str:
    candidates = [Path(get_app_path()) / "logs"]

    local_appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "PlayForm" / "logs")

    candidates.append(Path.home() / ".playform" / "logs")
    candidates.append(Path(tempfile.gettempdir()) / "PlayForm" / "logs")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            with open(probe, "a", encoding="utf-8"):
                pass
            probe.unlink(missing_ok=True)
            return str(candidate)
        except OSError:
            continue

    fallback = Path(tempfile.gettempdir()) / "PlayForm" / "logs"
    fallback.mkdir(parents=True, exist_ok=True)
    return str(fallback)

def get_mpvlog_file() -> str:
    return str(Path(get_logs_dir()) / "mpv-log.txt")

def set_restart_flag(flag:bool):
    os.environ["APP_RESTART"] = "1" if flag else "0"

def get_restart_flag() -> bool:
    return os.environ.get("APP_RESTART", "0") == "1"

def restart_app():
    if is_frozen():
        os.execl(sys.executable, sys.executable, *sys.argv[1:])
    else:
        python = sys.executable
        os.execl(python, python, *sys.argv)

def initialize_com():
    if sys.platform == "win32":
        import pythoncom
        pythoncom.CoInitialize()

def is_valid_mpv_options(text: str) -> bool:
    try:
        _ = shlex.split(text, posix=True)
        return True
    except ValueError:
        return False
    except:
        return False

def parse_mpv_options(text: str) -> dict:
    options: dict[str, str | bool] = {}
    for token in shlex.split(text, posix=True):
        token = token.lstrip("-")
        if not token:
            continue
        key, sep, value = token.partition("=")
        key = key.replace("-", "_")
        options[key] = value if sep else True
    return options

def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    return 'youtube.com' in url_lower or 'youtu.be' in url_lower

def is_local_file(path: str) -> bool:
    if not path:
        return False
    try:
        return os.path.isfile(path)
    except:
        return False

def open_file_location(path: str):
    if not is_local_file(path):
        return

    if sys.platform == "win32":
        sp.Popen(fr'explorer /select,"{path}"')
    elif sys.platform == "darwin":
        sp.Popen(["open", "-R", path])
    else:
        sp.Popen(["xdg-open", os.path.dirname(path)])


def _mpv_lib_filename() -> str:
    if sys.platform == "darwin":
        return "libmpv.dylib"
    return "libmpv-2.dll"


def setup_mpv_macos():
    bundle_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    lib_path = os.path.join(bundle_dir, "lib", _mpv_lib_filename())
    os.environ["MPV_LIB_PATH"] = os.path.join(bundle_dir, "lib")
    return lib_path


def setup_mpv_windows():
    lib_dir = os.path.join(get_parent_dir(), "lib")
    libmpv_path = os.path.join(lib_dir, _mpv_lib_filename())

    os.environ["MPV_LIB_PATH"] = lib_dir

    if os.path.isdir(lib_dir):
        current_path = os.environ.get("PATH", "")
        normalized_entries = [os.path.normcase(os.path.normpath(entry)) for entry in current_path.split(os.pathsep) if entry]
        normalized_lib_dir = os.path.normcase(os.path.normpath(lib_dir))
        if normalized_lib_dir not in normalized_entries:
            os.environ["PATH"] = lib_dir + os.pathsep + current_path if current_path else lib_dir

        if hasattr(os, "add_dll_directory"):
            try:
                _dll_dir_handles.append(os.add_dll_directory(lib_dir))
            except OSError:
                pass

        if hasattr(ctypes, "windll"):
            try:
                ctypes.windll.kernel32.SetDllDirectoryW(lib_dir)
            except Exception:
                pass

    return libmpv_path, lib_dir


def _get_linux_package_manager() -> str | None:
    distro = ""
    like = ""
    try:
        release = pform.freedesktop_os_release()
        distro = release.get("ID", "")
        like = release.get("ID_LIKE", "")
    except Exception:
        pass
    if "debian" in like or distro in ("ubuntu", "debian", "mint", "linuxmint", "pop"):
        return "apt"
    elif "rhel" in like or "fedora" in like or distro in ("fedora", "rhel", "centos", "almalinux", "rocky"):
        return "dnf"
    elif distro == "arch" or "arch" in like:
        return "pacman"
    elif distro in ("opensuse", "opensuse-leap", "opensuse-tumbleweed") or "suse" in like:
        return "zypper"
    return None


def _check_mpv_installed_linux() -> bool:
    import shutil as _shutil
    if _shutil.which("mpv"):
        return True
    lib_candidates = [
        "/usr/lib/libmpv.so",
        "/usr/lib/libmpv.so.2",
        "/usr/lib/x86_64-linux-gnu/libmpv.so.2",
        "/usr/lib64/libmpv.so.2",
        "/usr/lib/aarch64-linux-gnu/libmpv.so.2",
    ]
    return any(os.path.exists(p) for p in lib_candidates)


def ensure_mpv_linux():
    if _check_mpv_installed_linux():
        return
    pm = _get_linux_package_manager()
    if pm is None:
        print("Warning: Could not detect package manager. Please install libmpv manually.")
        return
    print("libmpv not found. Installing mpv...")
    if pm == "apt":
        packages = ["libmpv2", "libmpv-dev"]
        install_cmd = ["apt-get", "install", "-y"] + packages
    elif pm == "dnf":
        packages = ["mpv-libs", "mpv-libs-devel"]
        install_cmd = ["dnf", "install", "-y"] + packages
    elif pm == "pacman":
        packages = ["mpv"]
        install_cmd = ["pacman", "-S", "--noconfirm"] + packages
    elif pm == "zypper":
        packages = ["libmpv2", "mpv-devel"]
        install_cmd = ["zypper", "install", "-y"] + packages
    else:
        print("Warning: Unsupported package manager. Please install libmpv manually.")
        return
    try:
        if os.getuid() != 0:
            print(f"Root access required. Running with sudo: {' '.join(install_cmd)}")
            result = sp.run(["sudo"] + install_cmd)
        else:
            result = sp.run(install_cmd)
        if result.returncode == 0:
            print("libmpv installed successfully.")
        else:
            print("libmpv installation failed. Please install it manually.")
    except Exception as e:
        print(f"Failed to install libmpv: {e}")


def setup_mpv_binaries():
    if sys.platform == "win32":
        setup_mpv_windows()
    elif sys.platform == "darwin":
        setup_mpv_macos()
    elif sys.platform.startswith("linux"):
        ensure_mpv_linux()
