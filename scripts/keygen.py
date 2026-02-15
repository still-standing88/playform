#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def generate_keypair(destination):
    os.makedirs(destination, exist_ok=True)
    
    print("Generating RSA-4096 keypair...")
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )
    
    public_key = private_key.public_key()
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    private_path = Path(destination) / "private_key.pem"
    public_path = Path(destination) / "public_key.pem"
    
    with open(private_path, 'wb') as f:
        f.write(private_pem)
    
    with open(public_path, 'wb') as f:
        f.write(public_pem)
    
    print(f"Private key saved to: {private_path}")
    print(f"Public key saved to: {public_path}")
    print("\nWARNING: Keep private_key.pem secure and never share it!")


def main():
    parser = argparse.ArgumentParser(description='Generate RSA-4096 keypair')
    parser.add_argument('--destination', '-d', required=True, help='Destination folder for keys')
    
    args = parser.parse_args()
    generate_keypair(args.destination)


if __name__ == "__main__":
    main()
