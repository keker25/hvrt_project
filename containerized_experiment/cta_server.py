#!/usr/bin/env python3
"""
CTA (Core Trust Authority) Server - FastAPI 容器化版本 (增强版)
- 添加调试接口
- 完善设备状态管理
"""
import os
import sys
import json
import time
import base64
import hashlib
import hmac
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network_simulator import default_network

app = FastAPI(title="HVRT CTA Server")

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

class CTA:
    def __init__(self):
        self.privkey, self.pubkey = CryptoUtils.generate_keypair()
        self.devices: Dict[str, Dict] = {}
        self.revoked_devices = set()
        self.revocation_version = 1
        self.gtt = self._issue_gtt()
    
    def _issue_gtt(self):
        t0 = time.time()
        gtt_id = CryptoUtils.generate_id("gtt")
        gtt_data = {
            "gtt_id": gtt_id,
            "root_pubkey": self.pubkey,
            "revocation_version": self.revocation_version,
            "valid_from": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "valid_to": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
        }
        gtt_data["signature"] = CryptoUtils.sign(self.privkey, gtt_data)
        self.gtt = gtt_data
        return gtt_data
    
    def register_device(self, device_id: str, region: str):
        t0 = time.time()
        if device_id in self.devices:
            raise HTTPException(status_code=409, detail=f"Device {device_id} already registered")
        
        device_secret = CryptoUtils.generate_secret()
        self.devices[device_id] = {
            "secret": device_secret,
            "region": region,
            "status": "active",
            "registered_at": time.time()
        }
        
        delay_ms = default_network.simulate_delay_only()
        t_total = (time.time() - t0) * 1000
        
        return {
            "gtt": self.gtt,
            "device_secret": device_secret,
            "timings": {
                "register_ms": t_total,
                "network_delay_ms": delay_ms
            }
        }
    
    def revoke_device(self, device_id: str):
        t0 = time.time()
        if device_id not in self.devices:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        if device_id not in self.revoked_devices:
            self.revoked_devices.add(device_id)
            self.revocation_version += 1
            self._issue_gtt()
            print(f"[CTA] Device {device_id} revoked! New version: {self.revocation_version}")
        
        delay_ms = default_network.simulate_delay_only()
        t_total = (time.time() - t0) * 1000
        
        return {
            "status": "revoked",
            "revocation_version": self.revocation_version,
            "timings": {
                "revoke_ms": t_total,
                "network_delay_ms": delay_ms
            }
        }
    
    def get_sync_data(self):
        t0 = time.time()
        delay_ms = default_network.simulate_delay_only()
        t_total = (time.time() - t0) * 1000
        
        # 构建完整的设备状态字典
        device_states = {}
        for device_id in self.devices:
            device_states[device_id] = "revoked" if device_id in self.revoked_devices else "active"
        
        print(f"[CTA] Sync: version={self.revocation_version}, devices={len(device_states)}, revoked={len(self.revoked_devices)}")
        
        return {
            "gtt": self.gtt,
            "revocation_version": self.revocation_version,
            "revoked_devices": list(self.revoked_devices),
            "device_states": device_states,
            "timings": {
                "sync_ms": t_total,
                "network_delay_ms": delay_ms
            }
        }
    
    def get_device_status(self, device_id: str):
        """调试接口：获取设备状态"""
        if device_id not in self.devices:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        revoked = device_id in self.revoked_devices
        return {
            "device_id": device_id,
            "status": "revoked" if revoked else "active",
            "revoked": revoked,
            "cta_revocation_version": self.revocation_version
        }

cta = CTA()

class RegisterRequest(BaseModel):
    device_id: str
    region: str

class RevokeRequest(BaseModel):
    device_id: str

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "cta"}

@app.get("/pubkey")
async def get_pubkey():
    return {"pubkey": cta.pubkey}

@app.get("/gtt")
async def get_gtt():
    return {"gtt": cta.gtt}

@app.get("/sync")
async def sync():
    return cta.get_sync_data()

@app.post("/register")
async def register(request: RegisterRequest):
    return cta.register_device(request.device_id, request.region)

@app.post("/revoke")
async def revoke(request: RevokeRequest):
    return cta.revoke_device(request.device_id)

@app.get("/version")
async def get_version():
    return {"revocation_version": cta.revocation_version}

@app.get("/debug/device_status/{device_id}")
async def debug_device_status(device_id: str):
    """调试接口：检查设备在 CTA 的状态"""
    return cta.get_device_status(device_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("CTA_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
