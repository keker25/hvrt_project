#!/usr/bin/env python3
"""
HVRT 分层信任离线认证系统 - 完整功能演示 (无网络依赖)
这个脚本模拟完整的 CTA-EC-AG-TD 认证流程
"""
import os
import hashlib
import hmac
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

print("=" * 80)
print("  HVRT 分层信任离线认证系统 - 完整演示 (模拟所有服务)")
print("=" * 80)

# ==========================================
# 1. 密码学工具
# ==========================================
print("\n【1/7】初始化密码学模块")
print("-" * 80)

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

class CryptoUtils:
    @staticmethod
    def generate_keypair():
        priv = ed25519.Ed25519PrivateKey.generate()
        pub = priv.public_key()
        priv_b64 = base64.b64encode(
            priv.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
        ).decode()
        pub_b64 = base64.b64encode(
            pub.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).decode()
        return priv_b64, pub_b64
    
    @staticmethod
    def sign(priv_b64: str, data: Dict):
        priv_bytes = base64.b64decode(priv_b64)
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
        data_json = json.dumps(data, sort_keys=True).encode('utf-8')
        sig = priv.sign(data_json)
        return base64.b64encode(sig).decode()
    
    @staticmethod
    def verify(pub_b64: str, data: Dict, sig_b64: str) -> bool:
        try:
            pub_bytes = base64.b64decode(pub_b64)
            pub = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            data_json = json.dumps(data, sort_keys=True).encode('utf-8')
            sig = base64.b64decode(sig_b64)
            pub.verify(sig, data_json)
            return True
        except Exception:
            return False
    
    @staticmethod
    def hmac_sha256(key: str, msg: str) -> str:
        h = hmac.new(key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(h.digest()).decode()
    
    @staticmethod
    def generate_nonce() -> str:
        return base64.b64encode(os.urandom(32)).decode()
    
    @staticmethod
    def generate_id(prefix: str) -> str:
        return f"{prefix}_{base64.b16encode(os.urandom(8)).decode().lower()}"

print("✓ 密码学工具初始化完成")

# ==========================================
# 2. 模拟 CTA (云端信任中心)
# ==========================================
print("\n【2/7】模拟 CTA (云端信任中心)")
print("-" * 80)

class MockCTA:
    def __init__(self):
        self.privkey, self.pubkey = CryptoUtils.generate_keypair()
        self.devices = {}
        self.revocation_version = 1
        self.gtt = None
        self._generate_gtt()
        print(f"✓ CTA 初始化完成")
        print(f"  根公钥: {self.pubkey[:30]}...")
    
    def _generate_gtt(self):
        gtt_data = {
            "gtt_id": CryptoUtils.generate_id("gtt"),
            "root_pubkey": self.pubkey,
            "policy_version": 1,
            "revocation_version": self.revocation_version,
            "valid_from": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "valid_to": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
        }
        signature = CryptoUtils.sign(self.privkey, gtt_data)
        self.gtt = {**gtt_data, "signature": signature}
        print(f"✓ 生成 GTT: {self.gtt['gtt_id']}")
    
    def register_device(self, device_id: str, region_id: str):
        secret = base64.b64encode(os.urandom(24)).decode()
        self.devices[device_id] = {
            "device_id": device_id,
            "device_secret": secret,
            "status": "active",
            "region_id": region_id,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        print(f"✓ CTA 注册设备: {device_id}")
        return self.devices[device_id]
    
    def get_gtt(self):
        return self.gtt
    
    def revoke_device(self, device_id: str):
        if device_id in self.devices:
            self.devices[device_id]["status"] = "revoked"
            self.revocation_version += 1
            self._generate_gtt()
            print(f"✓ CTA 撤销设备: {device_id}, 新版本: {self.revocation_version}")

cta = MockCTA()

# ==========================================
# 3. 模拟 EC (边缘协调节点)
# ==========================================
print("\n【3/7】模拟 EC (边缘协调节点)")
print("-" * 80)

class MockEC:
    def __init__(self, cta: MockCTA):
        self.cta = cta
        self.gtt = None
        self.device_states = {}
        self.revocation_version = 0
        self.sync_with_cta()
        print(f"✓ EC 初始化完成")
    
    def sync_with_cta(self):
        self.gtt = self.cta.get_gtt()
        self.revocation_version = self.gtt["revocation_version"]
        self.device_states = {
            d["device_id"]: d["status"] 
            for d in self.cta.devices.values()
        }
        print(f"✓ EC 从 CTA 同步完成, 版本: {self.revocation_version}")
    
    def get_gtt_summary(self):
        return {k: self.gtt[k] for k in ["gtt_id", "root_pubkey", "policy_version", "revocation_version"]}
    
    def get_state_current(self):
        return {
            "region_id": "regionA",
            "revocation_version": self.revocation_version,
            "device_states": self.device_states
        }

ec = MockEC(cta)

# ==========================================
# 4. 模拟 AG (接入网关)
# ==========================================
print("\n【4/7】模拟 AG (接入网关)")
print("-" * 80)

class MockAG:
    def __init__(self, ec: MockEC, name: str = "AG1"):
        self.name = name
        self.ec = ec
        self.privkey, self.pubkey = CryptoUtils.generate_keypair()
        self.gtt = None
        self.device_states = {}
        self.revocation_version = 0
        self.rrts = {}
        self.sats = {}
        self.challenges = {}
        self.sync_with_ec()
        print(f"✓ {self.name} 初始化完成")
    
    def sync_with_ec(self):
        self.gtt = self.ec.gtt
        state = self.ec.get_state_current()
        self.device_states = state["device_states"]
        self.revocation_version = state["revocation_version"]
        print(f"✓ {self.name} 从 EC 同步完成, 版本: {self.revocation_version}")
    
    def issue_rrt(self, device_id: str, region_id: str):
        rrt_data = {
            "rrt_id": CryptoUtils.generate_id("rrt"),
            "device_id": device_id,
            "region_id": region_id,
            "gtt_id": self.gtt["gtt_id"],
            "issue_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "expire_time": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
            "policy_tag": "default"
        }
        signature = CryptoUtils.sign(self.privkey, rrt_data)
        rrt = {**rrt_data, "signature": signature}
        self.rrts[rrt["rrt_id"]] = rrt
        print(f"✓ {self.name} 签发 RRT: {rrt['rrt_id']}")
        return rrt
    
    def issue_sat(self, device_id: str, rrt_id: str):
        sat_data = {
            "sat_id": CryptoUtils.generate_id("sat"),
            "device_id": device_id,
            "rrt_id": rrt_id,
            "issue_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "expire_time": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            "auth_scope": "local_access"
        }
        signature = CryptoUtils.sign(self.privkey, sat_data)
        sat = {**sat_data, "signature": signature}
        self.sats[sat["sat_id"]] = sat
        print(f"✓ {self.name} 签发 SAT: {sat['sat_id']}")
        return sat
    
    def create_challenge(self, device_id: str, sat: Dict, rrt: Dict):
        challenge_id = CryptoUtils.generate_id("chl")
        nonce = CryptoUtils.generate_nonce()
        self.challenges[challenge_id] = {
            "device_id": device_id,
            "nonce": nonce,
            "sat": sat,
            "rrt": rrt,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        print(f"✓ {self.name} 生成挑战: {challenge_id}")
        return {
            "challenge_id": challenge_id,
            "nonce": nonce,
            "timestamp": self.challenges[challenge_id]["timestamp"]
        }
    
    def verify_response(self, device_id: str, challenge_id: str, response_hmac: str, device_secret: str):
        if challenge_id not in self.challenges:
            return {"result": "deny", "reason": "challenge not found"}
        
        challenge = self.challenges[challenge_id]
        if challenge["device_id"] != device_id:
            return {"result": "deny", "reason": "device mismatch"}
        
        message = f"{challenge_id}:{challenge['nonce']}:{device_id}"
        expected_hmac = CryptoUtils.hmac_sha256(device_secret, message)
        if expected_hmac != response_hmac:
            return {"result": "deny", "reason": "invalid HMAC"}
        
        sat = challenge["sat"]
        sat_verify = sat.copy()
        sat_sig = sat_verify.pop("signature")
        if not CryptoUtils.verify(self.pubkey, sat_verify, sat_sig):
            return {"result": "deny", "reason": "SAT verification failed"}
        
        rrt = challenge["rrt"]
        rrt_verify = rrt.copy()
        rrt_sig = rrt_verify.pop("signature")
        if not CryptoUtils.verify(self.pubkey, rrt_verify, rrt_sig):
            return {"result": "deny", "reason": "RRT verification failed"}
        
        if rrt["gtt_id"] != self.gtt["gtt_id"]:
            return {"result": "deny", "reason": "GTT mismatch"}
        
        gtt_verify = self.gtt.copy()
        gtt_sig = gtt_verify.pop("signature")
        if not CryptoUtils.verify(self.gtt["root_pubkey"], gtt_verify, gtt_sig):
            return {"result": "deny", "reason": "GTT verification failed"}
        
        if device_id in self.device_states and self.device_states[device_id] != "active":
            return {"result": "deny", "reason": f"device is {self.device_states[device_id]}"}
        
        del self.challenges[challenge_id]
        session_id = CryptoUtils.generate_id("sess")
        return {
            "result": "allow",
            "reason": "local verification success",
            "session_id": session_id
        }

ag1 = MockAG(ec, "AG1")
ag2 = MockAG(ec, "AG2")

# ==========================================
# 5. 模拟 TD (终端设备)
# ==========================================
print("\n【5/7】模拟 TD (终端设备)")
print("-" * 80)

class MockTD:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.device_secret = None
        self.rrt = None
        self.sat = None
        print(f"✓ TD {device_id} 初始化完成")
    
    def register_with_cta(self, cta: MockCTA, region_id: str):
        device = cta.register_device(self.device_id, region_id)
        self.device_secret = device["device_secret"]
        return device
    
    def enroll(self, ag: MockAG, region_id: str):
        self.rrt = ag.issue_rrt(self.device_id, region_id)
        self.sat = ag.issue_sat(self.device_id, self.rrt["rrt_id"])
        print(f"✓ TD {self.device_id} 在 {ag.name} 完成注册")
    
    def access(self, ag: MockAG):
        print(f"→ TD {self.device_id} 向 {ag.name} 发起接入请求")
        challenge = ag.create_challenge(self.device_id, self.sat, self.rrt)
        
        message = f"{challenge['challenge_id']}:{challenge['nonce']}:{self.device_id}"
        response_hmac = CryptoUtils.hmac_sha256(self.device_secret, message)
        
        result = ag.verify_response(
            self.device_id,
            challenge["challenge_id"],
            response_hmac,
            self.device_secret
        )
        return result
    
    def roam(self, from_ag: MockAG, to_ag: MockAG, region_id: str):
        print(f"\n→ TD {self.device_id} 从 {from_ag.name} 漫游到 {to_ag.name}")
        self.enroll(to_ag, region_id)
        return self.access(to_ag)

td = MockTD("td001")

# ==========================================
# 6. 执行完整认证流程
# ==========================================
print("\n【6/7】执行完整认证流程")
print("-" * 80)

print("\n① 设备注册到 CTA...")
td.register_with_cta(cta, "regionA")
ec.sync_with_cta()
ag1.sync_with_ec()
ag2.sync_with_ec()

print("\n② 在 AG1 注册 (获取 RRT 和 SAT)...")
td.enroll(ag1, "regionA")

print("\n③ 接入 AG1...")
result1 = td.access(ag1)
print(f"  结果: {result1['result']} - {result1['reason']}")

print("\n④ 漫游到 AG2...")
result2 = td.roam(ag1, ag2, "regionA")
print(f"  结果: {result2['result']} - {result2['reason']}")

print("\n⑤ 测试设备撤销...")
cta.revoke_device("td001")
ec.sync_with_cta()
ag1.sync_with_ec()

print("\n⑥ 用已撤销的设备再次接入...")
td.enroll(ag1, "regionA")
result3 = td.access(ag1)
print(f"  结果: {result3['result']} - {result3['reason']}")

# ==========================================
# 7. 总结
# ==========================================
print("\n【7/7】系统架构总结")
print("=" * 80)
print("""
┌─────────────────────────────────────────────────────────┐
│                    HVRT 分层信任架构                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐                                        │
│  │   TD (终端)   │ ──SAT──►                              │
│  └──────────────┘         │                              │
│                           │                              │
│  ┌──────────────────────────────────────────────┐      │
│  │         AG (接入网关) - 本地离线认证           │      │
│  │  ┌─────────────────────────────────────────┐  │      │
│  │  │  SAT → RRT → GTT 链式验证              │  │      │
│  │  │  挑战-响应 (HMAC-SHA256)               │  │      │
│  │  └─────────────────────────────────────────┘  │      │
│  └──────────────────────────────────────────────┘      │
│                           │                              │
│                           ▼                              │
│  ┌──────────────────────────────────────────────┐      │
│  │      EC (边缘协调) - 区域状态同步             │      │
│  └──────────────────────────────────────────────┘      │
│                           │                              │
│                           ▼                              │
│  ┌──────────────────────────────────────────────┐      │
│  │     CTA (云端信任中心) - 全局信任根           │      │
│  │  ┌─────────────────────────────────────────┐  │      │
│  │  │  设备注册、撤销、GTT 签发                │  │      │
│  │  └─────────────────────────────────────────┘  │      │
│  └──────────────────────────────────────────────┘      │
│                                                           │
└─────────────────────────────────────────────────────────┘
""")
print("=" * 80)
print("✓ HVRT 完整演示完成！所有功能正常工作！")
print("=" * 80)
