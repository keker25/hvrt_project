#!/usr/bin/env python3
"""
AG (Access Gateway) Server - FastAPI 容器化版本 (增强版)
- 添加调试接口
- 完善撤销状态检查（签发和认证阶段）
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

app = FastAPI(title="HVRT AG Server")

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

class AG:
    def __init__(self, ec_url: str, ag_id: str):
        self.ec_url = ec_url
        self.ag_id = ag_id
        self.privkey, self.pubkey = CryptoUtils.generate_keypair()
        self.gtt = None
        self.revocation_version = 1
        self.revoked_devices = set()
        self.device_states = {}  # 存储完整的设备状态
        self.challenges = {}
        self._sync_with_ec()
    
    def _sync_with_ec(self):
        try:
            response = httpx.get(f"{self.ec_url}/sync_data", timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.gtt = data["gtt"]
                self.revocation_version = data["revocation_version"]
                self.revoked_devices = set(data["revoked_devices"])
                self.device_states = data.get("device_states", {})
                print(f"[AG {self.ag_id}] Synced with EC: version={self.revocation_version}, devices={len(self.device_states)}, revoked={len(self.revoked_devices)}")
                print(f"[AG {self.ag_id}] device_states: {self.device_states}")
        except Exception as e:
            print(f"AG sync error: {e}")
    
    def sync_with_ec(self):
        t0 = time.time()
        self._sync_with_ec()
        t_total = (time.time() - t0) * 1000
        return {
            "revocation_version": self.revocation_version,
            "timings": {"sync_ms": t_total}
        }
    
    def get_device_status(self, device_id: str):
        """调试接口：获取设备状态"""
        revoked = device_id in self.revoked_devices
        return {
            "device_id": device_id,
            "revoked": revoked,
            "ag_id": self.ag_id,
            "ag_revocation_version": self.revocation_version
        }
    
    def issue_rrt(self, device_id: str, region: str):
        """签发 RRT - 检查撤销状态"""
        t0 = time.time()
        
        if device_id in self.revoked_devices:
            raise HTTPException(status_code=403, detail=f"Device {device_id} is revoked")
        
        delay_ms = default_network.simulate_delay_only()
        
        rrt_id = CryptoUtils.generate_id("rrt")
        rrt_data = {
            "rrt_id": rrt_id,
            "device_id": device_id,
            "region": region,
            "gtt_id": self.gtt["gtt_id"],
            "ag_pubkey": self.pubkey,
            "issue_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "expire_time": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat().replace("+00:00", "Z")
        }
        rrt_data["signature"] = CryptoUtils.sign(self.privkey, rrt_data)
        
        t_total = (time.time() - t0) * 1000
        return {
            "rrt": rrt_data,
            "latency_ms": t_total,
            "timings": {
                "rrt_issue_ms": t_total,
                "network_delay_ms": delay_ms
            }
        }
    
    def issue_sat(self, device_id: str, rrt_id: str):
        """签发 SAT - 检查撤销状态"""
        t0 = time.time()
        
        if device_id in self.revoked_devices:
            raise HTTPException(status_code=403, detail=f"Device {device_id} is revoked")
        
        delay_ms = default_network.simulate_delay_only()
        
        sat_id = CryptoUtils.generate_id("sat")
        sat_data = {
            "sat_id": sat_id,
            "device_id": device_id,
            "rrt_id": rrt_id,
            "issue_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "expire_time": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
        }
        sat_data["signature"] = CryptoUtils.sign(self.privkey, sat_data)
        
        t_total = (time.time() - t0) * 1000
        return {
            "sat": sat_data,
            "latency_ms": t_total,
            "timings": {
                "sat_issue_ms": t_total,
                "network_delay_ms": delay_ms
            }
        }
    
    def generate_challenge(self, device_id: str):
        t0 = time.time()
        challenge_id = CryptoUtils.generate_id("chal")
        nonce = CryptoUtils.generate_nonce()
        self.challenges[challenge_id] = {
            "device_id": device_id,
            "nonce": nonce,
            "created_at": time.time()
        }
        t_total = (time.time() - t0) * 1000
        return {
            "challenge_id": challenge_id,
            "nonce": nonce,
            "latency_ms": t_total,
            "timings": {"challenge_ms": t_total}
        }
    
    def verify_response_hvrt(self, challenge_id: str, device_id: str, response_hmac: str, device_secret: str, sat: Dict, rrt: Dict):
        start_total = time.time()
        
        print(f"[AG {self.ag_id}] Verifying device: {device_id}")
        print(f"[AG {self.ag_id}] Current device_states: {self.device_states}")
        print(f"[AG {self.ag_id}] Current revoked_devices: {self.revoked_devices}")
        
        if challenge_id not in self.challenges:
            return {"result": "deny", "reason": "invalid_challenge_id", "timings": {"total_ms": 0, "ticket_verify_ms": 0, "state_check_ms": 0}}
        
        challenge = self.challenges[challenge_id]
        if challenge["device_id"] != device_id:
            return {"result": "deny", "reason": "device_mismatch", "timings": {"total_ms": 0, "ticket_verify_ms": 0, "state_check_ms": 0}}
        
        del self.challenges[challenge_id]
        
        expected_hmac = CryptoUtils.compute_hmac(device_secret, f"{challenge_id}:{challenge['nonce']}")
        if expected_hmac != response_hmac:
            return {"result": "deny", "reason": "invalid_response_hmac", "timings": {"total_ms": 0, "ticket_verify_ms": 0, "state_check_ms": 0}}
        
        start_ticket_verify = time.time()
        
        sat_data = {k: sat[k] for k in sat if k != "signature"}
        if not CryptoUtils.verify(self.pubkey, sat_data, sat["signature"]):
            return {"result": "deny", "reason": "invalid_sat_signature", "timings": {"total_ms": 0, "ticket_verify_ms": 0, "state_check_ms": 0}}
        
        rrt_data = {k: rrt[k] for k in rrt if k != "signature"}
        if not CryptoUtils.verify(self.pubkey, rrt_data, rrt["signature"]):
            return {"result": "deny", "reason": "invalid_rrt_signature", "timings": {"total_ms": 0, "ticket_verify_ms": 0, "state_check_ms": 0}}
        
        gtt_data = {k: self.gtt[k] for k in self.gtt if k != "signature"}
        if not CryptoUtils.verify(self.gtt["root_pubkey"], gtt_data, self.gtt["signature"]):
            return {"result": "deny", "reason": "invalid_gtt_signature", "timings": {"total_ms": 0, "ticket_verify_ms": 0, "state_check_ms": 0}}
        
        ticket_verify_ms = (time.time() - start_ticket_verify) * 1000
        
        start_state_check = time.time()
        is_revoked = device_id in self.revoked_devices or self.device_states.get(device_id) == "revoked"
        print(f"[AG {self.ag_id}] Device {device_id} check: is_revoked={is_revoked}")
        
        if is_revoked:
            state_check_ms = (time.time() - start_state_check) * 1000
            total_ms = (time.time() - start_total) * 1000
            print(f"[AG {self.ag_id}] DENYING device {device_id} (revoked)")
            return {
                "result": "deny", 
                "reason": "device_revoked", 
                "timings": {
                    "total_ms": total_ms,
                    "ticket_verify_ms": ticket_verify_ms, 
                    "state_check_ms": state_check_ms
                }
            }
        
        state_check_ms = (time.time() - start_state_check) * 1000
        total_ms = (time.time() - start_total) * 1000
        
        print(f"[AG {self.ag_id}] ALLOWING device {device_id}")
        return {
            "result": "allow",
            "reason": "hvrt_verified",
            "timings": {
                "total_ms": total_ms,
                "ticket_verify_ms": ticket_verify_ms,
                "state_check_ms": state_check_ms
            }
        }

ec_url = os.getenv("EC_URL", "http://ec:8050")
ag_id = os.getenv("AG_ID", "ag1")
ag = AG(ec_url, ag_id)

class IssueRRTRequest(BaseModel):
    device_id: str
    region: str

class IssueSATRequest(BaseModel):
    device_id: str
    rrt_id: str

class GenerateChallengeRequest(BaseModel):
    device_id: str

class VerifyResponseRequest(BaseModel):
    challenge_id: str
    device_id: str
    response_hmac: str
    device_secret: str
    sat: Dict[str, Any]
    rrt: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ag", "ag_id": ag_id}

@app.get("/pubkey")
async def get_pubkey():
    return {"pubkey": ag.pubkey}

@app.post("/issue_rrt")
async def issue_rrt(request: IssueRRTRequest):
    return ag.issue_rrt(request.device_id, request.region)

@app.post("/issue_sat")
async def issue_sat(request: IssueSATRequest):
    return ag.issue_sat(request.device_id, request.rrt_id)

@app.post("/generate_challenge")
async def generate_challenge(request: GenerateChallengeRequest):
    return ag.generate_challenge(request.device_id)

@app.post("/verify_response")
async def verify_response(request: VerifyResponseRequest):
    return ag.verify_response_hvrt(
        request.challenge_id,
        request.device_id,
        request.response_hmac,
        request.device_secret,
        request.sat,
        request.rrt
    )

@app.post("/sync")
async def sync():
    return ag.sync_with_ec()

@app.get("/version")
async def get_version():
    return {"revocation_version": ag.revocation_version, "ag_id": ag_id}

@app.get("/debug/device_status/{device_id}")
async def debug_device_status(device_id: str):
    """调试接口：检查设备在 AG 的状态"""
    return ag.get_device_status(device_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AG_PORT", 8100))
    uvicorn.run(app, host="0.0.0.0", port=port)
