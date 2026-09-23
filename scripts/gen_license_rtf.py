#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"

sys.path.insert(0, str(SRC_DIR))

import app_info


def _escape(text: str) -> str:
    escaped = []
    for char in text:
        if char == "\\":
            escaped.append("\\\\")
        elif char in "{}":
            escaped.append("\\" + char)
        elif ord(char) > 127:
            codepoint = ord(char)
            if codepoint > 32767:
                codepoint -= 65536
            escaped.append(f"\\u{codepoint}?")
        else:
            escaped.append(char)
    return "".join(escaped)


def _paragraph(text: str, size: str = "fs18", bold: bool = False) -> str:
    indent = len(text) - len(text.lstrip(" "))
    body = _escape(text.strip())
    bold_on = "\\b " if bold else ""
    bold_off = "\\b0 " if bold else ""
    # Leading spaces ride as non-breaking spaces so the license's own
    # indentation survives the rich-edit control.
    lead = "\\~" * indent
    return f"\\pard\\fi0\\li0\\{size} {bold_on}{lead}{body}{bold_off}\\par"


def build_rtf(gpl_text: str) -> str:
    name = app_info.APP_NAME
    notice = [
        (f"{name} - {app_info.APP_DESCRIPTION}", "fs32", True),
        (f"{app_info.APP_COPYRIGHT}. Published by {app_info.APP_PUBLISHER}.", "fs20", False),
        ("", "fs18", False),
        ("This program is free software: you can redistribute it and/or modify", "fs20", False),
        ("it under the terms of the GNU General Public License as published by", "fs20", False),
        ("the Free Software Foundation, either version 3 of the License, or", "fs20", False),
        ("(at your option) any later version.", "fs20", False),
        ("", "fs20", False),
        ("This program is distributed in the hope that it will be useful,", "fs20", False),
        ("but WITHOUT ANY WARRANTY; without even the implied warranty of", "fs20", False),
        ("MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the", "fs20", False),
        ("GNU General Public License below for more details.", "fs20", False),
        ("", "fs20", False),
        (f"Full license text: https://www.gnu.org/licenses/gpl-3.0.html", "fs20", False),
        (f"Source code: {app_info.APP_WEBSITE}", "fs20", False),
        (f"Support: {app_info.APP_SUPPORT_EMAIL}", "fs20", False),
        ("", "fs20", False),
        ("-" * 96, "fs20", False),
        ("", "fs20", False),
    ]

    lines = [
        "{\\rtf1\\ansi\\ansicpg1252\\deff0",
        "{\\fonttbl{\\f0\\fswiss\\fcharset0 Segoe UI;}}",
        "\\viewkind4\\uc1",
    ]
    lines.append("\\pard\\f0\\sb0\\sa120")
    lines.extend(_paragraph(text, size, bold) for text, size, bold in notice)
    lines.append("\\pard\\sb0\\sa0")
    lines.extend(_paragraph(line, "fs18") for line in gpl_text.splitlines())
    lines.append("}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate the installer's license RTF from the vendored GPL-3.0 text")
    parser.add_argument("--text", default=str(ROOT_DIR / "installer" / "windows" / "gpl-3.0.txt"),
                        help="Verbatim GPL text file")
    parser.add_argument("--output", "-o", default=str(ROOT_DIR / "installer" / "windows" / "License.rtf"),
                        help="Destination RTF file")
    args = parser.parse_args()

    text_file = Path(args.text)
    if not text_file.exists():
        print(f"Error: GPL text not found: {text_file}")
        return 1

    gpl_text = text_file.read_text(encoding="utf-8")

    output_file = Path(args.output)
    with open(output_file, "w", encoding="ascii", newline="\r\n") as f:
        f.write(build_rtf(gpl_text))

    print(f"License RTF generated: {output_file} ({len(gpl_text.splitlines())} lines from {text_file.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
