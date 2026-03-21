import os
import hashlib
import hmac
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64
import json


def generate_ed25519_keypair():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    return base64.b64encode(private_bytes).decode(), base64.b64encode(public_bytes).decode()


def sign_with_ed25519(private_key_b64: str, data: dict) -> str:
    private_bytes = base64.b64decode(private_key_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
    
    data_json = json.dumps(data, sort_keys=True).encode('utf-8')
    signature = private_key.sign(data_json)
    
    return base64.b64encode(signature).decode()


def verify_with_ed25519(public_key_b64: str, data: dict, signature_b64: str) -> bool:
    try:
        public_bytes = base64.b64decode(public_key_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        
        data_json = json.dumps(data, sort_keys=True).encode('utf-8')
        signature = base64.b64decode(signature_b64)
        
        public_key.verify(signature, data_json)
        return True
    except Exception:
        return False


def generate_hmac_sha256(key: str, message: str) -> str:
    key_bytes = key.encode('utf-8')
    message_bytes = message.encode('utf-8')
    hmac_obj = hmac.new(key_bytes, message_bytes, hashlib.sha256)
    return base64.b64encode(hmac_obj.digest()).decode()


def verify_hmac_sha256(key: str, message: str, signature_b64: str) -> bool:
    expected = generate_hmac_sha256(key, message)
    return hmac.compare_digest(expected, signature_b64)


def generate_nonce() -> str:
    return base64.b64encode(os.urandom(32)).decode()


def generate_id(prefix: str) -> str:
    random_bytes = os.urandom(16)
    return f"{prefix}_{base64.b16encode(random_bytes).decode().lower()[:16]}"
