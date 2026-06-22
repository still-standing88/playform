"""Compile Markdown documentation under docs/source/<lang>/ to HTML under docs/build/<lang>/.

Uses:
  - Python-Markdown with:
      mdx_truly_sane_lists  (consistent indentation-tolerant lists)
      markdown-link-attr-modifier  (add rel=noopener to external links)
      toc                    (table of contents)
      fenced_code / codehilite / tables  (built-in)
  - nh3  (HTML sanitisation)
"""

import sys
import os
import shutil
from pathlib import Path
from typing import List

import markdown
from mdx_truly_sane_lists.mdx_truly_sane_lists import TrulySaneListExtension
from markdown_link_attr_modifier import LinkAttrModifierExtension
import nh3


ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_SOURCE = ROOT_DIR / "docs" / "source"
DOCS_BUILD  = ROOT_DIR / "docs" / "build"
TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    max-width: 960px;
    margin: 0 auto;
    padding: 20px 24px;
    line-height: 1.7;
    color: #1a1a1a;
    background: #fff;
  }}
  h1 {{ font-size: 2em; border-bottom: 2px solid #e0e0e0; padding-bottom: .3em; }}
  h2 {{ font-size: 1.5em; border-bottom: 1px solid #e8e8e8; padding-bottom: .2em; margin-top: 1.8em; }}
  h3 {{ font-size: 1.25em; margin-top: 1.4em; }}
  h4 {{ font-size: 1.1em; }}
  code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 0.94em; }}
  pre {{ background: #2d2d2d; color: #f8f8f2; padding: 16px; border-radius: 6px; overflow-x: auto; font-size: 0.92em; line-height: 1.5; }}
  pre code {{ background: none; padding: 0; color: inherit; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  blockquote {{ border-left: 3px solid #ccc; margin: 1em 0; padding: 0.5em 1em; color: #555; background: #f9f9f9; }}
  a {{ color: #0366d6; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  img {{ max-width: 100%; }}
  hr {{ border: 0; border-top: 1px solid #e0e0e0; margin: 2em 0; }}
  ul, ol {{ padding-left: 1.5em; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #d0d0d0; background: #1a1a1a; }}
    h1 {{ border-color: #444; }}
    h2 {{ border-color: #3a3a3a; }}
    code {{ background: #333; color: #e0e0e0; }}
    pre {{ background: #111; }}
    th {{ background: #2a2a2a; }}
    tr:nth-child(even) {{ background: #222; }}
    td, th {{ border-color: #444; }}
    blockquote {{ background: #222; border-color: #555; color: #bbb; }}
    a {{ color: #58a6ff; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def find_md_files(lang: str) -> List[Path]:
    """Return all .md files under docs/source/<lang>/ sorted by depth then name."""
    src_dir = DOCS_SOURCE / lang
    if not src_dir.is_dir():
        print(f"[warn] Source dir not found: {src_dir}")
        return []
    return sorted(src_dir.rglob("*.md"), key=lambda p: (len(p.relative_to(src_dir).parts), p.name))


def compile_md(md_path: Path, lang: str) -> str:
    """Convert a single .md file to HTML body fragment."""
    text = md_path.read_text(encoding="utf-8")

    md = markdown.Markdown(
        extensions=[
            TrulySaneListExtension(),
            LinkAttrModifierExtension(),
            "toc",
            "fenced_code",
            "codehilite",
            "tables",
            "nl2br",
        ],
        extension_configs={
            "toc": {
                "permalink": False,
                "toc_depth": "3-3",
            },
        },
        output_format="html5",
    )
    raw_html = md.convert(text)
    sanitised = nh3.clean(
        raw_html,
        link_rel=None,
        tags={
            "h1", "h2", "h3", "h4", "h5", "h6",
            "p", "br", "hr",
            "ul", "ol", "li",
            "a", "img",
            "strong", "em", "b", "i", "u", "s", "del", "ins",
            "code", "pre",
            "table", "thead", "tbody", "tfoot", "tr", "th", "td",
            "blockquote",
            "div", "span",
            "sub", "sup", "small", "mark",
            "dl", "dt", "dd",
            "details", "summary",
        },
        attributes={
            "*": {"id", "class", "style"},
            "a": {"href", "title", "rel", "target"},
            "img": {"src", "alt", "title", "width", "height"},
            "td": {"colspan", "rowspan"},
            "th": {"colspan", "rowspan"},
        },
    )
    # Determine a title — use first h1 text from the sanitised HTML, or file stem
    import re
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", sanitised)
    title = title_match.group(1) if title_match else md_path.stem
    # Strip any embedded tags from the title
    title = re.sub(r"<[^>]+>", "", title)

    return TEMPLATE.format(lang=lang, title=title, body=sanitised)


def copy_assets(src_lang_dir: Path, dst_lang_dir: Path):
    """Copy non-.md files from source to build dir."""
    for item in src_lang_dir.rglob("*"):
        if item.is_dir():
            continue
        if item.suffix.lower() == ".md":
            continue
        rel = item.relative_to(src_lang_dir)
        dest = dst_lang_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(item), str(dest))
        print(f"  copied asset: {rel}")


def compile_all(lang: str):
    """Compile all .md files for a given language."""
    src_dir = DOCS_SOURCE / lang
    dst_dir = DOCS_BUILD / lang

    if not src_dir.exists():
        print(f"[warn] docs/source/{lang}/ does not exist, skipping.")
        return

    if dst_dir.exists():
        shutil.rmtree(str(dst_dir))

    dst_dir.mkdir(parents=True, exist_ok=True)

    md_files = find_md_files(lang)
    if not md_files:
        print(f"[warn] No .md files found for lang={lang}")
        return

    print(f"Compiling {len(md_files)} Markdown file(s) for [{lang}]...")
    for md_path in md_files:
        rel_path = md_path.relative_to(src_dir)
        html = compile_md(md_path, lang)
        out_path = dst_dir / rel_path.with_suffix(".html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        print(f"  {rel_path}  ->  {out_path.relative_to(DOCS_BUILD)}")

    copy_assets(src_dir, dst_dir)
    print(f"Done [{lang}] -> {dst_dir}")


def main():
    langs = os.environ.get("DOCS_LANGS", "")
    if langs:
        lang_list = [l.strip() for l in langs.split(",") if l.strip()]
    else:
        args = sys.argv[1:]
        if args:
            lang_list = args
        else:
            # Default: every subdirectory of docs/source/
            lang_list = [
                d.name for d in DOCS_SOURCE.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]

    if not lang_list:
        # Fallback: if docs/source exists but no subdirs, try 'en'
        if DOCS_SOURCE.exists():
            lang_list = ["en"]
        else:
            print("[warn] No docs/source directory found.")
            return

    print(f"Compiling documentation for languages: {lang_list}")
    for lang in lang_list:
        compile_all(lang)
        print()

    print("All documentation compiled.")


if __name__ == "__main__":
    main()
