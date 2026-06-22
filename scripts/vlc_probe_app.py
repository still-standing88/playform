import os
import sys
from pathlib import Path
import ctypes


_dll_dir_handles = []


def is_frozen():
    return getattr(sys, "frozen", False) or "__compiled__" in globals()


def get_app_path() -> str:
    if is_frozen():
        base_dir = Path(sys.argv[0]).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parents[1]
    return str(base_dir)


def get_parent_dir() -> str:
    if is_frozen():
        return str(Path(sys.argv[0]).resolve().parent)
    return str(Path(__file__).resolve().parents[1])


def setup_vlc_binaries():
    lib_dir = os.path.join(get_parent_dir(), "lib")
    libvlc_path = os.path.join(lib_dir, "libvlc.dll")
    plugins_dir = os.path.join(lib_dir, "plugins")

    os.environ["USE_VLC"] = "1"
    os.environ["VLC_LIB_PATH"] = lib_dir
    os.environ["VLC_PLUGIN_PATH"] = plugins_dir if os.path.isdir(plugins_dir) else lib_dir
    os.environ.pop("PYTHON_VLC_MODULE_PATH", None)

    if os.path.exists(libvlc_path):
        os.environ["PYTHON_VLC_LIB_PATH"] = libvlc_path

    if os.path.isdir(lib_dir):
        current_path = os.environ.get("PATH", "")
        normalized_entries = [os.path.normcase(os.path.normpath(entry)) for entry in current_path.split(os.pathsep) if entry]
        normalized_lib_dir = os.path.normcase(os.path.normpath(lib_dir))
        if normalized_lib_dir not in normalized_entries:
            os.environ["PATH"] = lib_dir + os.pathsep + current_path if current_path else lib_dir

        if hasattr(os, "add_dll_directory"):
            try:
                _dll_dir_handles.append(os.add_dll_directory(lib_dir))
            except OSError as exc:
                print(f"[after_setup] add_dll_directory_error={exc}")

        if hasattr(ctypes, "windll"):
            try:
                ctypes.windll.kernel32.SetDllDirectoryW(lib_dir)
            except Exception as exc:
                print(f"[after_setup] SetDllDirectoryW_error={exc}")


def _print_state(label: str):
    print(f"[{label}] cwd={os.getcwd()}")
    print(f"[{label}] argv0={sys.argv[0]}")
    print(f"[{label}] executable={sys.executable}")
    print(f"[{label}] frozen={getattr(sys, 'frozen', False)} compiled={hasattr(sys, '__compiled__')}")
    for key in (
        "USE_VLC",
        "VLC_LIB_PATH",
        "VLC_PLUGIN_PATH",
        "PYTHON_VLC_LIB_PATH",
        "PYTHON_VLC_MODULE_PATH",
        "PATH",
    ):
        value = os.environ.get(key)
        if key == "PATH" and value:
            value = value.split(os.pathsep)[0:5]
        print(f"[{label}] {key}={value}")


def main():
    _print_state("before")
    print(f"[before] get_app_path={get_app_path()}")
    print(f"[before] get_parent_dir={get_parent_dir()}")

    setup_vlc_binaries()

    _print_state("after_setup")
    print(f"[after_setup] app_dir_exists={os.path.isdir(get_app_path())}")
    print(f"[after_setup] parent_dir_exists={os.path.isdir(get_parent_dir())}")
    print(f"[after_setup] lib_dir_exists={os.path.isdir(os.path.join(get_parent_dir(), 'lib'))}")
    print(f"[after_setup] dll_exists={os.path.isfile(os.path.join(get_parent_dir(), 'lib', 'libvlc.dll'))}")
    print(f"[after_setup] plugins_exists={os.path.isdir(os.path.join(get_parent_dir(), 'lib', 'plugins'))}")

    try:
        import vlc

        print(f"[after_vlc] plugin_path={getattr(vlc, 'plugin_path', None)}")
        print(f"[after_vlc] dll={getattr(vlc, 'dll', None)}")
    except Exception as exc:
        print(f"[after_vlc] import_error={type(exc).__name__}: {exc}")
        raise

    try:
        import av_play

        print(f"[after_av_play] module={av_play.__file__}")
        print(f"[after_av_play] VideoPlayer={getattr(av_play, 'VideoPlayer', None)}")
    except Exception as exc:
        print(f"[after_av_play] import_error={type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
