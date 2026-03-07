#!/usr/bin/env python3

import argparse
import json
import os
import sys
import platform
from pathlib import Path


def detect_platform():
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    else:
        return 'unknown'


def detect_arch():
    machine = platform.machine().lower()
    if machine in ('amd64', 'x86_64'):
        return 'x64'
    elif machine in ('arm64', 'aarch64'):
        return 'arm64'
    elif machine in ('i386', 'i686', 'x86'):
        return 'x86'
    else:
        return machine if machine else 'unknown'


def load_checksum_file(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read().strip()
    return None


def find_all_files(folder_path):
    all_files = {}
    for root, dirs, filenames in os.walk(folder_path):
        for filename in filenames:
            full_path = Path(root) / filename
            if filename not in all_files:
                all_files[filename] = []
            all_files[filename].append(full_path)
    return all_files


def scan_folder(folder_path):
    all_files = find_all_files(folder_path)
    
    tracked_files = {}
    
    for filename, paths in all_files.items():
        if filename.endswith('-manifest.json'):
            continue
            
        if filename.endswith('.sig'):
            base_name = filename[:-4]
            if base_name not in tracked_files:
                tracked_files[base_name] = {}
            tracked_files[base_name]['sig_file'] = paths[0]
        
        elif filename.endswith('.crc32'):
            base_name = filename[:-6]
            if base_name not in tracked_files:
                tracked_files[base_name] = {}
            tracked_files[base_name]['crc32_file'] = paths[0]
        
        elif filename.endswith('.sha256'):
            base_name = filename[:-7]
            if base_name not in tracked_files:
                tracked_files[base_name] = {}
            tracked_files[base_name]['sha256_file'] = paths[0]
        
        elif filename.endswith('.sha512'):
            base_name = filename[:-7]
            if base_name not in tracked_files:
                tracked_files[base_name] = {}
            tracked_files[base_name]['sha512_file'] = paths[0]
    
    for base_name in tracked_files.keys():
        if base_name in all_files:
            tracked_files[base_name]['binary_path'] = all_files[base_name][0]
    
    manifest_files = []
    
    for base_name, file_data in tracked_files.items():
        if 'binary_path' not in file_data:
            print(f"Warning: No binary found for {base_name}, skipping")
            continue
        
        binary_path = file_data['binary_path']
        binary_dir = binary_path.parent
        
        file_info = {
            "path": binary_path.name
        }
        
        if binary_dir != folder_path:
            relative_dir = binary_dir.relative_to(folder_path)
            file_info["path"] = str(relative_dir / binary_path.name).replace('\\', '/')
        
        if 'crc32_file' in file_data:
            crc32_value = load_checksum_file(file_data['crc32_file'])
            if crc32_value:
                file_info['crc32'] = crc32_value
        
        if 'sha256_file' in file_data:
            sha256_value = load_checksum_file(file_data['sha256_file'])
            if sha256_value:
                file_info['sha256'] = sha256_value
        
        if 'sha512_file' in file_data:
            sha512_value = load_checksum_file(file_data['sha512_file'])
            if sha512_value:
                file_info['sha512'] = sha512_value
        
        if 'sig_file' in file_data:
            file_info['has_signature'] = True
        
        manifest_files.append(file_info)
    
    return manifest_files


def generate_manifest(folder, output, platform_override, version, arch_override=None):
    script_dir = Path(__file__).parent
    
    if folder is None:
        release_dir = script_dir.parent / 'release'
        folder = release_dir
    else:
        folder = Path(folder)
    
    if not folder.exists():
        print(f"Error: Folder not found: {folder}")
        return
    
    detected_platform = detect_platform()
    target_platform = platform_override if platform_override else detected_platform
    detected_arch = detect_arch()
    target_arch = arch_override if arch_override else detected_arch

    if output is None:
        output = folder / f'{target_platform}-{target_arch}-manifest.json'
    else:
        output = Path(output)
    
    files = scan_folder(folder)
    
    manifest = {
        "version": version,
        "files": files
    }
    
    with open(output, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Manifest generated: {output}")
    print(f"Target platform: {target_platform}")
    print(f"Target arch: {target_arch}")
    print(f"Version: {version}")
    print(f"Files tracked: {len(files)}")


def main():
    parser = argparse.ArgumentParser(description='Generate platform-specific manifest from folder')
    parser.add_argument('--folder', '-f', help='Folder to scan (default: ../release/ from script location)')
    parser.add_argument('--output', '-o', help='Output manifest path (default: <folder>/<platform>-manifest.json)')
    parser.add_argument('--platform', '-p', choices=['windows', 'macos', 'linux'], help='Target platform (default: auto-detect)')
    parser.add_argument('--arch', '-a', choices=['x64', 'arm64', 'x86'], help='Target architecture (default: auto-detect)')
    parser.add_argument('--version', '-v', required=True, help='Version string (e.g., 1.2.3)')

    args = parser.parse_args()
    generate_manifest(args.folder, args.output, args.platform, args.version, args.arch)


if __name__ == "__main__":
    main()
