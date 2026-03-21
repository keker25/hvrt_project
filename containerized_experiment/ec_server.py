#!/usr/bin/env python3
"""
EC (Edge Coordinator) Server - FastAPI 容器化版本 (增强版)
- 添加调试接口
- 完善撤销同步
"""
import os
import sys
import json
import time
import base64
import hashlib
import hmac
import random
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network_simulator import default_network

app = FastAPI(title="HVRT EC Server")

class CryptoUtils:
    @staticmethod
    def generate_keypair():
        privkey = ed25519.Ed25519PrivateKey.generate()
        pubkey = privkey.public_key()
        priv_bytes = privkey.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_bytes = pubkey.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(priv_bytes).decode(), base64.b64encode(pub_bytes).decode()
    
    @staticmethod
    def generate_ed25519_keypair():
        return CryptoUtils.generate_keypair()
    
    @staticmethod
    def sign(privkey_b64: str, data: Dict) -> str:
        priv_bytes = base64.b64decode(privkey_b64)
        privkey = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
        sorted_items = sorted((str(k), str(v)) for k, v in data.items() if k != "signature")
        msg = "|".join(f"{k}={v}" for k, v in sorted_items).encode()
        signature = privkey.sign(msg)
        return base64.b64encode(signature).decode()
    
    @staticmethod
    def verify(pubkey_b64: str, data: Dict, signature_b64: str) -> bool:
        try:
            pub_bytes = base64.b64decode(pubkey_b64)
            pubkey = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            signature = base64.b64decode(signature_b64)
            sorted_items = sorted((str(k), str(v)) for k, v in data.items() if k != "signature")
            msg = "|".join(f"{k}={v}" for k, v in sorted_items).encode()
            pubkey.verify(signature, msg)
            return True
        except Exception:
            return False
    
    @staticmethod
    def generate_id(prefix: str) -> str:
        return f"{prefix}_{base64.b16encode(os.urandom(8)).decode().lower()}"
    
    @staticmethod
    def generate_nonce() -> str:
        return base64.b64encode(os.urandom(16)).decode()
    
    @staticmethod
    def compute_hmac(secret: str, message: str) -> str:
        hmac_obj = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(hmac_obj.digest()).decode()
    
    @staticmethod
    def generate_secret() -> str:
        return base64.b64encode(os.urandom(32)).decode()

class EC:
    def __init__(self, cta_url: str):
        self.cta_url = cta_url
        self.gtt = None
        self.revocation_version = 1
        self.revoked_devices = set()
        self.device_states = {}  # 存储完整的设备状态
        self._sync_with_cta()
    
    def _sync_with_cta(self):
        try:
            response = httpx.get(f"{self.cta_url}/sync", timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.gtt = data["gtt"]
                self.revocation_version = data["revocation_version"]
                self.revoked_devices = set(data["revoked_devices"])
                self.device_states = data.get("device_states", {})
                print(f"[EC] Synced with CTA: version={self.revocation_version}, devices={len(self.device_states)}, revoked={len(self.revoked_devices)}")
                print(f"[EC] device_states: {self.device_states}")
        except Exception as e:
            print(f"EC sync error: {e}")
    
    def sync_with_cta(self):
        t0 = time.time()
        self._sync_with_cta()
        t_total = (time.time() - t0) * 1000
        return {
            "revocation_version": self.revocation_version,
            "timings": {"sync_ms": t_total}
        }
    
    def get_sync_data(self):
        return {
            "gtt": self.gtt,
            "revocation_version": self.revocation_version,
            "revoked_devices": list(self.revoked_devices),
            "device_states": self.device_states
        }
    
    def get_device_status(self, device_id: str):
        """调试接口：获取设备状态"""
        revoked = device_id in self.revoked_devices
        status = self.device_states.get(device_id, "unknown")
        return {
            "device_id": device_id,
            "revoked": revoked,
            "status": status,
            "ec_revocation_version": self.revocation_version
        }

cta_url = os.getenv("CTA_URL", "http://cta:8000")
ec = EC(cta_url)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ec"}

@app.post("/sync")
async def sync():
    return ec.sync_with_cta()

@app.get("/sync_data")
async def get_sync_data():
    return ec.get_sync_data()

@app.get("/version")
async def get_version():
    return {"revocation_version": ec.revocation_version}

@app.get("/debug/device_status/{device_id}")
async def debug_device_status(device_id: str):
    """调试接口：检查设备在 EC 的状态"""
    return ec.get_device_status(device_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("EC_PORT", 8050))
    uvicorn.run(app, host="0.0.0.0", port=port)
