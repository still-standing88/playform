#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def sign_file(binary_path, key_path, output_path):
    if not os.path.exists(binary_path):
        print(f"Error: Binary not found: {binary_path}")
        return
    
    if not os.path.exists(key_path):
        print(f"Error: Private key not found: {key_path}")
        return
    
    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None
        )
    
    with open(binary_path, 'rb') as f:
        binary_data = f.read()
    
    signature = private_key.sign(
        binary_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    with open(output_path, 'wb') as f:
        f.write(signature)
    
    print(f"Signed: {binary_path}")
    print(f"Signature saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Sign a binary file with RSA-4096 private key')
    parser.add_argument('--binary', '-b', required=True, help='Binary file to sign')
    parser.add_argument('--key', '-k', required=True, help='Private key file (PEM)')
    parser.add_argument('--output', '-o', required=True, help='Output signature file')
    
    args = parser.parse_args()
    sign_file(args.binary, args.key, args.output)


if __name__ == "__main__":
    main()
