import os
import sys
import traceback
from pathlib import Path


def write_log(text: str) -> None:
    try:
        base = Path(sys.argv[0]).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        log_path = base / "probe-log.txt"
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except Exception:
        pass


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    src_dir = base / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    write_log("=== probe start ===")
    write_log(f"sys.frozen={getattr(sys, 'frozen', False)}")
    write_log(f"sys.executable={sys.executable}")
    write_log(f"sys.argv[0]={sys.argv[0]}")

    try:
        from app_info import setup_env
        setup_env()
        write_log("setup_env=ok")

        from utilities.functions import get_app_path, get_parent_dir, setup_vlc_binaries
        write_log(f"get_app_path(before)={get_app_path()}")
        write_log(f"get_parent_dir(before)={get_parent_dir()}")
        setup_vlc_binaries()
        os.environ["USE_VLC"] = "1"
        write_log("setup_vlc_binaries=ok")
        for key in ("USE_VLC", "VLC_LIB_PATH", "VLC_PLUGIN_PATH", "PYTHON_VLC_LIB_PATH", "PYTHON_VLC_MODULE_PATH", "PATH"):
            value = os.environ.get(key)
            if key == "PATH" and value:
                value = value[:400]
            write_log(f"{key}={value}")

        import utilities.vlc_bootstrap
        write_log("vlc_bootstrap=ok")

        try:
            import vlc
            write_log(f"vlc_import=ok plugin_path={getattr(vlc, 'plugin_path', None)} dll={getattr(vlc, 'dll', None)}")
        except Exception:
            write_log("vlc_import=fail")
            write_log(traceback.format_exc())

        import EXPLORER.explorer_widget
        write_log("import_EXPLORER.explorer_widget=ok")

        import gui.main_window
        write_log("import_gui.main_window=ok")

        return 0
    except Exception:
        write_log("probe_exception")
        write_log(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
