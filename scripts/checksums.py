#!/usr/bin/env python3

import argparse
import hashlib
import zlib
import os
from pathlib import Path


def calculate_checksums(filepath):
    crc32_value = 0
    sha256_hash = hashlib.sha256()
    sha512_hash = hashlib.sha512()
    
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            crc32_value = zlib.crc32(chunk, crc32_value)
            sha256_hash.update(chunk)
            sha512_hash.update(chunk)
    
    crc32_value = crc32_value & 0xFFFFFFFF
    
    return {
        'crc32': f"{crc32_value:08x}",
        'sha256': sha256_hash.hexdigest(),
        'sha512': sha512_hash.hexdigest()
    }


def main():
    parser = argparse.ArgumentParser(description='Generate CRC32, SHA256, and SHA512 checksums')
    parser.add_argument('--file', '-f', required=True, help='File to generate checksums for')
    parser.add_argument('--output-dir', '-o', help='Output directory for checksum files (optional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        return
    
    checksums = calculate_checksums(args.file)
    
    filename = Path(args.file).name
    
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        
        crc32_path = Path(args.output_dir) / f"{filename}.crc32"
        sha256_path = Path(args.output_dir) / f"{filename}.sha256"
        sha512_path = Path(args.output_dir) / f"{filename}.sha512"
        
        with open(crc32_path, 'w') as f:
            f.write(checksums['crc32'])
        
        with open(sha256_path, 'w') as f:
            f.write(checksums['sha256'])
        
        with open(sha512_path, 'w') as f:
            f.write(checksums['sha512'])
        
        print(f"CRC32:  {checksums['crc32']} -> {crc32_path}")
        print(f"SHA256: {checksums['sha256']} -> {sha256_path}")
        print(f"SHA512: {checksums['sha512']} -> {sha512_path}")
    else:
        print(f"File: {filename}")
        print(f"CRC32:  {checksums['crc32']}")
        print(f"SHA256: {checksums['sha256']}")
        print(f"SHA512: {checksums['sha512']}")


if __name__ == "__main__":
    main()
