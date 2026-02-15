#!/usr/bin/env python3

import argparse
import os
from pathlib import Path


def generate_public_key_module(key_path, output_path):
    if not os.path.exists(key_path):
        print(f"Error: Public key not found: {key_path}")
        return
    
    with open(key_path, 'r') as f:
        public_key_pem = f.read()
    
    module_content = f'''PUBLIC_KEY_PEM = """{public_key_pem}"""
'''
    
    output_file = Path(output_path) / 'public_key.py'
    os.makedirs(output_path, exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(module_content)
    
    print(f"Public key module generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate importable public key Python module')
    parser.add_argument('--key', '-k', required=True, help='Public key PEM file')
    parser.add_argument('--destination', '-d', required=True, help='Destination folder for public_key.py')
    
    args = parser.parse_args()
    generate_public_key_module(args.key, args.destination)


if __name__ == "__main__":
    main()
