from invoke.tasks import task
from invoke.collection import Collection
from invoke_config import *

import sys
import shutil
import platform as _platform
import dist
import build


@task
def install_req(c):
    print("Installing all dependencies...")
    c.run("pip install -r requirements.txt", pty=False, in_stream=False)


@task
def dev_install(c):
    install_req(c)
    build.compile_assets(c)
    print("\nDevelopment environment ready!")


@task
def clear_cache(c):
    if sys.platform == "win32":
        c.run('for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"', shell="cmd", pty=False, in_stream=False)
    else:
        c.run('find . -type d -name __pycache__ -exec rm -rf {} +', pty=False, in_stream=False)


@task
def run_app(c):
    if sys.platform == "win32":
        c.run(r'python src\app.py', pty=False, in_stream=False)
    else:
        c.run('python src/app.py', pty=False, in_stream=False)


def _detect_plat(override):
    return override.lower() if override else _platform.system().lower()


def _app_dist_dir(plat):
    if plat == "darwin":
        return BIN_DIR / f"{build.APP_NAME}.app" / "Contents" / "MacOS"
    return BIN_DIR / "app.dist"


def _binary_name(name, plat):
    return f"{name}.exe" if plat == "windows" else name


def _copy_dir(src, dest):
    if src.exists():
        shutil.copytree(str(src), str(dest), dirs_exist_ok=True)
        print(f"Copied {src} -> {dest}")


def _run_python_script(c, script_name, *args):
    script = SCRIPTS_DIR / script_name
    cmd = " ".join([f'"{sys.executable}"', f'"{script}"', *[f'"{arg}"' for arg in args]])
    c.run(cmd, pty=False, in_stream=False)


def _copy_speechcore_dlls(app_dist_dir):
    if sys.platform != "win32":
        return
    try:
        import importlib
        sc = importlib.import_module("SpeechCore")
        sc_dir = Path(sc.__file__).parent
    except Exception:
        print("[warn] SpeechCore not found, skipping DLL copy")
        return
    dlls = list(sc_dir.glob("*.dll"))
    if not dlls:
        print("[warn] No DLLs found in SpeechCore package")
        return
    for dll in dlls:
        dest = app_dist_dir / dll.name
        shutil.copy2(str(dll), str(dest))
        print(f"Copied {dll.name} -> {dest}")


def _sync_translation_files(app_dist_dir):
    _copy_dir(ROOT_DIR / "lang", app_dist_dir / "lang")


@task
def translate_gen(c):
    print("Generating translation template...")
    _run_python_script(c, "translate_gen.py")


@task
def translate_compile(c):
    print("Compiling translation catalogs...")
    _run_python_script(c, "translate_compile.py")


@task
def translate_creat(c, language):
    print(f"Creating translation catalog for {language}...")
    _run_python_script(c, "translate_creat.py", language)


@task
def build_docs(c, langs=None):
    """Compile Markdown documentation to HTML.
    
    Reads docs/source/<lang>/*.md and outputs HTML to docs/build/<lang>/.
    
    Args:
        langs: Comma-separated language codes (e.g. 'en,fr').
               If omitted, all subdirectories under docs/source/ are processed.
    """
    cmd = f'"{sys.executable}" "{SCRIPTS_DIR / "compile_docs.py"}"'
    if langs:
        for lang in langs.split(","):
            cmd += f" {lang.strip()}"
    c.run(cmd, pty=False, in_stream=False)


@task
def compile(c, target_platform=None, app_name=build.APP_NAME, version=build.APP_VERSION, compiler=None):
    plat = _detect_plat(target_platform)

    build.compile_assets(c)
    build.build_assets_pyd(c)

    public_key_py = SRC_DIR / "public_key.py"
    if not public_key_py.exists():
        dist.generate_public_key(c, key_path=str(ROOT_DIR / "public_key.pem"), destination=str(SRC_DIR))

    updater_dist = BIN_DIR / "updater.dist"
    if updater_dist.exists():
        shutil.rmtree(str(updater_dist))
        print(f"Removed {updater_dist}")

    build.compile(c, target_platform=target_platform, app_name=app_name, version=version, compiler=compiler)
    build.compile_updater(c, target_platform=target_platform)

    app_dist_dir = _app_dist_dir(plat)
    if not app_dist_dir.exists():
        print(f"[warn] app dist dir not found: {app_dist_dir}")
        return

    if updater_dist.exists():
        shutil.copytree(str(updater_dist), str(app_dist_dir), dirs_exist_ok=True)
        print(f"Copied updater.dist -> {app_dist_dir}")
    else:
        print(f"[warn] updater.dist not found after compile: {updater_dist}")

    for stale in app_dist_dir.glob("*.crc32"):
        stale.unlink()
    for stale in app_dist_dir.glob("*.sha256"):
        stale.unlink()
    for stale in app_dist_dir.glob("*.sha512"):
        stale.unlink()
    for stale in app_dist_dir.glob("*.sig"):
        stale.unlink()
    for stale in app_dist_dir.glob("*-manifest.json"):
        stale.unlink()
        print(f"Removed stale manifest: {stale.name}")

    _copy_speechcore_dlls(app_dist_dir)

    _sync_translation_files(app_dist_dir)
    _copy_dir(ROOT_DIR / "bin",  app_dist_dir / "bin")
    _copy_dir(ROOT_DIR / "lib",  app_dist_dir / "lib")

    build_docs(c)
    docs_build = ROOT_DIR / "docs" / "build"
    if docs_build.exists():
        docs_dist = app_dist_dir / "docs"
        shutil.copytree(str(docs_build), str(docs_dist), dirs_exist_ok=True)
        print(f"Copied docs/build -> {docs_dist}")


@task
def release(c, version=build.APP_VERSION, target_platform=None, app_name=build.APP_NAME, key=None):
    plat = _detect_plat(target_platform)
    app_dist_dir = _app_dist_dir(plat)
    private_key = key or str(ROOT_DIR / "private_key.pem")

    app_bin     = app_dist_dir / _binary_name(app_name, plat)
    updater_bin = app_dist_dir / _binary_name("updater", plat)

    dist.checksums(c, file_path=str(app_bin),     output_dir=str(app_dist_dir))
    dist.checksums(c, file_path=str(updater_bin), output_dir=str(app_dist_dir))

    dist.sign(c, binary=str(app_bin),     key=private_key, output=str(app_bin)     + ".sig")
    dist.sign(c, binary=str(updater_bin), key=private_key, output=str(updater_bin) + ".sig")

    dist.manifest(c, folder=str(app_dist_dir), version=version)


@task
def bundle(c, target_platform=None, app_name=build.APP_NAME, version=build.APP_VERSION):
    plat = _detect_plat(target_platform)
    app_dist_dir = _app_dist_dir(plat)

    _sync_translation_files(app_dist_dir)

    if not (app_dist_dir / f"{app_name}-{version}-{plat}").exists():
        print(f"[warn] No .sig files found in {app_dist_dir}. Run 'inv release' first.")

    archive_name = BIN_DIR / f"{app_name}-{version}-{plat}"
    shutil.make_archive(str(archive_name), "zip", root_dir=str(app_dist_dir), base_dir=".")
    print(f"Packed {app_dist_dir.name} -> {archive_name}.zip")


namespace = Collection(build, dist)
namespace.add_task(install_req)
namespace.add_task(dev_install)
namespace.add_task(clear_cache)
namespace.add_task(run_app)
namespace.add_task(translate_gen)
namespace.add_task(translate_compile)
namespace.add_task(translate_creat)
namespace.add_task(build_docs)
namespace.add_task(compile)
namespace.add_task(bundle)
namespace.add_task(release)
