import os
import sys
import shutil
import zipfile
from pathlib import Path
import tarfile

from utilities.functions import get_parent_dir


def _get_bin_dir() -> Path:
    return Path(get_parent_dir()) / "bin"


def install_tool(
    downloaded_path: str,
    tool_name: str,
    is_zip: bool,
    binary_name_win: str,
    binary_name_posix: str,
) -> tuple[bool, str]:
    if tool_name == "ffmpeg":
        return _install_ffmpeg_binaries(downloaded_path)

    bin_dir = _get_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)

    src = Path(downloaded_path)
    if not src.exists():
        return False, f"Downloaded file not found: {src}"

    final_name = binary_name_win if sys.platform == "win32" else binary_name_posix
    dest       = bin_dir / final_name

    try:
        if not is_zip:
            shutil.copy2(str(src), str(dest))
            if sys.platform != "win32":
                os.chmod(str(dest), 0o755)
        else:
            tmp_dir = src.parent / f"_extract_{tool_name}"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(str(src), "r") as zf:
                    zf.extractall(str(tmp_dir))

                binary = _find_binary(tmp_dir, final_name)

                if binary is None and sys.platform != "win32":
                    binary = _find_binary(tmp_dir, Path(final_name).stem)

                if binary is None:
                    return False, f"Binary '{final_name}' not found inside zip archive"

                shutil.copy2(str(binary), str(dest))
                if sys.platform != "win32":
                    os.chmod(str(dest), 0o755)
            finally:
                shutil.rmtree(str(tmp_dir), ignore_errors=True)

    except Exception as exc:
        return False, str(exc)

    _record_installed_binary(tool_name, dest)
    return True, str(dest)


def _record_installed_binary(tool_name: str, dest: Path) -> None:
    """Point the matching prefs at a freshly installed binary so tools pick
    it up without waiting for the next startup's binary scan."""
    pref_keys = {
        "yt-dlp": ("yt-dlp_binary", "yt-dlp_path"),
        "ffmpeg": ("ffmpeg_binary", "ffmpeg_path"),
    }.get(tool_name)
    if pref_keys is None or not dest.exists():
        return
    binary_key, dir_key = pref_keys
    try:
        from app_config import prefs

        prefs.prefs[binary_key] = str(dest)
        prefs.prefs[dir_key] = str(dest.parent)
        prefs.save()
    except Exception:
        pass


def _install_ffmpeg_binaries(downloaded_path: str) -> tuple[bool, str]:
    if sys.platform == "darwin":
        return _install_macos_ffmpeg(downloaded_path)
    return _install_ffmpeg_package(downloaded_path)


def _install_ffmpeg_package(downloaded_path: str) -> tuple[bool, str]:
    """The Windows and Linux packages keep every binary and library the tools
    need in one bin/ folder inside a single top-level folder, so the whole
    folder is copied into PlayForm's bin."""
    bin_dir = _get_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)

    src = Path(downloaded_path)
    if not src.exists():
        return False, f"Downloaded file not found: {src}"

    tmp_dir = src.parent / f"_extract_ffmpeg_{src.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

    try:
        _extract_archive(src, tmp_dir)

        package_bin = _find_package_bin(tmp_dir)
        if package_bin is None:
            return False, "Could not locate the package's bin folder"

        if not (package_bin / ffmpeg_name).is_file():
            return False, f"'{ffmpeg_name}' not found in the downloaded package"

        copied: list[str] = []
        for entry in sorted(package_bin.iterdir()):
            if not entry.is_file():
                continue
            dest = bin_dir / entry.name
            shutil.copy2(str(entry), str(dest))
            if sys.platform != "win32":
                os.chmod(str(dest), 0o755)
            copied.append(str(dest))

        _record_installed_binary("ffmpeg", bin_dir / ffmpeg_name)

        return True, ", ".join(copied)
    except Exception as exc:
        return False, str(exc)
    finally:
        shutil.rmtree(str(tmp_dir), ignore_errors=True)


def _extract_archive(src: Path, dest: Path) -> None:
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(str(src), "r") as zf:
            zf.extractall(str(dest))
        return

    if tarfile.is_tarfile(src):
        with tarfile.open(str(src), "r:*") as tf:
            tf.extractall(str(dest), filter="data")
        return

    raise ValueError(f"Unsupported archive format: {src.name}")


def _find_package_bin(extract_dir: Path) -> Path | None:
    candidates = [extract_dir / "bin"]
    candidates += [child / "bin" for child in extract_dir.iterdir() if child.is_dir()]
    for candidate in candidates:
        if candidate.is_dir() and any(entry.is_file() for entry in candidate.iterdir()):
            return candidate
    return None


def _install_macos_ffmpeg(downloaded_path: str) -> tuple[bool, str]:
    """evermeet ships ffmpeg and ffprobe as separate 7z archives, each holding
    a single binary."""
    import patoolib

    bin_dir = _get_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)

    src = Path(downloaded_path)
    if not src.exists():
        return False, f"Downloaded file not found: {src}"

    tmp_dir = src.parent / f"_extract_ffmpeg_{src.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []

    try:
        try:
            patoolib.extract_archive(str(src), outdir=str(tmp_dir), verbosity=-1)
        except Exception:
            shutil.copy2(str(src), str(tmp_dir / src.name))

        for binary_name in ("ffmpeg", "ffprobe"):
            candidate = _find_binary(tmp_dir, binary_name)
            if candidate and candidate.is_file():
                dest = bin_dir / binary_name
                shutil.copy2(str(candidate), str(dest))
                os.chmod(str(dest), 0o755)
                copied.append(str(dest))

        if not copied:
            return False, "Could not locate ffmpeg or ffprobe in the downloaded package"

        _record_installed_binary("ffmpeg", bin_dir / "ffmpeg")

        return True, ", ".join(copied)
    except Exception as exc:
        return False, str(exc)
    finally:
        shutil.rmtree(str(tmp_dir), ignore_errors=True)


def _find_binary(extract_dir: Path, binary_name: str) -> Path | None:
    direct = extract_dir / binary_name
    if direct.exists():
        return direct

    for child in extract_dir.iterdir():
        if child.is_dir():
            candidate = child / binary_name
            if candidate.exists():
                return candidate

    for p in extract_dir.rglob(binary_name):
        if p.is_file():
            return p

    return None
