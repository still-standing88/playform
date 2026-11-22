import sys
import json
import subprocess
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
REPO = "still-standing88/playform"
TARGET_BRANCH = "develop"
TITLE = "PlayForm Beta"
NOTES_FILE = ROOT / "change-log.md"


def get_version() -> str:
    src_app_info = ROOT / "src" / "app_info.py"
    if src_app_info.exists():
        text = src_app_info.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("APP_VERSION"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    build_py = ROOT / "build.py"
    if build_py.exists():
        text = build_py.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("APP_VERSION"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("Could not determine version from app_info.py or build.py")


def get_notes(version: str) -> str:
    if not NOTES_FILE.exists():
        sys.exit(f"Change log not found: {NOTES_FILE}")
    notes = NOTES_FILE.read_text(encoding="utf-8").strip()
    if not notes:
        sys.exit(f"Change log is empty: {NOTES_FILE}")
    lines = notes.splitlines()
    heading = f"## v{version} Release Notes"
    try:
        start = lines.index(heading)
    except ValueError:
        sys.exit(f"Release notes for v{version} not found in {NOTES_FILE}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end]).strip() + "\n"


def get_platform_tag() -> str:
    return platform.system().lower()


def find_assets(version: str, plat: str) -> list[Path]:
    prefix = f"PlayForm-{version}-{plat}"
    zip_name = f"{prefix}.zip"
    app_dist = DIST / "app.dist"
    manifests = sorted(app_dist.glob("*-manifest.json"))

    zip_path = DIST / zip_name
    if not zip_path.is_file():
        sys.exit(f"Release ZIP not found: {zip_path}. Run 'inv bundle' first.")
    assets: list[Path] = [zip_path]

    if plat == "windows":
        msi_path = DIST / "installer" / f"PlayForm-{version}.msi"
        if not msi_path.is_file():
            sys.exit(f"Release MSI not found: {msi_path}. Run 'inv package-windows' first.")
        assets.append(msi_path)

    if not manifests:
        sys.exit(f"No update manifest found in {app_dist}. Run 'inv release' first.")
    for manifest in manifests:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("version") != version:
            sys.exit(f"Manifest version does not match v{version}: {manifest}")
        assets.append(manifest)

    return assets


def check_gh() -> None:
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("GitHub CLI (gh) not found. Install from https://cli.github.com/")


def release_exists(tag: str) -> bool:
    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", REPO],
        capture_output=True,
    )
    return result.returncode == 0


def publish_release(version: str, notes: str, assets: list[Path]) -> None:
    tag = f"v{version}"
    title = f"{TITLE} {tag}"
    exists = release_exists(tag)

    if exists:
        print(f"Release {tag} already exists - updating.")
        subprocess.run(
            ["gh", "release", "edit", tag, "--repo", REPO,
             "--title", title, "--notes-file", "-"],
            input=notes,
            text=True,
            check=True,
            cwd=str(ROOT),
        )
        for a in assets:
            print(f"  Uploading: {a.name}")
            subprocess.run(
                ["gh", "release", "upload", tag, str(a), "--repo", REPO, "--clobber"],
                check=True,
                cwd=str(ROOT),
            )
    else:
        cmd = [
            "gh", "release", "create", tag,
            "--repo", REPO,
            "--title", title,
            "--notes-file", "-",
            "--target", TARGET_BRANCH,
        ]
        for a in assets:
            cmd.append(str(a))

        print(f"Creating release {tag} with {len(assets)} asset(s)")
        print(f"  Repo:   {REPO}")
        print(f"  Target: {TARGET_BRANCH}")
        print(f"  Notes:  {NOTES_FILE.name} ({len(notes)} chars)")
        for a in assets:
            print(f"  Asset:  {a.name}")

        subprocess.run(cmd, input=notes, text=True, check=True, cwd=str(ROOT))

    print(f"\nRelease {tag}: https://github.com/{REPO}/releases/tag/{tag}")


def main():
    check_gh()
    version = get_version()
    notes = get_notes(version)
    plat = get_platform_tag()
    assets = find_assets(version, plat)
    publish_release(version, notes, assets)


if __name__ == "__main__":
    main()
