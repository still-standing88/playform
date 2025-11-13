import hmac
import hashlib
import os
import pickle

from pathlib import Path
from typing import Any, Union

try:
    import keyring
except ImportError:
    keyring = None


class SignatureError(Exception):
    pass

class TamperingError(SignatureError):


    def __init__(self, message, quarantined_path=None):
        super().__init__(message)
        self.quarantined_path = quarantined_path

class SignatureMissingError(SignatureError):
    pass



class SecurePickle:


    def __init__(self, service_name: str, key_name: str):
        if not isinstance(service_name, str) or not service_name:
            raise ValueError("service_name must be a non-empty string.")

        if not isinstance(key_name, str) or not key_name:
            raise ValueError("key_name must be a non-empty string.")
            
        self.service_name = service_name
        self.key_name = key_name
        self._key: Union[bytes, None] = None

    def _get_key(self) -> bytes:
        if self._key:
            return self._key

        if keyring:
            key_hex = keyring.get_password(self.service_name, self.key_name)
            if key_hex:
                self._key = bytes.fromhex(key_hex)
                return self._key
            
            new_key_bytes = os.urandom(32)
            keyring.set_password(self.service_name, self.key_name, new_key_bytes.hex())
            self._key = new_key_bytes
            return self._key

        key_file = Path.home() / f".{self.service_name}_{self.key_name}.key"
        if key_file.exists():
            self._key = key_file.read_bytes()
            return self._key

        new_key_bytes = os.urandom(32)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(new_key_bytes)
        try:
            os.chmod(key_file, 0o600)
        except OSError:
            pass
            
        self._key = new_key_bytes
        return self._key

    def _sign_bytes(self, data: bytes) -> str:
        key = self._get_key()
        return hmac.new(key, data, hashlib.sha256).hexdigest()

    def _atomic_write(self, path: Path, data: bytes):
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp_path.write_bytes(data)
            tmp_path.replace(path)
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise e

    def save(self, obj: Any, file_path: Union[str, Path]):
        pkl_path = Path(file_path)
        pkl_path.parent.mkdir(parents=True, exist_ok=True)

        pickled_data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        self._atomic_write(pkl_path, pickled_data)

        signature = self._sign_bytes(pickled_data)
        sig_path = pkl_path.with_suffix(pkl_path.suffix + ".sig")
        self._atomic_write(sig_path, signature.encode('utf-8'))

    def load(self, file_path: Union[str, Path]) -> Any:
        pkl_path = Path(file_path)
        sig_path = pkl_path.with_suffix(pkl_path.suffix + ".sig")

        if not pkl_path.exists():
            raise FileNotFoundError(f"Pickle file not found: {pkl_path}")
        if not sig_path.exists():
            raise SignatureMissingError(f"Signature file missing for '{pkl_path}'.")

        pickled_data = pkl_path.read_bytes()
        stored_signature = sig_path.read_text('utf-8').strip()
        expected_signature = self._sign_bytes(pickled_data)

        if not hmac.compare_digest(expected_signature, stored_signature):
            quarantine_path = pkl_path.with_suffix(pkl_path.suffix + ".quarantined")
            pkl_path.replace(quarantine_path)
            sig_path.unlink(missing_ok=True)
            raise TamperingError(
                f"SIGNATURE MISMATCH! File has been quarantined to '{quarantine_path}'.",
                quarantined_path=quarantine_path
            )
            
        return pickle.loads(pickled_data)

