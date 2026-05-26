from __future__ import annotations

import argparse
from pathlib import Path

import polib


ROOT_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = ROOT_DIR / "lang"
DOMAIN = "PlayFormDomain"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new gettext PO file for a language.")
    parser.add_argument("language", help="Language code, for example fr, es, ar, or de_DE")
    parser.add_argument("--template", default=str(LOCALE_DIR / f"{DOMAIN}.pot"))
    args = parser.parse_args()

    language = str(args.language).strip()
    if not language:
        print("Language code is required.")
        return 1

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        return 1

    po_path = LOCALE_DIR / language / "LC_MESSAGES" / f"{DOMAIN}.po"
    if po_path.exists():
        print(f"Translation already exists: {po_path}")
        return 0

    po = polib.pofile(str(template_path))
    po.metadata["Language"] = language
    po.metadata["Language-Team"] = language
    po.metadata.setdefault("Content-Type", "text/plain; charset=UTF-8")
    po_path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(po_path))
    print(f"Created {po_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
