from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from app_info import (  # noqa: E402
    APP_AUTHOR,
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_LICENSE,
    APP_NAME,
    APP_PUBLISHER,
    APP_SUPPORT_EMAIL,
    APP_VERSION,
    APP_WEBSITE,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
LANG_DIR = ROOT_DIR / "lang"
DOMAIN = "PlayFormDomain"


def _collect_sources() -> list[Path]:
    excluded_names = {"assets_rc.py", "public_key.py"}
    sources: list[Path] = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if path.name in excluded_names:
            continue
        sources.append(path)
    return sources


def _relative_source_list(sources: list[Path]) -> list[str]:
    return [str(source.relative_to(ROOT_DIR)) for source in sources]


def _build_header() -> str:
    created_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M%z")
    return (
        f"# {APP_NAME} translation template.\n"
        f"# {APP_DESCRIPTION}\n"
        f"# {APP_COPYRIGHT}\n"
        f"# License: {APP_LICENSE}\n"
        f"# Website: {APP_WEBSITE}\n"
        f"# Publisher: {APP_PUBLISHER}\n"
        f"# Author: {APP_AUTHOR}\n"
        f"# Support: {APP_SUPPORT_EMAIL}\n"
        "#\n"
        "msgid \"\"\n"
        "msgstr \"\"\n"
        f"\"Project-Id-Version: {APP_NAME} {APP_VERSION}\\n\"\n"
        f"\"Report-Msgid-Bugs-To: {APP_SUPPORT_EMAIL}\\n\"\n"
        f"\"POT-Creation-Date: {created_at}\\n\"\n"
        "\"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n\"\n"
        f"\"Last-Translator: {APP_AUTHOR} <{APP_SUPPORT_EMAIL}>\\n\"\n"
        f"\"Language-Team: {APP_PUBLISHER} <{APP_SUPPORT_EMAIL}>\\n\"\n"
        "\"MIME-Version: 1.0\\n\"\n"
        "\"Content-Type: text/plain; charset=UTF-8\\n\"\n"
        "\"Content-Transfer-Encoding: 8bit\\n\"\n"
        "\n"
    )


def _rewrite_header(output_path: Path) -> None:
    content = output_path.read_text(encoding="utf-8")
    marker = "\"Content-Transfer-Encoding: 8bit\\n\"\n\n"
    if marker not in content:
        return
    body = content.split(marker, 1)[1]
    body_lines = [line for line in body.splitlines(keepends=True) if not line.startswith("#: ")]
    output_path.write_text(_build_header() + "".join(body_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the gettext POT template.")
    parser.add_argument("--output", default=str(LANG_DIR / f"{DOMAIN}.pot"))
    args = parser.parse_args()

    sources = _collect_sources()
    if not sources:
        print("No Python source files found under src/")
        return 1

    xgettext = "xgettext"
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".txt") as handle:
        for source in _relative_source_list(sources):
            handle.write(f"{source}\n")
        file_list = handle.name

    try:
        cmd = [
            xgettext,
            "--language=Python",
            "--from-code=UTF-8",
            "--keyword=_",
            "--keyword=ngettext:1,2",
            "--sort-output",
            "--no-location",
            "--output",
            str(output_path),
            f"--files-from={file_list}",
        ]
        result = subprocess.run(cmd, cwd=str(ROOT_DIR), check=False)
        if result.returncode != 0:
            print("xgettext failed to generate the POT file.")
            return result.returncode
        _rewrite_header(output_path)
        print(f"Generated {output_path}")
        return 0
    finally:
        try:
            Path(file_list).unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
