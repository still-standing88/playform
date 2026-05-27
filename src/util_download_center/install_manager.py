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

    return True, str(dest)


def _install_ffmpeg_binaries(downloaded_path: str) -> tuple[bool, str]:
    import patoolib

    bin_dir = _get_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)

    src = Path(downloaded_path)
    if not src.exists():
        return False, f"Downloaded file not found: {src}"

    tmp_dir = src.parent / f"_extract_ffmpeg_{src.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    copied: list[str] = []

    try:
        lower_name = src.name.lower()
        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(str(src), "r") as zf:
                zf.extractall(str(tmp_dir))
        elif tarfile.is_tarfile(src):
            with tarfile.open(str(src), "r:*") as tf:
                tf.extractall(str(tmp_dir))
        else:
            try:
                patoolib.extract_archive(str(src), outdir=str(tmp_dir), verbosity=-1)
            except Exception:
                shutil.copy2(str(src), str(tmp_dir / src.name))

        ffmpeg_candidate = _find_binary(tmp_dir, ffmpeg_name)
        ffprobe_candidate = _find_binary(tmp_dir, ffprobe_name)

        if ffmpeg_candidate and ffmpeg_candidate.is_file():
            dest = bin_dir / ffmpeg_name
            shutil.copy2(str(ffmpeg_candidate), str(dest))
            if sys.platform != "win32":
                os.chmod(str(dest), 0o755)
            copied.append(str(dest))

        if ffprobe_candidate and ffprobe_candidate.is_file():
            dest = bin_dir / ffprobe_name
            shutil.copy2(str(ffprobe_candidate), str(dest))
            if sys.platform != "win32":
                os.chmod(str(dest), 0o755)
            copied.append(str(dest))

        if not copied and lower_name.startswith("ffmpeg"):
            dest = bin_dir / ffmpeg_name
            shutil.copy2(str(src), str(dest))
            if sys.platform != "win32":
                os.chmod(str(dest), 0o755)
            copied.append(str(dest))
        elif not copied and lower_name.startswith("ffprobe"):
            dest = bin_dir / ffprobe_name
            shutil.copy2(str(src), str(dest))
            if sys.platform != "win32":
                os.chmod(str(dest), 0o755)
            copied.append(str(dest))

        if not copied:
            return False, "Could not locate ffmpeg or ffprobe in the downloaded package"

        try:
            from app_config import prefs

            ffmpeg_dest = bin_dir / ffmpeg_name
            if ffmpeg_dest.exists():
                prefs.prefs["ffmpeg_binary"] = str(ffmpeg_dest)
                prefs.prefs["ffmpeg_path"] = str(bin_dir)
                prefs.save()
        except Exception:
            pass

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
