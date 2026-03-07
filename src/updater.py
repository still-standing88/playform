#!/usr/bin/env python3

import os
import sys
import json
import shutil
import hashlib
import zlib
import zipfile
import time
import subprocess
import platform as platform_module
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

try:
    from public_key import PUBLIC_KEY_PEM
except ImportError:
    print("Error: public_key.py not found. Generate it using public_key_generator.py")
    sys.exit(1)


def detect_platform():
    system = platform_module.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    else:
        return 'unknown'


def detect_arch():
    machine = platform_module.machine().lower()
    if machine in ('amd64', 'x86_64'):
        return 'x64'
    elif machine in ('arm64', 'aarch64'):
        return 'arm64'
    elif machine in ('i386', 'i686', 'x86'):
        return 'x86'
    else:
        return machine if machine else 'unknown'


class Logger:
    def __init__(self, log_file="updater.log"):
        self.log_file = log_file
        self.log_handle = open(log_file, 'a', encoding='utf-8')
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)
        self.log_handle.write(log_line + "\n")
        self.log_handle.flush()
    
    def info(self, message):
        self.log(message, "INFO")
    
    def error(self, message):
        self.log(message, "ERROR")
    
    def warning(self, message):
        self.log(message, "WARNING")
    
    def success(self, message):
        self.log(message, "SUCCESS")
    
    def close(self):
        self.log_handle.close()


def calculate_crc32(filepath):
    crc32_value = 0
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            crc32_value = zlib.crc32(chunk, crc32_value)
    return f"{crc32_value & 0xFFFFFFFF:08x}"


def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def calculate_sha512(filepath):
    sha512_hash = hashlib.sha512()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha512_hash.update(chunk)
    return sha512_hash.hexdigest()


def verify_signature(binary_path, sig_path, public_key_pem):
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        
        with open(binary_path, 'rb') as f:
            binary_data = f.read()
        
        with open(sig_path, 'rb') as f:
            signature = f.read()
        
        public_key.verify(
            signature,
            binary_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        raise e


def find_signature_file(filename, temp_path, extract_path):
    sig_filename = filename + '.sig'
    
    temp_sig = temp_path / sig_filename
    if temp_sig.exists():
        return temp_sig
    
    extract_sig = extract_path / sig_filename
    if extract_sig.exists():
        return extract_sig
    
    return None


def create_cleanup_script(old_file, new_updater):
    if sys.platform == "win32":
        script_path = "cleanup_update.bat"
        script_content = f"""@echo off
timeout /t 2 /nobreak >nul
del /f /q "{old_file}" 2>nul
start "" "{new_updater}"
del "%~f0"
"""
    else:
        script_path = "cleanup_update.sh"
        script_content = f"""#!/bin/sh
sleep 2
rm -f "{old_file}"
"{new_updater}" &
rm -f "$0"
"""
    
    with open(script_path, "w") as f:
        f.write(script_content)
    
    if sys.platform != "win32":
        os.chmod(script_path, 0o755)
    
    return script_path


def replace_self_and_restart(logger, new_updater_path, current_updater_path):
    logger.info("Attempting to replace updater with new version...")
    
    old_updater = current_updater_path + ".old"
    
    try:
        if os.path.exists(old_updater):
            os.remove(old_updater)
        
        os.rename(current_updater_path, old_updater)
        logger.info(f"Renamed current updater to: {old_updater}")
    except Exception as e:
        logger.error(f"Could not rename updater: {e}")
        logger.info("Attempting delayed replacement...")
        return delayed_replace(logger, new_updater_path, current_updater_path)
    
    try:
        shutil.copy2(new_updater_path, current_updater_path)
        logger.success(f"Copied new updater to: {current_updater_path}")
    except Exception as e:
        logger.error(f"Failed to copy new updater: {e}")
        os.rename(old_updater, current_updater_path)
        return False
    
    cleanup_script = create_cleanup_script(old_updater, current_updater_path)
    logger.info(f"Created cleanup script: {cleanup_script}")
    
    if sys.platform == "win32":
        subprocess.Popen(["cmd", "/c", cleanup_script], 
                        creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen(["/bin/sh", cleanup_script])
    
    logger.success("Updater replacement initiated. Exiting...")
    logger.close()
    sys.exit(0)


def delayed_replace(logger, new_updater, current_updater):
    if sys.platform == "win32":
        helper_script = "delayed_replace.bat"
        script = f"""@echo off
:wait
timeout /t 1 /nobreak >nul
del /f /q "{current_updater}" 2>nul
if exist "{current_updater}" goto wait
move /y "{new_updater}" "{current_updater}"
start "" "{current_updater}"
del "%~f0"
"""
    else:
        helper_script = "delayed_replace.sh"
        script = f"""#!/bin/sh
while [ -f "{current_updater}" ]; do
    sleep 1
    rm -f "{current_updater}" 2>/dev/null
done
mv "{new_updater}" "{current_updater}"
"{current_updater}" &
rm -f "$0"
"""
    
    with open(helper_script, "w") as f:
        f.write(script)
    
    if sys.platform != "win32":
        os.chmod(helper_script, 0o755)
    
    logger.info(f"Created delayed replacement script: {helper_script}")
    
    if sys.platform == "win32":
        subprocess.Popen(["cmd", "/c", helper_script],
                        creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen(["/bin/sh", helper_script])
    
    logger.success("Delayed replacement initiated. Exiting...")
    logger.close()
    sys.exit(0)


def update(temp_dir, zip_filename, install_dir=None):
    logger = Logger()
    
    logger.info("=" * 60)
    logger.info("Updater started")
    logger.info("=" * 60)
    
    current_platform = detect_platform()
    logger.info(f"Detected platform: {current_platform}")
    current_arch = detect_arch()
    logger.info(f"Detected arch: {current_arch}")
    
    if install_dir is None:
        install_dir = Path(__file__).parent
    else:
        install_dir = Path(install_dir)
    
    temp_path = Path(temp_dir)
    zip_path = temp_path / zip_filename
    
    logger.info(f"Install directory: {install_dir}")
    logger.info(f"Temporary directory: {temp_path}")
    logger.info(f"Update archive: {zip_path}")
    
    if not temp_path.exists():
        logger.error(f"Temporary directory not found: {temp_path}")
        logger.close()
        return False
    
    if not zip_path.exists():
        logger.error(f"Update archive not found: {zip_path}")
        logger.close()
        return False
    
    logger.info("Public key loaded from public_key.py")
    
    zip_sig_path = Path(str(zip_path) + '.sig')
    if zip_sig_path.exists():
        logger.info("Found archive signature file, verifying...")
        if verify_signature(zip_path, zip_sig_path, PUBLIC_KEY_PEM):
            logger.success("Archive signature verified successfully")
        else:
            logger.error("Archive signature verification failed!")
            logger.close()
            return False
    else:
        logger.warning("No archive signature found, skipping archive validation")
    
    extract_path = temp_path / "extracted"
    
    if extract_path.exists():
        logger.warning(f"Extract directory exists, removing: {extract_path}")
        shutil.rmtree(extract_path)
    
    extract_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created extract directory: {extract_path}")
    
    logger.info("Extracting update archive...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        logger.success("Archive extracted successfully")
    except Exception as e:
        logger.error(f"Failed to extract archive: {e}")
        logger.close()
        return False
    
    manifest_filename = f"{current_platform}-{current_arch}-manifest.json"
    manifest_path = temp_path / manifest_filename
    
    if not manifest_path.exists():
        logger.error(f"Platform manifest not found: {manifest_filename}")
        logger.close()
        return False
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    logger.info(f"Manifest loaded: {manifest_filename}")
    logger.info(f"Version: {manifest['version']}")
    logger.info(f"Files to validate: {len(manifest['files'])}")
    
    updater_file = None
    current_updater = Path(sys.argv[0]).resolve()
    
    for file_entry in manifest['files']:
        file_path = extract_path / file_entry['path']
        
        if not file_path.exists():
            logger.error(f"File not found in archive: {file_entry['path']}")
            logger.close()
            return False
        
        logger.info(f"Validating: {file_entry['path']}")
        
        if 'crc32' in file_entry:
            actual_crc32 = calculate_crc32(file_path)
            if actual_crc32 != file_entry['crc32']:
                logger.error(f"CRC32 mismatch for {file_entry['path']}")
                logger.error(f"Expected: {file_entry['crc32']}, Got: {actual_crc32}")
                logger.close()
                return False
            logger.success(f"CRC32 verified: {file_entry['path']}")
        
        if 'sha256' in file_entry:
            actual_sha256 = calculate_sha256(file_path)
            if actual_sha256 != file_entry['sha256']:
                logger.error(f"SHA256 mismatch for {file_entry['path']}")
                logger.error(f"Expected: {file_entry['sha256']}, Got: {actual_sha256}")
                logger.close()
                return False
            logger.success(f"SHA256 verified: {file_entry['path']}")
        
        if 'sha512' in file_entry:
            actual_sha512 = calculate_sha512(file_path)
            if actual_sha512 != file_entry['sha512']:
                logger.error(f"SHA512 mismatch for {file_entry['path']}")
                logger.error(f"Expected: {file_entry['sha512']}, Got: {actual_sha512}")
                logger.close()
                return False
            logger.success(f"SHA512 verified: {file_entry['path']}")
        
        if file_entry.get('has_signature', False):
            sig_path = find_signature_file(file_path.name, temp_path, extract_path)
            
            if sig_path is None:
                logger.error(f"Signature file not found for {file_entry['path']}")
                logger.close()
                return False
            
            logger.info(f"Found signature at: {sig_path}")
            
            if not verify_signature(file_path, sig_path, PUBLIC_KEY_PEM):
                logger.error(f"Signature verification failed for {file_entry['path']}")
                logger.close()
                return False
            logger.success(f"Signature verified: {file_entry['path']}")
        
        if file_path.resolve() == current_updater or file_path.name == current_updater.name:
            updater_file = file_path
            logger.info(f"Detected updater file: {file_entry['path']}")
    
    logger.info("All files validated successfully")
    logger.info("Beginning file replacement...")
    
    for file_entry in manifest['files']:
        file_path = extract_path / file_entry['path']
        dest_path = install_dir / file_entry['path']
        
        if file_path == updater_file:
            logger.info(f"Skipping updater (will replace later): {file_entry['path']}")
            continue
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.copy2(file_path, dest_path)
            logger.success(f"Replaced: {file_entry['path']}")
        except Exception as e:
            logger.error(f"Failed to replace {file_entry['path']}: {e}")
            logger.close()
            return False
    
    logger.success("All files replaced successfully")
    
    if updater_file:
        replace_self_and_restart(logger, updater_file, str(current_updater))
    
    logger.success("Update completed successfully")
    logger.close()
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Cross-platform updater with validation')
    parser.add_argument('--temp', '-t', required=True, help='Temporary directory path containing zip and manifest')
    parser.add_argument('--zip', '-z', required=True, help='Zip filename (in temp directory)')
    parser.add_argument('--install-dir', '-i', help='Installation directory (default: script directory)')
    
    args = parser.parse_args()
    
    success = update(args.temp, args.zip, args.install_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
