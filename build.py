import sys
import shutil
import platform as _platform

from invoke.tasks import task
from invoke_config import *


APP_NAME        = "PlayForm"
APP_VERSION     = "1.1.0"
APP_PUBLISHER   = "JoyBytes"
APP_DESCRIPTION = "PlayForm Media Player"
APP_COPYRIGHT   = f"Copyright (c) 2026 {APP_PUBLISHER}"
ENTRY_POINT     = SRC_DIR / "app.py"
UPDATER_ENTRY   = SRC_DIR / "updater.py"

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


def _join_cmd(args) -> str:
    parts = []
    for a in args:
        s = str(a)
        if any(c in s for c in (' ', '(', ')')):
            parts.append(f'"{s}"')
        else:
            parts.append(s)
    return " ".join(parts)


def _base_args(output_dir, debug_build=False) -> list[str]:
    """Options that are identical across all platforms."""
    args = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--deployment",
    ]
    if not debug_build:
        args.append("--remove-output")
    args.extend([
        #"--low-memory",
        "--no-debug-immortal-assumptions",
        "--include-package-data=qdarkstyle",
        "--nofollow-import-to=ffmpeg_binary",
        "--nofollow-import-to=assets_rc",
        # media_core (av_play/metaindex/metaparser) is compiled separately by
        # build_media_core_pyd into its own .pyd, moved into app.dist below -
        # same pattern as assets_rc. Since the main compile never follows
        # into media_core, it also never discovers the third-party packages
        # only media_core imports (python-mpv, lxml, mutagen aren't imported
        # anywhere else in src/) - force their inclusion explicitly so
        # app.dist still ships them; without this the compiled media_core.pyd
        # would fail to import them at runtime.
        "--nofollow-import-to=media_core",
        "--include-package=mpv",
        "--include-package=lxml",
        "--include-package=mutagen",
        "--nofollow-import-to=pygments",
        "--nofollow-import-to=sqlalchemy.ext",
        "--nofollow-import-to=sqlalchemy.dialects.mssql",
        "--nofollow-import-to=sqlalchemy.dialects.mysql",
        "--nofollow-import-to=sqlalchemy.dialects.oracle",
        "--nofollow-import-to=sqlalchemy.dialects.postgresql",
        "--enable-plugin=pyside6",
        f"--include-qt-plugins={','.join(QT_PLUGINS)}",
        "--report=compilation-report.xml",
        f"--output-dir={output_dir}",
    ])
    return args


def _translation_data_args() -> list[str]:
    lang_dir = ROOT_DIR / "lang"
    if lang_dir.exists():
        return [f"--include-data-dir={lang_dir}=lang"]
    return []


def _windows_args(assets_dir, app_name) -> list[str]:
    args = [
        "--windows-console-mode=disable",
        "--assume-yes-for-downloads",
        f"--output-filename={app_name}.exe",
    ]
    icon = assets_dir / f"{app_name}.ico"
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
    icon = assets_dir / f"{app_name}.icns"
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
    c.run(f"python {SCRIPTS_DIR / 'compile_assets.py'}", pty=False, in_stream=False)


@task
def build_assets_pyd(c):
    """Compile assets_rc.py to a native .pyd module (output: dist/)"""
    assets_rc = SRC_DIR / "assets_rc.py"
    if not assets_rc.exists():
        print("assets_rc.py not found, running compile_assets first...")
        compile_assets(c)
    print("Compiling assets_rc.py to .pyd module...")
    c.run(
        f"{sys.executable} -m nuitka --module {assets_rc} --output-dir={BIN_DIR} --remove-output",
        pty=False,
        in_stream=False,
    )


@task
def build_media_core_pyd(c):
    """Compile src/media_core (av_play/metaindex/metaparser) to a native
    .pyd module (output: dist/) - same --module pattern as build_assets_pyd,
    just for a real multi-file package instead of one flat .py file.
    --include-package=media_core is what makes Nuitka embed every submodule
    (av_play, metaindex, metaparser and their own subpackages) into the one
    compiled extension, so `import media_core.av_play` etc. keeps working
    against the compiled artifact exactly as it does against the source tree.
    """
    media_core_dir = SRC_DIR / "media_core"
    if not media_core_dir.exists():
        print(f"media_core package not found at {media_core_dir}, skipping.")
        return
    print("Compiling media_core package to .pyd module...")
    c.run(
        f"{sys.executable} -m nuitka --module {media_core_dir} --include-package=media_core "
        f"--output-dir={BIN_DIR} --remove-output",
        pty=False,
        in_stream=False,
    )


@task(pre=[build_assets_pyd, build_media_core_pyd])
def compile(c, target_platform=None, app_name=APP_NAME, version=APP_VERSION, compiler=None, debug_build=False):
    """Compile the application with Nuitka."""
    plat = _detect_platform(target_platform)
    output_dir = BIN_DIR

    if not ENTRY_POINT.exists():
        print(f"Error: entry point not found: {ENTRY_POINT}")
        return

    print(f"Compiling [{app_name} v{version}] for platform: {plat}")
    print(f"Entry point : {ENTRY_POINT}")
    print(f"Output dir  : {output_dir}")

    args = _base_args(output_dir, debug_build=debug_build)
    if debug_build:
        args += ["--show-scons", "--verbose", "--show-modules", "--show-progress"]
    args += _translation_data_args()

    args += [
        f"--company-name={APP_PUBLISHER}",
        f"--product-name={app_name}",
        f"--product-version={version}",
        f"--file-version={version}",
        f"--file-description={APP_DESCRIPTION}",
        f"--copyright={APP_COPYRIGHT}",
    ]

    if compiler:
        args.append(f"--{compiler}")

    if plat == "windows":
        args += _windows_args(ASSETS_DIR, app_name)
    elif plat == "darwin":
        args += _darwin_args(ASSETS_DIR, app_name, version)
    else:
        args += _linux_args(app_name)

    args.append(str(ENTRY_POINT))

    cmd = _join_cmd(args)
    print(f"\nNuitka command:\n  {cmd}\n")
    c.run(cmd, pty=False, in_stream=False)

    if plat == "darwin":
        app_dist_dir = BIN_DIR / f"{app_name}.app" / "Contents" / "MacOS"
    else:
        app_dist_dir = BIN_DIR / "app.dist"

    if app_dist_dir.exists():
        for pattern in ("assets_rc*.pyd", "media_core*.pyd"):
            for pyd_file in BIN_DIR.glob(pattern):
                dest_pyd = app_dist_dir / pyd_file.name
                shutil.move(str(pyd_file), str(dest_pyd))
                print(f"Moved {pyd_file.name} -> {dest_pyd}")

        (app_dist_dir / "bin").mkdir(exist_ok=True)

        if plat == "windows":
            for pdb in app_dist_dir.rglob("*.pdb"):
                pdb.unlink()
                print(f"Removed {pdb.name}")
    else:
        print(f"[warn] Output dir not found: {app_dist_dir}, skipping post-compile moves.")


@task
def build(c, target_platform=None, app_name=APP_NAME, version=APP_VERSION, compiler=None):
    compile(c, target_platform=target_platform, app_name=app_name, version=version, compiler=compiler)


def _updater_base_args(output_dir, debug_build=False) -> list[str]:
    args = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--deployment",
    ]
    if not debug_build:
        args.append("--remove-output")
    args.extend([
        "--no-debug-immortal-assumptions",
        "--report=updater-compilation-report.xml",
        f"--output-dir={output_dir}",
    ])
    return args


def _updater_windows_args() -> list[str]:
    return [
        "--windows-console-mode=disable",
        "--assume-yes-for-downloads",
        "--output-filename=updater.exe",
    ]


def _updater_darwin_args() -> list[str]:
    return ["--output-filename=updater"]


def _updater_linux_args() -> list[str]:
    return ["--output-filename=updater"]


@task
def compile_updater(c, target_platform=None, debug_build=False):
    plat = _detect_platform(target_platform)
    output_dir = BIN_DIR

    if not UPDATER_ENTRY.exists():
        print(f"Error: updater entry point not found: {UPDATER_ENTRY}")
        return

    print(f"Compiling updater for platform: {plat}")
    print(f"Entry point : {UPDATER_ENTRY}")
    print(f"Output dir  : {output_dir}")

    args = _updater_base_args(output_dir, debug_build=debug_build)
    if debug_build:
        args += ["--show-scons", "--verbose", "--show-modules", "--show-progress"]

    if plat == "windows":
        args += _updater_windows_args()
    elif plat == "darwin":
        args += _updater_darwin_args()
    else:
        args += _updater_linux_args()

    args.append(str(UPDATER_ENTRY))

    cmd = _join_cmd(args)
    print(f"\nNuitka command:\n  {cmd}\n")
    c.run(cmd, pty=False, in_stream=False)


