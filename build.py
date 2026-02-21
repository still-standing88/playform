import sys
import platform as _platform

from invoke.tasks import task
from invoke_config import *


APP_NAME        = "aPlayForm"
APP_VERSION     = "1.0.0"
ENTRY_POINT     = SRC_DIR / "app.py"

QT_PLUGINS = [
    "platforms",
    "styles",
    "iconengines",
    "imageformats",
]


def _detect_platform(override: str | None) -> str:
    if override:
        return override.lower()
    return _platform.system().lower()


def _base_args(output_dir) -> list[str]:
    """Options that are identical across all platforms."""
    return [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--deployment",
        "--no-debug-immortal-assumptions",
        "--include-package-data=qdarkstyle",
        "--nofollow-import-to=ffmpeg_binary",
        "--nofollow-import-to=assets_rc",
        "--enable-plugin=pyside6",
        f"--include-qt-plugins={','.join(QT_PLUGINS)}",
        "--report=compilation-report.xml",
        f"--output-dir={output_dir}",
    ]


def _windows_args(assets_dir, app_name) -> list[str]:
    args = [
        "--windows-console-mode=disable",
        "--assume-yes-for-downloads",
        f"--output-filename={app_name}.exe",
    ]
    icon = assets_dir / f"{app_name.lower()}.ico"
    if icon.exists():
        args.append(f"--windows-icon-from-ico={icon}")
    else:
        print(f"  [warn] No .ico found at {icon}, skipping icon.")
    return args


def _darwin_args(assets_dir, app_name, version) -> list[str]:
    args = [
        "--macos-create-app-bundle",
        f"--macos-app-name={app_name}",
        f"--macos-app-version={version}",
    ]
    icon = assets_dir / f"{app_name.lower()}.icns"
    if icon.exists():
        args.append(f"--macos-app-icon={icon}")
    else:
        print(f"  [warn] No .icns found at {icon}, skipping icon.")
    return args


def _linux_args(app_name) -> list[str]:
    return [f"--output-filename={app_name}"]



@task
def compile_assets(c):
    """Compile Qt resource files (.qrc -> _rc.py)"""
    print("Compiling Qt resource files...")
    c.run(f"python {SCRIPTS_DIR / 'compile_assets.py'}", pty=False)


@task(pre=[compile_assets])
def compile(c, target_platform=None, app_name=APP_NAME, version=APP_VERSION):
    """Compile the application with Nuitka.

    Args:
        target_platform: windows / linux / darwin  (auto-detected if omitted)
        app_name:        Output executable name     (default: APP_NAME)
        version:         App version string         (default: APP_VERSION)
    """
    plat = _detect_platform(target_platform)
    output_dir = BIN_DIR

    if not ENTRY_POINT.exists():
        print(f"Error: entry point not found: {ENTRY_POINT}")
        return

    print(f"Compiling [{app_name} v{version}] for platform: {plat}")
    print(f"Entry point : {ENTRY_POINT}")
    print(f"Output dir  : {output_dir}")

    args = _base_args(output_dir)

    if plat == "windows":
        args += _windows_args(ASSETS_DIR, app_name)
    elif plat == "darwin":
        args += _darwin_args(ASSETS_DIR, app_name, version)
    else:
        args += _linux_args(app_name)

    args.append(str(ENTRY_POINT))

    cmd = " ".join(str(a) for a in args)
    print(f"\nNuitka command:\n  {cmd}\n")
    c.run(cmd, pty=False)


@task
def build(c, target_platform=None, app_name=APP_NAME, version=APP_VERSION):
    """Alias that mirrors old 'build' task — calls compile."""
    compile(c, target_platform=target_platform, app_name=app_name, version=version)
