from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
LANG_DIR = ROOT_DIR / "lang"
DOMAIN = "PlayFormDomain"


def _po_paths(languages: list[str]) -> list[Path]:
    if languages:
        return [LANG_DIR / language / "LC_MESSAGES" / f"{DOMAIN}.po" for language in languages]
    return sorted(LANG_DIR.glob(f"*/LC_MESSAGES/{DOMAIN}.po"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge the POT template into existing PO catalogs, keeping current translations."
    )
    parser.add_argument("languages", nargs="*", help="Language codes to merge, for example fr ar")
    parser.add_argument("--template", default=str(LANG_DIR / f"{DOMAIN}.pot"))
    parser.add_argument("--fuzzy-matching", action="store_true",
                        help="Let msgmerge guess translations for changed strings (marked fuzzy).")
    args = parser.parse_args()

    template = Path(args.template)
    if not template.exists():
        print(f"Template not found: {template}")
        return 1

    msgmerge = shutil.which("msgmerge")
    if not msgmerge:
        print("msgmerge was not found on PATH. Install the gettext tools first.")
        return 1

    po_paths = _po_paths(args.languages)
    if not po_paths:
        print("No .po files found to merge.")
        return 0

    for po_path in po_paths:
        if not po_path.exists():
            print(f"Missing translation catalog: {po_path}")
            return 1

        cmd = [msgmerge, "--update", "--backup=none", "--no-location", "--no-wrap"]
        if not args.fuzzy_matching:
            cmd.append("--no-fuzzy-matching")
        cmd += [str(po_path), str(template)]

        result = subprocess.run(cmd, cwd=str(ROOT_DIR), check=False)
        if result.returncode != 0:
            print(f"msgmerge failed for {po_path}")
            return result.returncode
        print(f"Merged {template.name} -> {po_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
