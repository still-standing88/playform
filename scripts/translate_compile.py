from __future__ import annotations

import argparse
from pathlib import Path

import polib


ROOT_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = ROOT_DIR / "lang"
DOMAIN = "PlayFormDomain"


def _po_files() -> list[Path]:
    if not LOCALE_DIR.exists():
        return []
    return sorted(LOCALE_DIR.glob("*/LC_MESSAGES/*.po"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile gettext PO files into MO files.")
    parser.add_argument("--locale-dir", default=str(LOCALE_DIR))
    args = parser.parse_args()

    locale_dir = Path(args.locale_dir)
    if not locale_dir.exists():
        print(f"Locale directory not found: {locale_dir}")
        return 1

    po_files = sorted(locale_dir.glob("*/LC_MESSAGES/*.po"))
    if not po_files:
        print("No .po files found to compile.")
        return 0

    for po_path in po_files:
        mo_path = po_path.with_suffix(".mo")
        po = polib.pofile(str(po_path))
        mo_path.parent.mkdir(parents=True, exist_ok=True)
        po.save_as_mofile(str(mo_path))
        print(f"Compiled {po_path} -> {mo_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
