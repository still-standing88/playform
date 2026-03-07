from invoke.tasks import task
from invoke_config import *

import os
import platform as _platform
import shutil

import build


@task
def keygen(c, destination="./keys"):
    """Generate RSA-4096 keypair for code signing
    
    Args:
        destination: Destination folder for keys (default: ./keys)
    """
    print(f"Generating keypair in {destination}...")
    c.run(f"python {SCRIPTS_DIR / 'keygen.py'} -d {destination}", pty=False, in_stream=False)


@task
def generate_public_key(c, key_path, destination="./src"):
    """Generate public key module from PEM file
    
    Args:
        key_path: Path to public_key.pem
        destination: Destination folder for public_key.py (default: ./src)
    """
    print(f"Generating public key module...")
    c.run(f"python {SCRIPTS_DIR / 'public_key_generator.py'} -k {key_path} -d {destination}", pty=False, in_stream=False)


@task
def checksums(c, file_path, output_dir=None):
    """Generate checksums (CRC32, SHA256, SHA512) for a file
    
    Args:
        file_path: File to generate checksums for
        output_dir: Output directory for checksum files (optional)
    """
    cmd = f"python {SCRIPTS_DIR / 'checksums.py'} -f {file_path}"
    if output_dir:
        cmd += f" -o {output_dir}"
    c.run(cmd, pty=False, in_stream=False)


@task
def sign(c, binary, key, output):
    """Sign a binary file with private key
    
    Args:
        binary: Binary file to sign
        key: Private key file (PEM)
        output: Output signature file
    """
    print(f"Signing {binary}...")
    c.run(f"python {SCRIPTS_DIR / 'sign.py'} -b {binary} -k {key} -o {output}", pty=False, in_stream=False)


@task
def manifest(c, folder, version, platform=None, arch=None, output=None):
    """Generate update manifest

    Args:
        folder: Folder containing release files
        version: Version string (e.g., 1.0.0)
        platform: Target platform (windows/linux/macos, auto-detect if not specified)
        arch: Target architecture (x64/arm64/x86, auto-detect if not specified)
        output: Output manifest file path (optional)
    """
    cmd = f"python {SCRIPTS_DIR / 'manifest_gen.py'} -f {folder} -v {version}"
    if platform:
        cmd += f" -p {platform}"
    if arch:
        cmd += f" -a {arch}"
    if output:
        cmd += f" -o {output}"
    c.run(cmd, pty=False, in_stream=False)


@task
def clean(c):
    """Remove build artifacts and cache files"""
    print("Cleaning build artifacts...")
    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        #"**/*.pyd",
        "*.egg-info",
        "build/",
        #"dist/",
        ".nuitka/"
    ]
    
    for pattern in patterns:
        if sys.platform == "win32":
            c.run(f'powershell -Command "Remove-Item -Recurse -Force {pattern} -ErrorAction SilentlyContinue"', pty=False, in_stream=False, warn=True)
        else:
            c.run(f"rm -rf {pattern}", pty=False, in_stream=False, warn=True)
    
    print("Clean complete!")


@task
def package_windows(c, version=build.APP_VERSION, source_dir=None, output_dir=None):
    """Build a Windows MSI installer using WiX Toolset

    Args:
        version: Version string (e.g., 1.0.0)
        source_dir: Compiled app dist folder (default: dist/app.dist)
        output_dir: Folder where the .msi will be placed (default: dist/installer)
    """
    if _platform.system().lower() != "windows":
        print("Error: package_windows must be run on Windows.")
        return

    app_dist = source_dir or str(ROOT_DIR / "dist" / "app.dist")
    out_dir = output_dir or str(ROOT_DIR / "dist" / "installer")

    os.makedirs(out_dir, exist_ok=True)

    script = ROOT_DIR / "installer" / "windows" / "build-msi.ps1"
    cmd = (
        f'powershell -ExecutionPolicy Bypass -File "{script}"'
        f' -SourceDir "{app_dist}"'
        f' -OutputDir "{out_dir}"'
        f' -Version "{version}"'
    )
    print(f"Building MSI installer for version {version}...")
    c.run(cmd, pty=False, in_stream=False)
    print(f"MSI installer output: {out_dir}")


@task
def package_macos(c, version=build.APP_VERSION, app_name=build.APP_NAME, arch=None, output_dir=None):
    """Create a macOS DMG installer using create-dmg

    Args:
        version: Version string (e.g., 1.0.0)
        app_name: Application name (default: APP_NAME)
        arch: Architecture tag for the DMG filename (e.g., x64, arm64; auto-detect if omitted)
        output_dir: Folder where the .dmg will be placed (default: dist)
    """
    if _platform.system().lower() != "darwin":
        print("Error: package_macos must be run on macOS.")
        return

    if arch is None:
        machine = _platform.machine().lower()
        if machine in ("arm64", "aarch64"):
            arch = "arm64"
        else:
            arch = "x64"

    out_dir = output_dir or str(ROOT_DIR / "dist")
    app_bundle = ROOT_DIR / "dist" / f"{app_name}.app"

    if not app_bundle.exists():
        print(f"Error: App bundle not found: {app_bundle}")
        return

    dmg_staging = ROOT_DIR / "dist" / "dmg"
    shutil.rmtree(str(dmg_staging), ignore_errors=True)
    os.makedirs(str(dmg_staging), exist_ok=True)
    shutil.copytree(str(app_bundle), str(dmg_staging / f"{app_name}.app"))

    dmg_name = f"{app_name}-{version}-{arch}.dmg"
    dmg_path = os.path.join(out_dir, dmg_name)

    c.run("which create-dmg || brew install create-dmg", pty=False, in_stream=False, warn=True)

    cmd = (
        f'create-dmg'
        f' --volname "{app_name}"'
        f' --window-pos 200 120'
        f' --window-size 600 300'
        f' --icon-size 100'
        f' --icon "{app_name}.app" 175 120'
        f' --hide-extension "{app_name}.app"'
        f' --app-drop-link 425 120'
        f' "{dmg_path}"'
        f' "{dmg_staging}/"'
    )
    print(f"Creating DMG: {dmg_name}...")
    c.run(cmd, pty=False, in_stream=False)
    print(f"DMG created: {dmg_path}")

