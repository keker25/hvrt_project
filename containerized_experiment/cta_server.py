#!/usr/bin/env python3
"""
CTA (Core Trust Authority) Server - FastAPI 容器化版本 (数据库版)
- 使用 SQLite 数据库存储
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
from database import Database

app = FastAPI(title="HVRT CTA Server")

# 初始化数据库
db = Database("/app/data/cta.db")


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
        # 检查是否已有密钥
        self.privkey = db.cta_get_metadata("root_privkey")
        self.pubkey = db.cta_get_metadata("root_pubkey")
        
        if not self.privkey or not self.pubkey:
            self.privkey, self.pubkey = CryptoUtils.generate_keypair()
            db.cta_set_metadata("root_privkey", self.privkey)
            db.cta_set_metadata("root_pubkey", self.pubkey)
        
        # 检查是否已有 revocation_version
        self.revocation_version = db.cta_get_metadata("revocation_version") or 1
        
        # 检查是否已有 GTT
        self.gtt = db.cta_get_metadata("current_gtt")
        if not self.gtt:
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
        db.cta_set_metadata("current_gtt", gtt_data)
        return gtt_data
    
    def register_device(self, device_id: str, region: str):
        t0 = time.time()
        
        # 检查设备是否已存在
        existing_device = db.cta_get_device(device_id)
        if existing_device:
            raise HTTPException(status_code=409, detail=f"Device {device_id} already registered")
        
        device_secret = CryptoUtils.generate_secret()
        db.cta_save_device(device_id, device_secret, region, "active")
        
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
        
        # 检查设备是否存在
        existing_device = db.cta_get_device(device_id)
        if not existing_device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # 检查是否已撤销
        if not db.cta_is_revoked(device_id):
            db.cta_revoke_device(device_id)
            self.revocation_version += 1
            db.cta_set_metadata("revocation_version", self.revocation_version)
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
        all_devices = db.cta_get_all_devices()
        revoked_devices = db.cta_get_revoked_devices()
        
        device_states = {}
        for device_id in all_devices:
            device_states[device_id] = "revoked" if device_id in revoked_devices else "active"
        
        print(f"[CTA] Sync: version={self.revocation_version}, devices={len(device_states)}, revoked={len(revoked_devices)}")
        
        # also include device secrets for EC consumption
        device_secrets = {}
        all_devices = db.cta_get_all_devices()
        for did, info in all_devices.items():
            device_secrets[did] = info.get("secret")

        return {
            "gtt": self.gtt,
            "revocation_version": self.revocation_version,
            "revoked_devices": list(revoked_devices),
            "device_states": device_states,
            "device_secrets": device_secrets,
            "timings": {
                "sync_ms": t_total,
                "network_delay_ms": delay_ms
            }
        }
    
    def get_device_status(self, device_id: str):
        """调试接口：获取设备状态"""
        existing_device = db.cta_get_device(device_id)
        if not existing_device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        revoked = db.cta_is_revoked(device_id)
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


@app.get("/")
async def root():
    return {"service": "cta", "status": "running"}


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


class OnlineVerifyRequest(BaseModel):
    device_id: str
    sat: Dict[str, Any]
    rrt: Dict[str, Any]
    ag_pubkey: str
    ec_pubkey: str | None = None


@app.post("/auth/online_verify")
async def online_verify(request: OnlineVerifyRequest):
    # 验证 SAT 与 RRT 的签名（使用 AG pubkey for SAT, EC/AG pubkey for RRT depending on deployment)
    sat = request.sat
    rrt = request.rrt
    ag_pubkey = request.ag_pubkey

    # verify SAT signature with AG pubkey
    sat_data = {k: v for k, v in sat.items() if k != "signature"}
    if not CryptoUtils.verify(ag_pubkey, sat_data, sat["signature"]):
        return {"result": "deny", "reason": "invalid SAT signature"}

    # verify RRT signature; try EC pubkey if provided, otherwise try AG pubkey
    rrt_data = {k: v for k, v in rrt.items() if k != "signature"}
    verified_rrt = False
    if request.ec_pubkey:
        try:
            if CryptoUtils.verify(request.ec_pubkey, rrt_data, rrt["signature"]):
                verified_rrt = True
        except Exception:
            verified_rrt = False
    if not verified_rrt:
        if not CryptoUtils.verify(ag_pubkey, rrt_data, rrt["signature"]):
            return {"result": "deny", "reason": "invalid RRT signature"}

    # check matching ids
    if sat.get("rrt_id") != rrt.get("rrt_id"):
        return {"result": "deny", "reason": "SAT-RRT mismatch"}

    if rrt.get("gtt_id") != cta.gtt.get("gtt_id"):
        return {"result": "deny", "reason": "RRT-GTT mismatch"}

    # verify gtt signature
    gtt_data = {k: v for k, v in cta.gtt.items() if k != "signature"}
    if not CryptoUtils.verify(cta.gtt["root_pubkey"], gtt_data, cta.gtt["signature"]):
        return {"result": "deny", "reason": "invalid GTT signature"}

    # check device revocation
    device = db.cta_get_device(request.device_id)
    if device and device.get("status") == "revoked":
        return {"result": "deny", "reason": "device_revoked"}

    return {"result": "allow", "reason": "CTA online verify success"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("CTA_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
