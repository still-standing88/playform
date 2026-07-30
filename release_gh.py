import sys
import subprocess
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
REPO = "still-standing88/playform"
TARGET_BRANCH = "develop"
TITLE = "Playform Beta"

NOTES = """## v{version} Release Notes

### Bug fixes

- Player: Fixed a crash when loading a local file while a track is already loaded.
- Player: Fixed the subtitles/chapters accessibility cursor not tracking playback.

### Features

Explorer: Added media database which allows you to easilly search folders for any file after it's indexed. This feature is currently still in beta.
- Explorer: You can now search files in a current folder or sub folders, as well as the database if the folder is indexed in the database.
- Explorer: F5 now refreshes the current list of files in folder.
- Explorer: GUI enhancements, including a toolbar and accessability improvements.

- Player: Added an Equalizer section that enables you to control EQ that's provided by mpv in real time.
- Player: A chapters panel is now available in the player which retrieves chapters when provided by media such as M4B files, as  wel as from Youtube videoes.
- Player: You mey now view metadata for any media using FProbe if available on your machine.
Player: you can now view comments and download subtitles for a youtube video.
- App GUI: Added a Panels toolbar with show/hide and float controls for every pane
"""


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


def get_platform_tag() -> str:
    return platform.system().lower()


def find_assets(version: str, plat: str) -> list[Path]:
    prefix = f"PlayForm-{version}-{plat}"
    zip_name = f"{prefix}.zip"
    app_dist = DIST / "app.dist"
    manifests = sorted(app_dist.glob("*-manifest.json"))

    assets: list[Path] = []

    zip_path = DIST / zip_name
    if zip_path.exists():
        assets.append(zip_path)
    else:
        candidates = sorted(DIST.glob(f"PlayForm-{version}-*.zip"))
        if candidates:
            assets.append(candidates[0])
        else:
            print(f"[warn] No ZIP found matching: {zip_name}")

    if manifests:
        for m in manifests:
            assets.append(m)
    else:
        print(f"[warn] No manifest found in {app_dist}. Run 'inv release' first.")

    if not assets:
        sys.exit(f"No release assets found in {DIST}")

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


def publish_release(version: str, assets: list[Path]) -> None:
    tag = f"v{version}"
    notes = NOTES.format(version=version)
    exists = release_exists(tag)

    if exists:
        print(f"Release {tag} already exists — updating.")
        subprocess.run(
            ["gh", "release", "edit", tag, "--repo", REPO, "--title", TITLE, "--notes", notes],
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
            "--title", TITLE,
            "--notes", notes,
            "--target", TARGET_BRANCH,
        ]
        for a in assets:
            cmd.append(str(a))

        print(f"Creating release {tag} with {len(assets)} asset(s)")
        print(f"  Repo:   {REPO}")
        print(f"  Target: {TARGET_BRANCH}")
        for a in assets:
            print(f"  Asset:  {a.name}")

        subprocess.run(cmd, check=True, cwd=str(ROOT))

    print(f"\nRelease {tag}: https://github.com/{REPO}/releases/tag/{tag}")


def main():
    check_gh()
    version = get_version()
    plat = get_platform_tag()
    assets = find_assets(version, plat)
    publish_release(version, assets)


if __name__ == "__main__":
    main()
