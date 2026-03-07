import os
import sys
import subprocess
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def create_qrc_file() -> Path | None:
    """Generate assets/resources.qrc with paths relative to the assets/ directory."""
    project_root = get_project_root()
    icons_dir = project_root / "assets" / "icons"

    if not icons_dir.is_dir():
        print(f"Icons directory not found: {icons_dir}")
        return None

    icon_files = sorted(
        f.name for f in icons_dir.iterdir()
        if f.is_file()
    )

    if not icon_files:
        print("No icon files found in assets/icons/")
        return None

    # Collect .png files from assets/ root (exclude .ico and .icns)
    assets_dir = project_root / "assets"
    app_images = sorted(
        f.name for f in assets_dir.iterdir()
        if f.is_file() and f.suffix.lower() == '.png'
    )

    lines = ['<RCC>', '  <qresource prefix="icons">']
    for name in icon_files:
        # alias strips the icons/ prefix so Qt path is :/icons/<name>
        lines.append(f'    <file alias="{name}">icons/{name}</file>')
    lines.append('  </qresource>')

    if app_images:
        lines.append('  <qresource prefix="app">')
        for name in app_images:
            lines.append(f'    <file>{name}</file>')
        lines.append('  </qresource>')

    lines += ['</RCC>', '']

    qrc_path = project_root / "assets" / "resources.qrc"
    qrc_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Created {qrc_path}")
    return qrc_path


def compile_qrc(qrc_path: Path) -> bool:
    """Compile the QRC file to src/assets_rc.py using pyside6-rcc."""
    project_root = get_project_root()
    output_file = project_root / "src" / "assets_rc.py"

    try:
        result = subprocess.run(
            ['pyside6-rcc', str(qrc_path), '-o', str(output_file)],
            capture_output=True,
            text=True,
            cwd=str(qrc_path.parent),   # run from assets/ so relative paths resolve
        )
        if result.returncode == 0:
            print(f"Compiled assets to {output_file}")
            return True
        else:
            print(f"Error compiling QRC: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        print("pyside6-rcc not found. Make sure PySide6 is installed.")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("Creating QRC file...")
    qrc = create_qrc_file()
    if qrc is None:
        sys.exit(1)

    print("Compiling QRC to Python resource module...")
    if not compile_qrc(qrc):
        sys.exit(1)
