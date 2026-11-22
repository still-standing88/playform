"""Discovery and validation shared by the player, downloader and capture tools."""
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass

from utilities.functions import get_parent_dir


@dataclass(frozen=True)
class BinaryCheckResult:
    name: str
    path: str
    exists: bool
    runnable: bool
    detected: bool
    version: str | None
    major: int | None
    ok: bool
    message: str


_CHECK_CACHE: dict = {}
_LABELS = {"deno": "Deno", "mediacap": "MediaCap"}


def _binary_names(tool_name: str) -> tuple[str, ...]:
    ext = ".exe" if sys.platform == "win32" else ""
    if tool_name == "deno":
        return ("deno" + ext,)
    platform_name = "windows" if sys.platform == "win32" else "linux"
    return (
        "MediaCap" + ext,
        "mediacap" + ext,
        f"MediaCap-cli-{platform_name}-x64{ext}",
        f"MediaCap-cli-{platform_name}-arm64{ext}",
    )


def check_cli_binary(tool_name: str, path: str) -> BinaryCheckResult:
    """Check identity and executability; cache successful probes until the file changes."""
    label = _LABELS[tool_name]
    path = os.path.abspath(os.path.expanduser(path)) if path else ""
    exists = bool(path and os.path.isfile(path))
    runnable = detected = False
    version = None
    if not exists:
        message = _("{name} was not found. Set its path in Preferences > Advanced or download it from Options > Get/Update Utilities.").format(name=label)
    elif (sys.platform == "win32" and not path.lower().endswith(".exe")) or not os.access(path, os.X_OK):
        message = _("{name} is not executable. Check the file permissions and configured path.").format(name=label)
    else:
        try:
            stat = os.stat(path)
        except OSError as exc:
            message = _("{name} could not be accessed: {details}").format(name=label, details=str(exc))
            return BinaryCheckResult(label, path, exists, False, False, None, None, False, message)
        signature = (stat.st_mtime_ns, stat.st_size)
        cached = _CHECK_CACHE.get((tool_name, path))
        if cached and cached[0] == signature:
            return cached[1]
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        try:
            result = subprocess.run(
                [path, "--version"], stdin=subprocess.DEVNULL, capture_output=True,
                encoding="utf-8", errors="replace", timeout=5, **options,
            )
            runnable = result.returncode == 0
            output = result.stdout + "\n" + result.stderr
            match = re.search(rf"(?im)^{re.escape(label)}\s+(\d+[^\s]*)", output)
            detected = match is not None
            version = match.group(1) if match else None
            if runnable and detected:
                message = _("{name} is available.").format(name=label)
            elif not runnable:
                message = _("{name} could not be executed: {details}").format(
                    name=label, details=result.stderr.strip() or str(result.returncode),
                )
            else:
                message = _("The file does not appear to be a valid {name} executable.").format(name=label)
        except (OSError, subprocess.SubprocessError) as exc:
            message = _("{name} could not be executed: {details}").format(name=label, details=str(exc))
    major = int(re.match(r"\d+", version)[0]) if version else None
    checked = BinaryCheckResult(label, path, exists, runnable, detected, version, major,
                                runnable and detected, message)
    if checked.ok:
        _CHECK_CACHE[(tool_name, path)] = (signature, checked)
    return checked


def _candidates(tool_name: str, prefs: dict, bin_dir: str | None) -> list[str]:
    names = _binary_names(tool_name)
    global_paths = [found for name in names if (found := shutil.which(name))]
    configured = str(prefs.get(f"{tool_name}_path", "") or "")
    local_paths = []
    if configured:
        configured = os.path.expanduser(configured)
        if os.path.isdir(configured):
            local_paths.extend(os.path.join(configured, name) for name in names)
        else:
            local_paths.append(configured)
    elif prefs.get(f"{tool_name}_binary"):
        local_paths.append(str(prefs[f"{tool_name}_binary"]))
    bundled = os.fspath(bin_dir) if bin_dir is not None else os.path.join(get_parent_dir(), "bin")
    bundled_paths = [os.path.join(bundled, name) for name in names]
    # MediaCap explicitly prefers a working global installation. Deno follows
    # the other utilities' configured-path-first policy.
    ordered = (global_paths + local_paths + bundled_paths if tool_name == "mediacap"
               else local_paths + global_paths + bundled_paths)
    return list(dict.fromkeys(os.path.abspath(path) for path in ordered))


def _check_tool(tool_name: str, prefs: dict | None = None, bin_dir: str | None = None) -> BinaryCheckResult:
    if prefs is None:
        from app_config import prefs as app_prefs
        prefs = app_prefs.prefs
    first_failure = None
    first_missing = None
    for path in _candidates(tool_name, prefs, bin_dir):
        result = check_cli_binary(tool_name, path)
        if result.ok:
            return result
        if result.exists and first_failure is None:
            first_failure = result
        elif not result.exists and first_missing is None:
            first_missing = result
    return first_failure or first_missing or check_cli_binary(tool_name, "")


def check_deno(prefs: dict | None = None) -> BinaryCheckResult:
    return _check_tool("deno", prefs)


def check_mediacap(prefs: dict | None = None, bin_dir: str | None = None) -> BinaryCheckResult:
    return _check_tool("mediacap", prefs, bin_dir)


def resolve_deno_binary_path(prefs: dict | None = None) -> str:
    result = check_deno(prefs)
    return result.path if result.ok else ""


def resolve_mediacap_binary_path(prefs: dict | None = None, bin_dir: str | None = None) -> str:
    result = check_mediacap(prefs, bin_dir)
    return result.path if result.ok else ""


def deno_runtime_args() -> list[str]:
    path = resolve_deno_binary_path()
    args = ["--js-runtimes", f"deno:{path}"] if path else []
    return args + ["--remote-components", "ejs:github"]
