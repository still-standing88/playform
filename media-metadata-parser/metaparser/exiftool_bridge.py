"""Subprocess wrapper around the bundled ExifTool.exe.

This is a dev-time cross-check oracle ONLY — it is never imported by
extractor.py or anything in metaparser/tags/, and must not become a runtime
dependency. Per plan.md's testing approach: run `-j` over a file, diff the
JSON against this package's own output via `diff_against` below, and treat
any disagreement as a bug in *our* code to chase, not a shrug. The module's
own extraction logic (chunk walkers + interpreters, plus mutagen for the
"solved problem" tag formats) must stand on its own without this binary —
mutagen is the only accepted third-party dependency for actual extraction.

`extract_json` is defensive on purpose (any failure — missing binary, bad
JSON, non-zero exit — returns None rather than raising) because it's meant
to be called from ad-hoc validation scripts during development, where one
bad file shouldn't kill a batch comparison run.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_EXIFTOOL = Path(__file__).parent.parent / "exiftool-13.59_64" / "ExifTool.exe"


class ExifToolError(Exception):
    pass


def _resolve_exiftool_path(exiftool_path: str | Path | None) -> Path | None:
    candidate = Path(exiftool_path) if exiftool_path else _DEFAULT_EXIFTOOL
    if not candidate.is_file():
        logger.warning("ExifTool binary not found at %s", candidate)
        return None
    return candidate


def extract_json(path: str | Path, exiftool_path: str | Path | None = None) -> dict | None:
    """Runs `exiftool -j -G <file>` and returns the single-file result dict,
    or None on any failure (missing binary, timeout, non-zero exit, bad
    JSON). `-G` prefixes tag names with their group (e.g. `RIFF:Genre`,
    `XML:CatID`) so callers can tell which container the tag actually came
    from instead of guessing from the bare name.
    """
    exe = _resolve_exiftool_path(exiftool_path)
    if exe is None:
        return None

    path = Path(path)
    try:
        result = subprocess.run(
            [str(exe), "-j", "-G", "-a", str(path)],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("exiftool subprocess failed for %s: %s", path, exc)
        return None

    if result.returncode != 0:
        logger.warning(
            "exiftool exited %d for %s: %s", result.returncode, path, result.stderr.decode(errors="replace")[:500]
        )
        return None

    try:
        parsed = json.loads(result.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        logger.warning("exiftool produced unparseable JSON for %s: %s", path, exc)
        return None

    if not parsed:
        return None
    return parsed[0]


def diff_against(path: str | Path, own_flat_metadata: dict[str, str]) -> dict:
    """Dev-time cross-check: compares this package's own flattened metadata
    (tag_name -> value, as strings) against exiftool's output for the same
    file. Returns {only_in_own, only_in_exiftool, value_mismatches,
    agreements_count} — a diff report, not a pass/fail, since exiftool's tag
    naming won't line up 1:1 with ours and that's expected, not a bug by
    itself. Use this while building interpreters against real sample files,
    per plan.md's testing approach.
    """
    exif_data = extract_json(path)
    if exif_data is None:
        return {"error": "exiftool extraction failed or binary unavailable"}

    exif_lower = {k.split(":")[-1].lower(): str(v) for k, v in exif_data.items()}
    own_lower = {k.lower(): str(v) for k, v in own_flat_metadata.items()}

    only_in_own = sorted(set(own_lower) - set(exif_lower))
    only_in_exiftool = sorted(set(exif_lower) - set(own_lower))
    shared = set(own_lower) & set(exif_lower)

    mismatches = {}
    agreements = 0
    for key in shared:
        if own_lower[key].strip() == exif_lower[key].strip():
            agreements += 1
        else:
            mismatches[key] = {"own": own_lower[key], "exiftool": exif_lower[key]}

    return {
        "only_in_own": only_in_own,
        "only_in_exiftool": only_in_exiftool,
        "value_mismatches": mismatches,
        "agreements_count": agreements,
    }
