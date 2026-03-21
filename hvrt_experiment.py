#!/usr/bin/env python3
"""
HVRT 完整实验框架 - 三种模式 + 统一日志 + 批量测试
"""
import os
import sys
import json
import time
import base64
import hashlib
import hmac
import random
import statistics
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def ensure_logs_dir():
    if not os.path.exists("logs"):
        os.makedirs("logs")
ensure_logs_dir()

class JsonLogger:
    def __init__(self, scheme: str):
        self.scheme = scheme
        self.log_path = f"logs/{scheme}.jsonl"
    
    def log_auth_result(self, request_id: str, device_id: str, ag_id: str,
                        cta_version: int, ec_version: int, ag_version: int,
                        ticket_issue_ms: float, challenge_ms: float, 
                        ticket_verify_ms: float, state_check_ms: float,
                        sync_ms: float, total_latency_ms: float,
                        result: str, reason: str):
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record = {
            "ts": ts,
            "scheme": self.scheme,
            "event": "auth_result",
            "request_id": request_id,
            "device_id": device_id,
            "ag_id": ag_id,
            "cta_version": cta_version,
            "ec_version": ec_version,
            "ag_version": ag_version,
            "ticket_issue_ms": ticket_issue_ms,
            "challenge_ms": challenge_ms,
            "ticket_verify_ms": ticket_verify_ms,
            "state_check_ms": state_check_ms,
            "sync_ms": sync_ms,
            "total_latency_ms": total_latency_ms,
            "result": result,
            "reason": reason
        }
        self._write(record)
    
    def log_sync(self, node: str, from_version: int, to_version: int,
                 changes_count: int, sync_latency_ms: float,
                 bytes_transferred: int):
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record = {
            "ts": ts,
            "scheme": self.scheme,
            "event": "sync",
            "node": node,
            "from_version": from_version,
            "to_version": to_version,
            "changes_count": changes_count,
            "sync_latency_ms": sync_latency_ms,
            "bytes_transferred": bytes_transferred
        }
        self._write(record)
    
    def log_roaming_result(self, device_id: str, from_ag: str, to_ag: str,
                           roaming_latency_ms: float, result: str):
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record = {
            "ts": ts,
            "scheme": self.scheme,
            "event": "roaming_auth_result",
            "device_id": device_id,
            "from_ag": from_ag,
            "to_ag": to_ag,
            "roaming_latency_ms": roaming_latency_ms,
            "result": result
        }
        self._write(record)
    
    def log_revocation_stage(self, stage: str, device_id: str,
                             cta_version: int, ec_version: int, ag_version: int,
                             result: str, reason: str):
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record = {
            "ts": ts,
            "scheme": self.scheme,
            "event": "revocation_stage_result",
            "stage": stage,
            "device_id": device_id,
            "cta_version": cta_version,
            "ec_version": ec_version,
            "ag_version": ag_version,
            "result": result,
            "reason": reason
        }
        self._write(record)
    
    def _write(self, record: Dict):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

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

class MockCTA:
    def __init__(self, logger: JsonLogger):
        self.logger = logger
        self.privkey, self.pubkey = CryptoUtils.generate_keypair()
        self.devices = {}
        self.revocation_version = 1
        self.gtt = None
        self.revocation_events = []
        self._generate_gtt()
    
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
    
    def register_device(self, device_id: str, region_id: str):
        secret = base64.b64encode(os.urandom(24)).decode()
        self.devices[device_id] = {
            "device_id": device_id,
            "device_secret": secret,
            "status": "active",
            "region_id": region_id
        }
        return self.devices[device_id]
    
    def revoke_device(self, device_id: str, reason: str = "security"):
        if device_id in self.devices:
            self.devices[device_id]["status"] = "revoked"
            event = {
                "event_type": "revoke",
                "device_id": device_id,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.revocation_events.append(event)
            self.revocation_version += 1
            self._generate_gtt()
            return True
        return False
    
    def get_gtt(self):
        return self.gtt
    
    def get_revocation_delta(self, from_version: int):
        if from_version == self.revocation_version:
            return {
                "from_version": from_version,
                "to_version": self.revocation_version,
                "changes": []
            }
        start_idx = max(0, from_version - 1)
        changes = self.revocation_events[start_idx:]
        return {
            "from_version": from_version,
            "to_version": self.revocation_version,
            "changes": changes
        }
    
    def online_verify(self, device_id: str, sat: Dict, rrt: Dict, ag_pubkey: str):
        time.sleep(0.003 + random.uniform(0, 0.002))
        sat_data = {k: v for k, v in sat.items() if k != "signature"}
        if not CryptoUtils.verify(ag_pubkey, sat_data, sat["signature"]):
            return {"result": "deny", "reason": "invalid SAT signature"}
        
        rrt_data = {k: v for k, v in rrt.items() if k != "signature"}
        if not CryptoUtils.verify(ag_pubkey, rrt_data, rrt["signature"]):
            return {"result": "deny", "reason": "invalid RRT signature"}
        
        if sat["rrt_id"] != rrt["rrt_id"]:
            return {"result": "deny", "reason": "SAT-RRT mismatch"}
        
        if rrt["gtt_id"] != self.gtt["gtt_id"]:
            return {"result": "deny", "reason": "RRT-GTT mismatch"}
        
        gtt_data = {k: v for k, v in self.gtt.items() if k != "signature"}
        if not CryptoUtils.verify(self.gtt["root_pubkey"], gtt_data, self.gtt["signature"]):
            return {"result": "deny", "reason": "invalid GTT signature"}
        
        if device_id in self.devices:
            if self.devices[device_id]["status"] == "revoked":
                return {"result": "deny", "reason": "device is revoked (CTA verified)"}
        
        return {"result": "allow", "reason": "CTA verification success"}
    
    def get_device_status_receipt(self, device_id: str):
        if device_id not in self.devices:
            return None
        receipt_data = {
            "device_id": device_id,
            "status": self.devices[device_id]["status"],
            "revocation_version": self.revocation_version,
            "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        signature = CryptoUtils.sign(self.privkey, receipt_data)
        return {**receipt_data, "signature": signature}

class MockEC:
    def __init__(self, logger: JsonLogger, cta: MockCTA):
        self.logger = logger
        self.cta = cta
        self.gtt = None
        self.device_states = {}
        self.revocation_version = 0
        self.sync_with_cta()
    
    def sync_with_cta(self):
        start_time = time.time()
        old_version = self.revocation_version
        self.gtt = self.cta.get_gtt()
        self.revocation_version = self.gtt["revocation_version"]
        delta = self.cta.get_revocation_delta(old_version)
        for event in delta["changes"]:
            if event["event_type"] == "revoke":
                self.device_states[event["device_id"]] = "revoked"
        sync_latency_ms = (time.time() - start_time) * 1000
        self.logger.log_sync(
            node="ec",
            from_version=old_version,
            to_version=self.revocation_version,
            changes_count=len(delta["changes"]),
            sync_latency_ms=sync_latency_ms,
            bytes_transferred=500
        )
        return sync_latency_ms
    
    def get_gtt(self):
        return self.gtt
    
    def get_state(self):
        return {
            "revocation_version": self.revocation_version,
            "device_states": self.device_states
        }

class MockAG:
    def __init__(self, logger: JsonLogger, ec: MockEC, name: str):
        self.logger = logger
        self.ec = ec
        self.name = name
        self.privkey, self.pubkey = CryptoUtils.generate_keypair()
        self.gtt = None
        self.device_states = {}
        self.revocation_version = 0
        self.rrts = {}
        self.sats = {}
        self.challenges = {}
        self.sync_with_ec()
    
    def sync_with_ec(self):
        start_time = time.time()
        old_version = self.revocation_version
        self.gtt = self.ec.get_gtt()
        state = self.ec.get_state()
        self.device_states = dict(state["device_states"])
        self.revocation_version = state["revocation_version"]
        sync_latency_ms = (time.time() - start_time) * 1000
        self.logger.log_sync(
            node=self.name,
            from_version=old_version,
            to_version=self.revocation_version,
            changes_count=0,
            sync_latency_ms=sync_latency_ms,
            bytes_transferred=600
        )
        return sync_latency_ms
    
    def issue_rrt(self, device_id: str, region_id: str):
        start_time = time.time()
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
        return rrt, (time.time() - start_time) * 1000
    
    def issue_sat(self, device_id: str, rrt_id: str):
        start_time = time.time()
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
        return sat, (time.time() - start_time) * 1000
    
    def generate_challenge(self, device_id: str):
        start_time = time.time()
        challenge_id = CryptoUtils.generate_id("chl")
        nonce = CryptoUtils.generate_nonce()
        self.challenges[challenge_id] = {
            "device_id": device_id,
            "nonce": nonce,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        return challenge_id, nonce, (time.time() - start_time) * 1000
    
    def verify_response_hvrt(self, challenge_id: str, device_id: str, 
                             response_hmac: str, device_secret: str,
                             sat: Dict, rrt: Dict):
        total_start = time.time()
        
        if challenge_id not in self.challenges:
            return {"result": "deny", "reason": "invalid challenge", "timings": {}}
        challenge = self.challenges[challenge_id]
        if challenge["device_id"] != device_id:
            return {"result": "deny", "reason": "device mismatch", "timings": {}}
        
        message = f"{challenge_id}:{challenge['nonce']}:{device_id}"
        if not CryptoUtils.verify_hmac(device_secret, message, response_hmac):
            return {"result": "deny", "reason": "invalid HMAC", "timings": {}}
        
        verify_start = time.time()
        sat_data = {k: v for k, v in sat.items() if k != "signature"}
        if not CryptoUtils.verify(self.pubkey, sat_data, sat["signature"]):
            return {"result": "deny", "reason": "invalid SAT signature", "timings": {}}
        rrt_data = {k: v for k, v in rrt.items() if k != "signature"}
        if not CryptoUtils.verify(self.pubkey, rrt_data, rrt["signature"]):
            return {"result": "deny", "reason": "invalid RRT signature", "timings": {}}
        if sat["rrt_id"] != rrt["rrt_id"]:
            return {"result": "deny", "reason": "SAT-RRT mismatch", "timings": {}}
        if rrt["gtt_id"] != self.gtt["gtt_id"]:
            return {"result": "deny", "reason": "RRT-GTT mismatch", "timings": {}}
        gtt_data = {k: v for k, v in self.gtt.items() if k != "signature"}
        if not CryptoUtils.verify(self.gtt["root_pubkey"], gtt_data, self.gtt["signature"]):
            return {"result": "deny", "reason": "invalid GTT signature", "timings": {}}
        ticket_verify_ms = (time.time() - verify_start) * 1000
        
        state_check_start = time.time()
        if device_id in self.device_states:
            if self.device_states[device_id] == "revoked":
                state_check_ms = (time.time() - state_check_start) * 1000
                total_latency_ms = (time.time() - total_start) * 1000
                return {
                    "result": "deny", 
                    "reason": "device is revoked (AG local state)",
                    "timings": {
                        "ticket_verify_ms": ticket_verify_ms,
                        "state_check_ms": state_check_ms,
                        "total_latency_ms": total_latency_ms
                    }
                }
        state_check_ms = (time.time() - state_check_start) * 1000
        total_latency_ms = (time.time() - total_start) * 1000
        
        return {
            "result": "allow", 
            "reason": "HVRT local verification success",
            "timings": {
                "ticket_verify_ms": ticket_verify_ms,
                "state_check_ms": state_check_ms,
                "total_latency_ms": total_latency_ms
            }
        }

class MockTD:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.device_secret = None
        self.rrt = None
        self.sat = None
        self.status_receipt = None
    
    def set_credentials(self, secret: str, rrt: Dict, sat: Dict):
        self.device_secret = secret
        self.rrt = rrt
        self.sat = sat
    
    def compute_response_hmac(self, challenge_id: str, nonce: str):
        message = f"{challenge_id}:{nonce}:{self.device_id}"
        return CryptoUtils.compute_hmac(self.device_secret, message)

def run_hvrt_experiment(rounds: int = 50, roaming_rounds: int = 20):
    print("=" * 80)
    print("  HVRT 完整实验 - 三种模式对比")
    print("=" * 80)
    
    for f in ["logs/hvrt.jsonl", "logs/centralized.jsonl", "logs/terminal_online_status.jsonl"]:
        if os.path.exists(f):
            os.remove(f)
    
    logger_hvrt = JsonLogger("hvrt")
    logger_centralized = JsonLogger("centralized")
    logger_terminal = JsonLogger("terminal_online_status")
    
    print("\n【初始化】创建 CTA, EC, AG1, AG2, TD...")
    cta = MockCTA(logger_hvrt)
    ec = MockEC(logger_hvrt, cta)
    ag1 = MockAG(logger_hvrt, ec, "ag1")
    ag2 = MockAG(logger_hvrt, ec, "ag2")
    td = MockTD("td001")
    
    device_data = cta.register_device("td001", "regionA")
    td.device_secret = device_data["device_secret"]
    
    print(f"\n【模式 A: HVRT】运行 {rounds} 次认证...")
    for i in range(rounds):
        request_id = CryptoUtils.generate_id("req")
        
        rrt, ticket_issue_ms = ag1.issue_rrt("td001", "regionA")
        sat, _ = ag1.issue_sat("td001", rrt["rrt_id"])
        
        challenge_id, nonce, challenge_ms = ag1.generate_challenge("td001")
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        
        result = ag1.verify_response_hvrt(
            challenge_id, "td001", response_hmac,
            td.device_secret, sat, rrt
        )
        
        logger_hvrt.log_auth_result(
            request_id=request_id,
            device_id="td001",
            ag_id="ag1",
            cta_version=cta.revocation_version,
            ec_version=ec.revocation_version,
            ag_version=ag1.revocation_version,
            ticket_issue_ms=ticket_issue_ms,
            challenge_ms=challenge_ms,
            ticket_verify_ms=result["timings"]["ticket_verify_ms"],
            state_check_ms=result["timings"]["state_check_ms"],
            sync_ms=0,
            total_latency_ms=result["timings"]["total_latency_ms"],
            result=result["result"],
            reason=result["reason"]
        )
        
        if (i + 1) % 10 == 0:
            print(f"  已完成 {i + 1}/{rounds} 次...")
    
    print(f"\n【模式 B: Centralized】运行 {rounds} 次认证 (模拟)...")
    for i in range(rounds):
        request_id = CryptoUtils.generate_id("req")
        
        rrt, ticket_issue_ms = ag1.issue_rrt("td001", "regionA")
        sat, _ = ag1.issue_sat("td001", rrt["rrt_id"])
        
        challenge_id, nonce, challenge_ms = ag1.generate_challenge("td001")
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        
        start_verify = time.time()
        centralized_result = cta.online_verify("td001", sat, rrt, ag1.pubkey)
        centralized_verify_ms = (time.time() - start_verify) * 1000
        
        logger_centralized.log_auth_result(
            request_id=request_id,
            device_id="td001",
            ag_id="ag1",
            cta_version=cta.revocation_version,
            ec_version=ec.revocation_version,
            ag_version=ag1.revocation_version,
            ticket_issue_ms=ticket_issue_ms,
            challenge_ms=challenge_ms,
            ticket_verify_ms=centralized_verify_ms,
            state_check_ms=0,
            sync_ms=0,
            total_latency_ms=ticket_issue_ms + challenge_ms + centralized_verify_ms,
            result=centralized_result["result"],
            reason=centralized_result["reason"]
        )
        
        if (i + 1) % 10 == 0:
            print(f"  已完成 {i + 1}/{rounds} 次...")
    
    print(f"\n【模式 C: Terminal-Online-Status】运行 {rounds} 次认证 (模拟)...")
    for i in range(rounds):
        request_id = CryptoUtils.generate_id("req")
        
        receipt_start = time.time()
        time.sleep(0.0015 + random.uniform(0, 0.001))
        status_receipt = cta.get_device_status_receipt("td001")
        receipt_ms = (time.time() - receipt_start) * 1000
        
        rrt, ticket_issue_ms = ag1.issue_rrt("td001", "regionA")
        sat, _ = ag1.issue_sat("td001", rrt["rrt_id"])
        
        challenge_id, nonce, challenge_ms = ag1.generate_challenge("td001")
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        
        start_verify = time.time()
        terminal_result = ag1.verify_response_hvrt(
            challenge_id, "td001", response_hmac,
            td.device_secret, sat, rrt
        )
        terminal_verify_ms = (time.time() - start_verify) * 1000
        
        logger_terminal.log_auth_result(
            request_id=request_id,
            device_id="td001",
            ag_id="ag1",
            cta_version=cta.revocation_version,
            ec_version=ec.revocation_version,
            ag_version=ag1.revocation_version,
            ticket_issue_ms=ticket_issue_ms,
            challenge_ms=challenge_ms,
            ticket_verify_ms=terminal_verify_ms,
            state_check_ms=receipt_ms,
            sync_ms=0,
            total_latency_ms=ticket_issue_ms + challenge_ms + terminal_verify_ms + receipt_ms,
            result=terminal_result["result"],
            reason=terminal_result["reason"]
        )
        
        if (i + 1) % 10 == 0:
            print(f"  已完成 {i + 1}/{rounds} 次...")
    
    print(f"\n【模式 A: HVRT】运行 {roaming_rounds} 次漫游...")
    for i in range(roaming_rounds):
        start_roam = time.time()
        rrt2, _ = ag2.issue_rrt("td001", "regionA")
        sat2, _ = ag2.issue_sat("td001", rrt2["rrt_id"])
        challenge_id, nonce, _ = ag2.generate_challenge("td001")
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        result = ag2.verify_response_hvrt(challenge_id, "td001", response_hmac, td.device_secret, sat2, rrt2)
        roaming_latency_ms = (time.time() - start_roam) * 1000
        logger_hvrt.log_roaming_result("td001", "ag1", "ag2", roaming_latency_ms, result["result"])
        
        start_roam_back = time.time()
        rrt1, _ = ag1.issue_rrt("td001", "regionA")
        sat1, _ = ag1.issue_sat("td001", rrt1["rrt_id"])
        challenge_id2, nonce2, _ = ag1.generate_challenge("td001")
        response_hmac2 = td.compute_response_hmac(challenge_id2, nonce2)
        result2 = ag1.verify_response_hvrt(challenge_id2, "td001", response_hmac2, td.device_secret, sat1, rrt1)
        roaming_latency_ms2 = (time.time() - start_roam_back) * 1000
        logger_hvrt.log_roaming_result("td001", "ag2", "ag1", roaming_latency_ms2, result2["result"])
        
        if (i + 1) % 5 == 0:
            print(f"  已完成 {i + 1}/{roaming_rounds} 次...")
    
    print(f"\n【模式 B: Centralized】运行 {roaming_rounds} 次漫游...")
    for i in range(roaming_rounds):
        start_roam = time.time()
        rrt2, _ = ag2.issue_rrt("td001", "regionA")
        sat2, _ = ag2.issue_sat("td001", rrt2["rrt_id"])
        challenge_id, nonce, _ = ag2.generate_challenge("td001")
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        centralized_result = cta.online_verify("td001", sat2, rrt2, ag2.pubkey)
        roaming_latency_ms = (time.time() - start_roam) * 1000
        logger_centralized.log_roaming_result("td001", "ag1", "ag2", roaming_latency_ms, centralized_result["result"])
        
        start_roam_back = time.time()
        rrt1, _ = ag1.issue_rrt("td001", "regionA")
        sat1, _ = ag1.issue_sat("td001", rrt1["rrt_id"])
        challenge_id2, nonce2, _ = ag1.generate_challenge("td001")
        response_hmac2 = td.compute_response_hmac(challenge_id2, nonce2)
        centralized_result2 = cta.online_verify("td001", sat1, rrt1, ag1.pubkey)
        roaming_latency_ms2 = (time.time() - start_roam_back) * 1000
        logger_centralized.log_roaming_result("td001", "ag2", "ag1", roaming_latency_ms2, centralized_result2["result"])
        
        if (i + 1) % 5 == 0:
            print(f"  已完成 {i + 1}/{roaming_rounds} 次...")
    
    print(f"\n【模式 C: Terminal-Online-Status】运行 {roaming_rounds} 次漫游...")
    for i in range(roaming_rounds):
        start_roam = time.time()
        time.sleep(0.0015 + random.uniform(0, 0.001))
        status_receipt = cta.get_device_status_receipt("td001")
        rrt2, _ = ag2.issue_rrt("td001", "regionA")
        sat2, _ = ag2.issue_sat("td001", rrt2["rrt_id"])
        challenge_id, nonce, _ = ag2.generate_challenge("td001")
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        terminal_result = ag2.verify_response_hvrt(challenge_id, "td001", response_hmac, td.device_secret, sat2, rrt2)
        roaming_latency_ms = (time.time() - start_roam) * 1000
        logger_terminal.log_roaming_result("td001", "ag1", "ag2", roaming_latency_ms, terminal_result["result"])
        
        start_roam_back = time.time()
        time.sleep(0.0015 + random.uniform(0, 0.001))
        status_receipt2 = cta.get_device_status_receipt("td001")
        rrt1, _ = ag1.issue_rrt("td001", "regionA")
        sat1, _ = ag1.issue_sat("td001", rrt1["rrt_id"])
        challenge_id2, nonce2, _ = ag1.generate_challenge("td001")
        response_hmac2 = td.compute_response_hmac(challenge_id2, nonce2)
        terminal_result2 = ag1.verify_response_hvrt(challenge_id2, "td001", response_hmac2, td.device_secret, sat1, rrt1)
        roaming_latency_ms2 = (time.time() - start_roam_back) * 1000
        logger_terminal.log_roaming_result("td001", "ag2", "ag1", roaming_latency_ms2, terminal_result2["result"])
        
        if (i + 1) % 5 == 0:
            print(f"  已完成 {i + 1}/{roaming_rounds} 次...")
    
    print("\n" + "=" * 80)
    print("  图 3: 撤销前后的认证结果测试")
    print("=" * 80)
    
    print("\n阶段 1: 撤销前")
    request_id = CryptoUtils.generate_id("req")
    rrt, ticket_issue_ms = ag1.issue_rrt("td001", "regionA")
    sat, _ = ag1.issue_sat("td001", rrt["rrt_id"])
    challenge_id, nonce, challenge_ms = ag1.generate_challenge("td001")
    response_hmac = td.compute_response_hmac(challenge_id, nonce)
    result1 = ag1.verify_response_hvrt(
        challenge_id, "td001", response_hmac,
        td.device_secret, sat, rrt
    )
    print(f"  CTA版本={cta.revocation_version}, EC版本={ec.revocation_version}, AG版本={ag1.revocation_version}")
    print(f"  结果: {result1['result']} - {result1['reason']}")
    logger_hvrt.log_revocation_stage(
        stage="before_revoke",
        device_id="td001",
        cta_version=cta.revocation_version,
        ec_version=ec.revocation_version,
        ag_version=ag1.revocation_version,
        result=result1["result"],
        reason=result1["reason"]
    )
    
    print("\n阶段 2: CTA 已撤销，但 EC/AG 尚未同步")
    cta.revoke_device("td001", "test revocation")
    request_id = CryptoUtils.generate_id("req")
    rrt, ticket_issue_ms = ag1.issue_rrt("td001", "regionA")
    sat, _ = ag1.issue_sat("td001", rrt["rrt_id"])
    challenge_id, nonce, challenge_ms = ag1.generate_challenge("td001")
    response_hmac = td.compute_response_hmac(challenge_id, nonce)
    result2 = ag1.verify_response_hvrt(
        challenge_id, "td001", response_hmac,
        td.device_secret, sat, rrt
    )
    print(f"  CTA版本={cta.revocation_version}, EC版本={ec.revocation_version}, AG版本={ag1.revocation_version}")
    print(f"  结果: {result2['result']} - {result2['reason']}")
    logger_hvrt.log_revocation_stage(
        stage="cta_revoked_no_sync",
        device_id="td001",
        cta_version=cta.revocation_version,
        ec_version=ec.revocation_version,
        ag_version=ag1.revocation_version,
        result=result2["result"],
        reason=result2["reason"]
    )
    
    print("\n阶段 3: EC 已同步，AG 未同步")
    ec.sync_with_cta()
    request_id = CryptoUtils.generate_id("req")
    rrt, ticket_issue_ms = ag1.issue_rrt("td001", "regionA")
    sat, _ = ag1.issue_sat("td001", rrt["rrt_id"])
    challenge_id, nonce, challenge_ms = ag1.generate_challenge("td001")
    response_hmac = td.compute_response_hmac(challenge_id, nonce)
    result3 = ag1.verify_response_hvrt(
        challenge_id, "td001", response_hmac,
        td.device_secret, sat, rrt
    )
    print(f"  CTA版本={cta.revocation_version}, EC版本={ec.revocation_version}, AG版本={ag1.revocation_version}")
    print(f"  结果: {result3['result']} - {result3['reason']}")
    logger_hvrt.log_revocation_stage(
        stage="ec_synced_ag_not_synced",
        device_id="td001",
        cta_version=cta.revocation_version,
        ec_version=ec.revocation_version,
        ag_version=ag1.revocation_version,
        result=result3["result"],
        reason=result3["reason"]
    )
    
    print("\n阶段 4: EC 与 AG 均同步")
    ag1.sync_with_ec()
    request_id = CryptoUtils.generate_id("req")
    rrt, ticket_issue_ms = ag1.issue_rrt("td001", "regionA")
    sat, _ = ag1.issue_sat("td001", rrt["rrt_id"])
    challenge_id, nonce, challenge_ms = ag1.generate_challenge("td001")
    response_hmac = td.compute_response_hmac(challenge_id, nonce)
    result4 = ag1.verify_response_hvrt(
        challenge_id, "td001", response_hmac,
        td.device_secret, sat, rrt
    )
    print(f"  CTA版本={cta.revocation_version}, EC版本={ec.revocation_version}, AG版本={ag1.revocation_version}")
    print(f"  结果: {result4['result']} - {result4['reason']}")
    logger_hvrt.log_revocation_stage(
        stage="ec_ag_both_synced",
        device_id="td001",
        cta_version=cta.revocation_version,
        ec_version=ec.revocation_version,
        ag_version=ag1.revocation_version,
        result=result4["result"],
        reason=result4["reason"]
    )
    
    print("\n" + "=" * 80)
    print("  实验完成！分析日志...")
    print("=" * 80)
    
    analyze_logs()
    
    print("\n✅ 所有实验完成！")
    print("日志已保存到:")
    print("  logs/hvrt.jsonl")
    print("  logs/centralized.jsonl")
    print("  logs/terminal_online_status.jsonl")

def analyze_logs():
    files = {
        "HVRT": "logs/hvrt.jsonl",
        "Centralized": "logs/centralized.jsonl",
        "Terminal-Online-Status": "logs/terminal_online_status.jsonl"
    }
    
    data = defaultdict(list)
    roaming_data = defaultdict(list)
    revocation_data = []
    
    for name, path in files.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    if rec.get("event") == "auth_result":
                        data[name].append(rec["total_latency_ms"])
                    elif rec.get("event") == "roaming_auth_result":
                        roaming_data[name].append(rec["roaming_latency_ms"])
                    elif rec.get("event") == "revocation_stage_result":
                        revocation_data.append(rec)
    
    print("\n【图 1: 平均认证时延 (ms)】")
    print("-" * 50)
    print(f"  {'方案':<25} {'均值':<10} {'中位数':<10} {'P95':<10} {'标准差':<10}")
    print("-" * 80)
    for k, v in data.items():
        if len(v) > 5:
            vals = v[5:]
            sorted_vals = sorted(vals)
            p95 = sorted_vals[int(len(sorted_vals) * 0.95)] if sorted_vals else 0
            print(f"  {k:<25} {statistics.mean(vals):<10.2f} {statistics.median(vals):<10.2f} {p95:<10.2f} {statistics.pstdev(vals):<10.2f}")
        elif v:
            sorted_vals = sorted(v)
            p95 = sorted_vals[int(len(sorted_vals) * 0.95)] if sorted_vals else 0
            print(f"  {k:<25} {statistics.mean(v):<10.2f} {statistics.median(v):<10.2f} {p95:<10.2f} {statistics.pstdev(v):<10.2f}")
    
    if roaming_data:
        print(f"\n【图 2: 漫游认证时延 (ms)】")
        print("-" * 50)
        print(f"  {'方案':<25} {'均值':<10} {'中位数':<10} {'P95':<10} {'标准差':<10}")
        print("-" * 80)
        for k, v in roaming_data.items():
            if v:
                sorted_vals = sorted(v)
                p95 = sorted_vals[int(len(sorted_vals) * 0.95)] if sorted_vals else 0
                print(f"  {k:<25} {statistics.mean(v):<10.2f} {statistics.median(v):<10.2f} {p95:<10.2f} {statistics.pstdev(v):<10.2f}")
    
    if revocation_data:
        print(f"\n【图 3: 撤销前后认证结果】")
        print("-" * 50)
        for rec in revocation_data:
            stage_name = {
                "before_revoke": "撤销前",
                "cta_revoked_no_sync": "CTA已撤销未同步",
                "ec_synced_ag_not_synced": "EC已同步AG未同步",
                "ec_ag_both_synced": "EC与AG均同步"
            }.get(rec["stage"], rec["stage"])
            print(f"  {stage_name:<20} (CTA={rec['cta_version']}, EC={rec['ec_version']}, AG={rec['ag_version']}) → {rec['result']}")

if __name__ == "__main__":
    try:
        run_hvrt_experiment(rounds=50, roaming_rounds=20)
    except KeyboardInterrupt:
        print("\n\n用户中断")
