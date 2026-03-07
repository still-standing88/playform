import os
import sys
import shutil
import zipfile
from pathlib import Path

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
