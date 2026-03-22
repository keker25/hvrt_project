import os
import hashlib
import hmac
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64
import json
import time
from datetime import datetime
from .io_utils import atomic_write_json, read_json


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


def ensure_keypair(dir_path: str, name_prefix: str = 'key') -> tuple:
    """Ensure an ed25519 keypair exists in dir_path.

    Returns (private_b64, public_b64). Files written: {name_prefix}_priv.b64, {name_prefix}_pub.b64
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    priv_path = os.path.join(dir_path, f"{name_prefix}_priv.b64")
    pub_path = os.path.join(dir_path, f"{name_prefix}_pub.b64")

    if os.path.exists(priv_path) and os.path.exists(pub_path):
        with open(priv_path, 'r', encoding='utf-8') as f:
            priv = f.read().strip()
        with open(pub_path, 'r', encoding='utf-8') as f:
            pub = f.read().strip()
        return priv, pub

    priv, pub = generate_ed25519_keypair()
    # write atomically
    atomic_write_json(priv_path, priv)
    atomic_write_json(pub_path, pub)
    return priv, pub


def create_gtt(root_pubkey_b64: str, version: str = None) -> dict:
    """Create a simple GTT structure (unsigned)."""
    if version is None:
        version = datetime.utcnow().isoformat() + 'Z'
    gtt = {
        'version': version,
        'root_pubkey': root_pubkey_b64,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }
    return gtt


def sign_gtt(root_priv_b64: str, gtt: dict) -> str:
    """Return base64 signature of the GTT dict using ed25519."""
    return sign_with_ed25519(root_priv_b64, gtt)
