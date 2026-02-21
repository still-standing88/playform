from invoke.tasks import task
from invoke_config import *

import build


@task
def keygen(c, destination="./keys"):
    """Generate RSA-4096 keypair for code signing
    
    Args:
        destination: Destination folder for keys (default: ./keys)
    """
    print(f"Generating keypair in {destination}...")
    c.run(f"python {SCRIPTS_DIR / 'keygen.py'} -d {destination}", pty=False)


@task
def generate_public_key(c, key_path, destination="./src"):
    """Generate public key module from PEM file
    
    Args:
        key_path: Path to public_key.pem
        destination: Destination folder for public_key.py (default: ./src)
    """
    print(f"Generating public key module...")
    c.run(f"python {SCRIPTS_DIR / 'public_key_generator.py'} -k {key_path} -d {destination}", pty=False)


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
    c.run(cmd, pty=False)


@task
def sign(c, binary, key, output):
    """Sign a binary file with private key
    
    Args:
        binary: Binary file to sign
        key: Private key file (PEM)
        output: Output signature file
    """
    print(f"Signing {binary}...")
    c.run(f"python {SCRIPTS_DIR / 'sign.py'} -b {binary} -k {key} -o {output}", pty=False)


@task
def manifest(c, folder, version, platform=None, output=None):
    """Generate update manifest
    
    Args:
        folder: Folder containing release files
        version: Version string (e.g., 1.0.0)
        platform: Target platform (windows/linux/macos, auto-detect if not specified)
        output: Output manifest file path (optional)
    """
    cmd = f"python {SCRIPTS_DIR / 'manifest_gen.py'} -f {folder} -v {version}"
    if platform:
        cmd += f" -p {platform}"
    if output:
        cmd += f" -o {output}"
    c.run(cmd, pty=False)


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
            c.run(f'powershell -Command "Remove-Item -Recurse -Force {pattern} -ErrorAction SilentlyContinue"', warn=True)
        else:
            c.run(f"rm -rf {pattern}", warn=True)
    
    print("Clean complete!")


@task
def release_build(c, version, platform=None):
    """Complete release build pipeline
    
    Args:
        version: Version string (e.g., 1.0.0)
        platform: Target platform (windows/linux/macos, auto-detect if not specified)
    """
    print(f"Starting release build for version {version}...")
    
    clean(c)
    build.compile_assets(c)
    build.build(c, platform=platform)


    # sign(c, "dist/PlayForm.exe", "keys/private_key.pem", "dist/PlayForm.exe.sig")
    # checksums(c, "dist/PlayForm.exe", "dist/")
    # manifest(c, "dist/", version, platform=platform)
    
    print(f"\nRelease build {version} complete!")

