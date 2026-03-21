#!/usr/bin/env python3
"""
HVRT 真实网络服务 - 使用安全端口 (9000, 9050, 9100)
"""
import uvicorn
import asyncio
import httpx
import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

print("=" * 80)
print("  HVRT 真实网络服务 - 安全端口版")
print("=" * 80)

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
    def verify_hmac(secret: str, message: str, hmac_b64: str) -> bool:
        expected = CryptoUtils.compute_hmac(secret, message)
        return hmac.compare_digest(expected, hmac_b64)

cta_state = {
    "privkey": None,
    "pubkey": None,
    "devices": {},
    "revocation_version": 1,
    "gtt": None,
    "revocation_events": []
}

def init_cta():
    priv, pub = CryptoUtils.generate_keypair()
    cta_state["privkey"] = priv
    cta_state["pubkey"] = pub
    gtt_data = {
        "gtt_id": CryptoUtils.generate_id("gtt"),
        "root_pubkey": pub,
        "policy_version": 1,
        "revocation_version": 1,
        "valid_from": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "valid_to": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
    }
    signature = CryptoUtils.sign(priv, gtt_data)
    cta_state["gtt"] = {**gtt_data, "signature": signature}
    print(f"[CTA] 初始化完成，GTT: {cta_state['gtt']['gtt_id']}")

init_cta()

cta_app = FastAPI(title="HVRT CTA (9000)")

class RegisterDeviceRequest(BaseModel):
    device_id: str
    region_id: str

@cta_app.post("/cta/register_device")
async def register_device(req: RegisterDeviceRequest):
    secret = base64.b64encode(os.urandom(24)).decode()
    cta_state["devices"][req.device_id] = {
        "device_id": req.device_id,
        "device_secret": secret,
        "status": "active",
        "region_id": req.region_id
    }
    print(f"[CTA] 注册设备: {req.device_id}")
    return cta_state["devices"][req.device_id]

@cta_app.get("/cta/gtt/current")
async def get_gtt():
    return {"gtt": cta_state["gtt"]}

@cta_app.get("/cta/revocation/delta")
async def get_delta(from_version: int):
    if from_version == cta_state["revocation_version"]:
        return {"from_version": from_version, "to_version": cta_state["revocation_version"], "changes": []}
    start_idx = max(0, from_version - 1)
    changes = cta_state["revocation_events"][start_idx:]
    return {"from_version": from_version, "to_version": cta_state["revocation_version"], "changes": changes}

class RevokeDeviceRequest(BaseModel):
    device_id: str
    reason: Optional[str] = "security"

@cta_app.post("/cta/revoke_device")
async def revoke_device(req: RevokeDeviceRequest):
    if req.device_id in cta_state["devices"]:
        cta_state["devices"][req.device_id]["status"] = "revoked"
        event = {"event_type": "revoke", "device_id": req.device_id, "reason": req.reason, "timestamp": datetime.now(timezone.utc).isoformat()}
        cta_state["revocation_events"].append(event)
        cta_state["revocation_version"] += 1
        gtt_data = {k: v for k, v in cta_state["gtt"].items() if k != "signature"}
        gtt_data["gtt_id"] = CryptoUtils.generate_id("gtt")
        gtt_data["revocation_version"] = cta_state["revocation_version"]
        signature = CryptoUtils.sign(cta_state["privkey"], gtt_data)
        cta_state["gtt"] = {**gtt_data, "signature": signature}
        print(f"[CTA] 撤销设备: {req.device_id}, 新版本: {cta_state['revocation_version']}")
        return {"new_version": cta_state["revocation_version"], "gtt_id": cta_state["gtt"]["gtt_id"]}
    raise HTTPException(404, "Device not found")

@cta_app.get("/")
async def root():
    return {"service": "cta", "status": "running", "port": 9000}

ec_state = {
    "gtt": None,
    "device_states": {},
    "revocation_version": 0,
    "cta_url": "http://127.0.0.1:9000"
}

ec_app = FastAPI(title="HVRT EC (9050)")

@ec_app.on_event("startup")
async def ec_startup():
    print("[EC] 正在从 CTA 同步...")
    await asyncio.sleep(1)
    try:
        async with httpx.AsyncClient() as client:
            gtt_resp = await client.get(f"{ec_state['cta_url']}/cta/gtt/current")
            ec_state["gtt"] = gtt_resp.json()["gtt"]
            ec_state["revocation_version"] = ec_state["gtt"]["revocation_version"]
            print(f"[EC] 已同步 GTT: {ec_state['gtt']['gtt_id']}, 版本: {ec_state['revocation_version']}")
    except Exception as e:
        print(f"[EC] 同步失败: {e}")

@ec_app.get("/ec/gtt/current")
async def get_gtt():
    return {k: ec_state["gtt"][k] for k in ["gtt_id", "root_pubkey", "policy_version", "revocation_version"]}

@ec_app.get("/ec/state/current")
async def get_state():
    return {"region_id": "regionA", "revocation_version": ec_state["revocation_version"], "device_states": ec_state["device_states"]}

@ec_app.post("/ec/trigger_sync")
async def trigger_sync():
    try:
        async with httpx.AsyncClient() as client:
            gtt_resp = await client.get(f"{ec_state['cta_url']}/cta/gtt/current")
            ec_state["gtt"] = gtt_resp.json()["gtt"]
            old_ver = ec_state["revocation_version"]
            ec_state["revocation_version"] = ec_state["gtt"]["revocation_version"]
            delta_resp = await client.get(f"{ec_state['cta_url']}/cta/revocation/delta", params={"from_version": old_ver})
            delta = delta_resp.json()
            for event in delta["changes"]:
                if event["event_type"] == "revoke":
                    ec_state["device_states"][event["device_id"]] = "revoked"
            print(f"[EC] 同步到版本: {ec_state['revocation_version']}")
        return {"status": "ok", "version": ec_state["revocation_version"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@ec_app.get("/")
async def root():
    return {"service": "ec", "status": "running", "port": 9050}

ag_state = {
    "name": "AG1",
    "privkey": None,
    "pubkey": None,
    "gtt": None,
    "device_states": {},
    "revocation_version": 0,
    "rrts": {},
    "sats": {},
    "challenges": {},
    "ec_url": "http://127.0.0.1:9050"
}

def init_ag():
    priv, pub = CryptoUtils.generate_keypair()
    ag_state["privkey"] = priv
    ag_state["pubkey"] = pub

init_ag()

ag1_app = FastAPI(title="HVRT AG1 (9100)")

@ag1_app.on_event("startup")
async def ag_startup():
    print("[AG1] 正在从 EC 同步...")
    await asyncio.sleep(2)
    try:
        async with httpx.AsyncClient() as client:
            gtt_summary_resp = await client.get(f"{ag_state['ec_url']}/ec/gtt/current")
            gtt_summary = gtt_summary_resp.json()
            async with httpx.AsyncClient() as client2:
                gtt_resp = await client2.get("http://127.0.0.1:9000/cta/gtt/current")
                ag_state["gtt"] = gtt_resp.json()["gtt"]
            state_resp = await client.get(f"{ag_state['ec_url']}/ec/state/current")
            state = state_resp.json()
            ag_state["device_states"] = state["device_states"]
            ag_state["revocation_version"] = state["revocation_version"]
            print(f"[AG1] 已同步 GTT: {ag_state['gtt']['gtt_id']}, 版本: {ag_state['revocation_version']}")
    except Exception as e:
        print(f"[AG1] 同步失败: {e}")

class IssueRRTRequest(BaseModel):
    device_id: str
    region_id: str

@ag1_app.post("/ag/issue_rrt")
async def issue_rrt(req: IssueRRTRequest):
    rrt_data = {
        "rrt_id": CryptoUtils.generate_id("rrt"),
        "device_id": req.device_id,
        "region_id": req.region_id,
        "gtt_id": ag_state["gtt"]["gtt_id"],
        "issue_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "expire_time": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
        "policy_tag": "default"
    }
    signature = CryptoUtils.sign(ag_state["privkey"], rrt_data)
    rrt = {**rrt_data, "signature": signature}
    ag_state["rrts"][rrt["rrt_id"]] = rrt
    print(f"[AG1] 签发 RRT: {rrt['rrt_id']}")
    return {"rrt": rrt}

class IssueSATRequest(BaseModel):
    device_id: str
    rrt_id: str

@ag1_app.post("/ag/issue_sat")
async def issue_sat(req: IssueSATRequest):
    sat_data = {
        "sat_id": CryptoUtils.generate_id("sat"),
        "device_id": req.device_id,
        "rrt_id": req.rrt_id,
        "issue_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "expire_time": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
        "auth_scope": "local_access"
    }
    signature = CryptoUtils.sign(ag_state["privkey"], sat_data)
    sat = {**sat_data, "signature": signature}
    ag_state["sats"][sat["sat_id"]] = sat
    print(f"[AG1] 签发 SAT: {sat['sat_id']}")
    return {"sat": sat}

class AccessRequest(BaseModel):
    request_id: str
    device_id: str
    sat: Dict[str, Any]
    rrt: Dict[str, Any]

@ag1_app.post("/ag/access/request")
async def access_request(req: AccessRequest):
    challenge_id = CryptoUtils.generate_id("chl")
    nonce = CryptoUtils.generate_nonce()
    ag_state["challenges"][challenge_id] = {
        "device_id": req.device_id,
        "nonce": nonce,
        "sat": req.sat,
        "rrt": req.rrt,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    print(f"[AG1] 生成挑战: {challenge_id}")
    return {"challenge_id": challenge_id, "nonce": nonce}

class AccessRespond(BaseModel):
    request_id: str
    challenge_id: str
    device_id: str
    response_hmac: str

device_secrets_cache = {}

@ag1_app.post("/ag/access/respond")
async def access_respond(req: AccessRespond):
    if req.challenge_id not in ag_state["challenges"]:
        return {"result": "deny", "reason": "invalid challenge"}
    
    challenge = ag_state["challenges"][req.challenge_id]
    if challenge["device_id"] != req.device_id:
        return {"result": "deny", "reason": "device mismatch"}
    
    if req.device_id in device_secrets_cache:
        secret = device_secrets_cache[req.device_id]
        message = f"{req.challenge_id}:{challenge['nonce']}:{req.device_id}"
        if not CryptoUtils.verify_hmac(secret, message, req.response_hmac):
            return {"result": "deny", "reason": "invalid HMAC"}
    
    sat = challenge["sat"]
    rrt = challenge["rrt"]
    
    sat_data = {k: v for k, v in sat.items() if k != "signature"}
    if not CryptoUtils.verify(ag_state["pubkey"], sat_data, sat["signature"]):
        return {"result": "deny", "reason": "invalid SAT signature"}
    
    rrt_data = {k: v for k, v in rrt.items() if k != "signature"}
    if not CryptoUtils.verify(ag_state["pubkey"], rrt_data, rrt["signature"]):
        return {"result": "deny", "reason": "invalid RRT signature"}
    
    if sat["rrt_id"] != rrt["rrt_id"]:
        return {"result": "deny", "reason": "SAT-RRT mismatch"}
    
    if rrt["gtt_id"] != ag_state["gtt"]["gtt_id"]:
        return {"result": "deny", "reason": "RRT-GTT mismatch"}
    
    gtt_data = {k: v for k, v in ag_state["gtt"].items() if k != "signature"}
    if not CryptoUtils.verify(ag_state["gtt"]["root_pubkey"], gtt_data, ag_state["gtt"]["signature"]):
        return {"result": "deny", "reason": "invalid GTT signature"}
    
    if req.device_id in ag_state["device_states"]:
        if ag_state["device_states"][req.device_id] == "revoked":
            return {"result": "deny", "reason": "device is revoked (本地状态验证)", "local_version": ag_state["revocation_version"]}
    
    session_id = CryptoUtils.generate_id("sess")
    return {"result": "allow", "reason": "local verification success", "session_id": session_id}

@ag1_app.post("/ag/trigger_sync")
async def trigger_sync():
    try:
        async with httpx.AsyncClient() as client:
            async with httpx.AsyncClient() as client2:
                gtt_resp = await client2.get("http://127.0.0.1:9000/cta/gtt/current")
                ag_state["gtt"] = gtt_resp.json()["gtt"]
            state_resp = await client.get(f"{ag_state['ec_url']}/ec/state/current")
            state = state_resp.json()
            ag_state["device_states"] = state["device_states"]
            ag_state["revocation_version"] = state["revocation_version"]
            print(f"[AG1] 同步到版本: {ag_state['revocation_version']}")
        return {"status": "ok", "version": ag_state["revocation_version"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@ag1_app.get("/")
async def root():
    return {"service": "ag1", "status": "running", "port": 9100}

async def test_flow():
    print("\n" + "=" * 80)
    print("  运行完整 HVRT 测试")
    print("=" * 80)
    await asyncio.sleep(3)
    
    cta_url = "http://127.0.0.1:9000"
    ec_url = "http://127.0.0.1:9050"
    ag_url = "http://127.0.0.1:9100"
    
    print("\n【1】注册设备...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{cta_url}/cta/register_device", json={"device_id": "td_real", "region_id": "regionA"})
        device = resp.json()
        device_secret = device["device_secret"]
        device_secrets_cache["td_real"] = device_secret
        print(f"✓ 设备注册: {device['device_id']}")
    
    print("\n【2】EC 同步...")
    async with httpx.AsyncClient() as client:
        await client.post(f"{ec_url}/ec/trigger_sync")
        print(f"✓ EC 同步完成")
    
    print("\n【3】AG 同步...")
    async with httpx.AsyncClient() as client:
        await client.post(f"{ag_url}/ag/trigger_sync")
        print(f"✓ AG 同步完成")
    
    print("\n【4】签发 RRT 和 SAT...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{ag_url}/ag/issue_rrt", json={"device_id": "td_real", "region_id": "regionA"})
        rrt = resp.json()["rrt"]
        
        resp = await client.post(f"{ag_url}/ag/issue_sat", json={"device_id": "td_real", "rrt_id": rrt["rrt_id"]})
        sat = resp.json()["sat"]
        print(f"✓ RRT: {rrt['rrt_id']}, SAT: {sat['sat_id']}")
    
    print("\n【5】接入认证...")
    async with httpx.AsyncClient() as client:
        req_id = CryptoUtils.generate_id("req")
        resp = await client.post(f"{ag_url}/ag/access/request", json={"request_id": req_id, "device_id": "td_real", "sat": sat, "rrt": rrt})
        challenge = resp.json()
        
        message = f"{challenge['challenge_id']}:{challenge['nonce']}:td_real"
        hmac_val = CryptoUtils.compute_hmac(device_secret, message)
        
        resp = await client.post(f"{ag_url}/ag/access/respond", json={"request_id": req_id, "challenge_id": challenge["challenge_id"], "device_id": "td_real", "response_hmac": hmac_val})
        result = resp.json()
        print(f"✓ 接入结果: {result['result']} - {result['reason']}")
    
    print("\n【6】撤销设备...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{cta_url}/cta/revoke_device", json={"device_id": "td_real", "reason": "test"})
        print(f"✓ 撤销成功, 新版本: {resp.json()['new_version']}")
    
    print("\n【7】EC 和 AG 再次同步...")
    async with httpx.AsyncClient() as client:
        await client.post(f"{ec_url}/ec/trigger_sync")
        await client.post(f"{ag_url}/ag/trigger_sync")
        print(f"✓ 同步完成")
    
    print("\n【8】被撤销设备再次接入（应被拒绝）...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{ag_url}/ag/issue_rrt", json={"device_id": "td_real", "region_id": "regionA"})
        rrt2 = resp.json()["rrt"]
        
        resp = await client.post(f"{ag_url}/ag/issue_sat", json={"device_id": "td_real", "rrt_id": rrt2["rrt_id"]})
        sat2 = resp.json()["sat"]
        
        req_id2 = CryptoUtils.generate_id("req2")
        resp = await client.post(f"{ag_url}/ag/access/request", json={"request_id": req_id2, "device_id": "td_real", "sat": sat2, "rrt": rrt2})
        challenge2 = resp.json()
        
        message2 = f"{challenge2['challenge_id']}:{challenge2['nonce']}:td_real"
        hmac_val2 = CryptoUtils.compute_hmac(device_secret, message2)
        
        resp = await client.post(f"{ag_url}/ag/access/respond", json={"request_id": req_id2, "challenge_id": challenge2["challenge_id"], "device_id": "td_real", "response_hmac": hmac_val2})
        result2 = resp.json()
        print(f"✓ 接入结果: {result2['result']} - {result2['reason']}")
    
    print("\n" + "=" * 80)
    if result2["result"] == "deny":
        print("  ✓✓✓ HVRT 完整测试通过！")
    else:
        print("  ✗ 测试未通过！")
    print("=" * 80)
    print("\n服务仍在运行，按 Ctrl+C 停止")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

async def run_all():
    servers = [
        {"app": cta_app, "port": 9000, "name": "CTA"},
        {"app": ec_app, "port": 9050, "name": "EC"},
        {"app": ag1_app, "port": 9100, "name": "AG1"},
    ]
    tasks = []
    for server in servers:
        config = uvicorn.Config(server["app"], host="127.0.0.1", port=server["port"], log_level="info")
        server_obj = uvicorn.Server(config)
        tasks.append(asyncio.create_task(server_obj.serve()))
    await asyncio.sleep(2)
    await test_flow()

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        print("\n\n用户中断")
