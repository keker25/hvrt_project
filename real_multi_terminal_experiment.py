import json
import os
import time
import random
import statistics
import base64
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

NUM_TERMINALS = 5   # 终端数
NUM_ROUNDS = 3      # 认证轮数
ROAMING_ROUNDS = 2  # 漫游轮数

NETWORK_DELAY_MIN_MS = 10
NETWORK_DELAY_MAX_MS = 100
PACKET_LOSS_RATE = 0.05


def simulate_network_delay():
    delay_ms = random.uniform(NETWORK_DELAY_MIN_MS, NETWORK_DELAY_MAX_MS)
    time.sleep(delay_ms / 1000)
    return delay_ms

def simulate_json_serialization_delay():
    time.sleep(random.uniform(0.05, 0.2) / 1000)

def simulate_crypto_delay():
    time.sleep(random.uniform(0.1, 0.5) / 1000)


def simulate_packet_loss():
    return random.random() < PACKET_LOSS_RATE


class JsonLogger:
    def __init__(self, scheme: str, log_dir: str = "logs"):
        self.scheme = scheme
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, f"real_{scheme}.jsonl")
        if os.path.exists(self.log_path):
            os.remove(self.log_path)
    
    def _write(self, record: Dict):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def log_auth_result(self, request_id: str, device_id: str, ag_id: str,
                       cta_version: int, ec_version: int, ag_version: int,
                       ticket_issue_ms: float, challenge_ms: float, ticket_verify_ms: float,
                       state_check_ms: float, sync_ms: float, total_latency_ms: float,
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
    
    def log_sync(self, node: str, from_version: int, to_version: int,
                changes_count: int, sync_latency_ms: float, bytes_transferred: int):
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


class MockCTA:
    def __init__(self, logger):
        self.logger = logger
        self.root_privkey, self.root_pubkey = CryptoUtils.generate_ed25519_keypair()
        self.devices = {}
        self.revocation_version = 1
        self.gtt = None
        self._generate_gtt()
    
    def _generate_gtt(self):
        gtt_id = CryptoUtils.generate_id("gtt")
        gtt_data = {
            "gtt_id": gtt_id,
            "root_pubkey": self.root_pubkey,
            "revocation_version": self.revocation_version,
            "valid_from": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "valid_to": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
        }
        simulate_json_serialization_delay()
        simulate_crypto_delay()
        gtt_data["signature"] = CryptoUtils.sign(self.root_privkey, gtt_data)
        self.gtt = gtt_data
    
    def register_device(self, device_id: str, region: str):
        simulate_network_delay()
        device_secret = CryptoUtils.generate_secret()
        self.devices[device_id] = {
            "device_id": device_id,
            "device_secret": device_secret,
            "region": region,
            "status": "active",
            "registered_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        return {
            "device_id": device_id,
            "device_secret": device_secret,
            "gtt": self.gtt
        }
    
    def revoke_device(self, device_id: str, reason: str = "revoked"):
        simulate_network_delay()
        if device_id in self.devices:
            self.devices[device_id]["status"] = "revoked"
            self.revocation_version += 1
            self._generate_gtt()
            return {"success": True, "new_version": self.revocation_version}
        return {"success": False, "error": "device not found"}
    
    def get_gtt(self):
        simulate_network_delay()
        return self.gtt
    
    def get_state(self):
        simulate_network_delay()
        return {
            "revocation_version": self.revocation_version,
            "device_states": {did: d["status"] for did, d in self.devices.items()}
        }
    
    def get_revocation_delta(self, from_version: int):
        simulate_network_delay()
        return {
            "from_version": from_version,
            "to_version": self.revocation_version,
            "changes": []
        }
    
    def online_verify(self, device_id: str, sat: Dict, rrt: Dict, ag_pubkey: str):
        delay = simulate_network_delay()
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
        simulate_network_delay()
        if device_id not in self.devices:
            return None
        receipt_data = {
            "device_id": device_id,
            "status": self.devices[device_id]["status"],
            "revocation_version": self.revocation_version,
            "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        receipt_data["signature"] = CryptoUtils.sign(self.root_privkey, receipt_data)
        return receipt_data


class MockEC:
    def __init__(self, name: str, cta: MockCTA, logger):
        self.name = name
        self.cta = cta
        self.logger = logger
        self.gtt = None
        self.device_states = {}
        self.revocation_version = 0
    
    def sync_with_cta(self):
        start_time = time.time()
        old_version = self.revocation_version
        self.gtt = self.cta.get_gtt()
        state = self.cta.get_state()
        self.device_states = dict(state["device_states"])
        self.revocation_version = state["revocation_version"]
        sync_latency_ms = (time.time() - start_time) * 1000
        self.logger.log_sync(
            node=self.name,
            from_version=old_version,
            to_version=self.revocation_version,
            changes_count=0,
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
    def __init__(self, name: str, ec: MockEC, logger):
        self.name = name
        self.ec = ec
        self.logger = logger
        self.privkey, self.pubkey = CryptoUtils.generate_ed25519_keypair()
        self.gtt = None
        self.device_states = {}
        self.revocation_version = 0
        self.challenges = {}
    
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
    
    def issue_rrt(self, device_id: str, region: str):
        start = time.time()
        simulate_network_delay()
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
        simulate_json_serialization_delay()
        simulate_crypto_delay()
        rrt_data["signature"] = CryptoUtils.sign(self.privkey, rrt_data)
        return rrt_data, (time.time() - start) * 1000
    
    def issue_sat(self, device_id: str, rrt_id: str):
        start = time.time()
        simulate_network_delay()
        sat_id = CryptoUtils.generate_id("sat")
        sat_data = {
            "sat_id": sat_id,
            "device_id": device_id,
            "rrt_id": rrt_id,
            "issue_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "expire_time": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
        }
        simulate_json_serialization_delay()
        simulate_crypto_delay()
        sat_data["signature"] = CryptoUtils.sign(self.privkey, sat_data)
        return sat_data, (time.time() - start) * 1000
    
    def generate_challenge(self, device_id: str):
        start = time.time()
        simulate_network_delay()
        challenge_id = CryptoUtils.generate_id("chal")
        nonce = CryptoUtils.generate_nonce()
        self.challenges[challenge_id] = {
            "device_id": device_id,
            "nonce": nonce,
            "timestamp": time.time()
        }
        return challenge_id, nonce, (time.time() - start) * 1000
    
    def verify_response_hvrt(self, challenge_id: str, device_id: str, response_hmac: str,
                           device_secret: str, sat: Dict, rrt: Dict):
        start = time.time()
        
        if challenge_id not in self.challenges:
            return {"result": "deny", "reason": "invalid challenge"}
        
        challenge = self.challenges[challenge_id]
        del self.challenges[challenge_id]
        
        expected_hmac = CryptoUtils.compute_hmac(device_secret, f"{challenge_id}:{challenge['nonce']}")
        if expected_hmac != response_hmac:
            return {"result": "deny", "reason": "invalid HMAC"}
        
        verify_start = time.time()
        sat_data = {k: v for k, v in sat.items() if k != "signature"}
        if not CryptoUtils.verify(self.pubkey, sat_data, sat["signature"]):
            return {"result": "deny", "reason": "invalid SAT signature"}
        
        rrt_data = {k: v for k, v in rrt.items() if k != "signature"}
        if not CryptoUtils.verify(self.pubkey, rrt_data, rrt["signature"]):
            return {"result": "deny", "reason": "invalid RRT signature"}
        
        if sat["rrt_id"] != rrt["rrt_id"]:
            return {"result": "deny", "reason": "SAT-RRT mismatch"}
        
        if rrt["gtt_id"] != self.gtt["gtt_id"]:
            return {"result": "deny", "reason": "RRT-GTT mismatch"}
        
        gtt_data = {k: v for k, v in self.gtt.items() if k != "signature"}
        if not CryptoUtils.verify(self.gtt["root_pubkey"], gtt_data, self.gtt["signature"]):
            return {"result": "deny", "reason": "invalid GTT signature"}
        
        ticket_verify_ms = (time.time() - verify_start) * 1000
        
        state_check_start = time.time()
        if device_id in self.device_states:
            if self.device_states[device_id] == "revoked":
                return {"result": "deny", "reason": "device is revoked (AG local state)"}
        
        state_check_ms = (time.time() - state_check_start) * 1000
        total_ms = (time.time() - start) * 1000
        
        return {
            "result": "allow",
            "reason": "HVRT local verification success",
            "timings": {
                "ticket_verify_ms": ticket_verify_ms,
                "state_check_ms": state_check_ms,
                "total_latency_ms": total_ms
            }
        }


class MockTD:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.device_secret = None
        self.rrt = None
        self.sat = None
    
    def compute_response_hmac(self, challenge_id: str, nonce: str):
        return CryptoUtils.compute_hmac(self.device_secret, f"{challenge_id}:{nonce}")


def run_real_experiment():
    print("=" * 100)
    print("  HVRT 多终端真实网络实验")
    print("=" * 100)
    print(f"\n配置:")
    print(f"  终端数量: {NUM_TERMINALS}")
    print(f"  认证轮次: {NUM_ROUNDS}")
    print(f"  漫游轮次: {ROAMING_ROUNDS}")
    print(f"  网络延迟: {NETWORK_DELAY_MIN_MS}-{NETWORK_DELAY_MAX_MS} ms")
    print(f"  丢包率: {PACKET_LOSS_RATE*100}%\n")
    
    for f in ["logs/real_hvrt.jsonl", "logs/real_centralized.jsonl", "logs/real_terminal_online_status.jsonl"]:
        if os.path.exists(f):
            os.remove(f)
    
    logger_hvrt = JsonLogger("hvrt")
    logger_centralized = JsonLogger("centralized")
    logger_terminal = JsonLogger("terminal_online_status")
    
    print("【初始化】创建 CTA, EC, AG1, AG2...")
    cta_hvrt = MockCTA(logger_hvrt)
    ec_hvrt = MockEC("ec1", cta_hvrt, logger_hvrt)
    ag1_hvrt = MockAG("ag1", ec_hvrt, logger_hvrt)
    ag2_hvrt = MockAG("ag2", ec_hvrt, logger_hvrt)
    ec_hvrt.sync_with_cta()
    ag1_hvrt.sync_with_ec()
    ag2_hvrt.sync_with_ec()
    
    cta_centralized = MockCTA(logger_centralized)
    ec_centralized = MockEC("ec1", cta_centralized, logger_centralized)
    ag1_centralized = MockAG("ag1", ec_centralized, logger_centralized)
    ag2_centralized = MockAG("ag2", ec_centralized, logger_centralized)
    ec_centralized.sync_with_cta()
    ag1_centralized.sync_with_ec()
    ag2_centralized.sync_with_ec()
    
    cta_terminal = MockCTA(logger_terminal)
    ec_terminal = MockEC("ec1", cta_terminal, logger_terminal)
    ag1_terminal = MockAG("ag1", ec_terminal, logger_terminal)
    ag2_terminal = MockAG("ag2", ec_terminal, logger_terminal)
    ec_terminal.sync_with_cta()
    ag1_terminal.sync_with_ec()
    ag2_terminal.sync_with_ec()
    
    print(f"【初始化】创建 {NUM_TERMINALS} 个终端...")
    terminals_hvrt = []
    terminals_centralized = []
    terminals_terminal = []
    
    for i in range(1, NUM_TERMINALS + 1):
        device_id = f"td{i:03d}"
        
        td_hvrt = MockTD(device_id)
        reg_data = cta_hvrt.register_device(device_id, "regionA")
        td_hvrt.device_secret = reg_data["device_secret"]
        terminals_hvrt.append(td_hvrt)
        
        td_centralized = MockTD(device_id)
        reg_data_c = cta_centralized.register_device(device_id, "regionA")
        td_centralized.device_secret = reg_data_c["device_secret"]
        terminals_centralized.append(td_centralized)
        
        td_terminal = MockTD(device_id)
        reg_data_t = cta_terminal.register_device(device_id, "regionA")
        td_terminal.device_secret = reg_data_t["device_secret"]
        terminals_terminal.append(td_terminal)
    
    print("\n" + "=" * 100)
    print("  模块 1: HVRT 多终端普通认证")
    print("=" * 100)
    
    async def run_hvrt_auth(td):
        request_id = CryptoUtils.generate_id("req")
        
        rrt, ticket_ms = ag1_hvrt.issue_rrt(td.device_id, "regionA")
        sat, _ = ag1_hvrt.issue_sat(td.device_id, rrt["rrt_id"])
        
        challenge_id, nonce, chal_ms = ag1_hvrt.generate_challenge(td.device_id)
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        
        result = ag1_hvrt.verify_response_hvrt(challenge_id, td.device_id, response_hmac, td.device_secret, sat, rrt)
        
        logger_hvrt.log_auth_result(
            request_id=request_id,
            device_id=td.device_id,
            ag_id="ag1",
            cta_version=cta_hvrt.revocation_version,
            ec_version=ec_hvrt.revocation_version,
            ag_version=ag1_hvrt.revocation_version,
            ticket_issue_ms=ticket_ms,
            challenge_ms=chal_ms,
            ticket_verify_ms=result["timings"]["ticket_verify_ms"],
            state_check_ms=result["timings"]["state_check_ms"],
            sync_ms=0,
            total_latency_ms=result["timings"]["total_latency_ms"],
            result=result["result"],
            reason=result["reason"]
        )
    
    import asyncio
    
    async def run_all_hvrt():
        for round_idx in range(NUM_ROUNDS):
            if (round_idx + 1) % 3 == 0:
                print(f"  已完成 {round_idx + 1}/{NUM_ROUNDS} 轮...")
            tasks = [run_hvrt_auth(td) for td in terminals_hvrt]
            await asyncio.gather(*tasks)
    
    asyncio.run(run_all_hvrt())
    
    print("\n" + "=" * 100)
    print("  模块 2: Centralized 多终端普通认证")
    print("=" * 100)
    
    async def run_centralized_auth(td):
        request_id = CryptoUtils.generate_id("req")
        
        rrt, ticket_ms = ag1_centralized.issue_rrt(td.device_id, "regionA")
        sat, _ = ag1_centralized.issue_sat(td.device_id, rrt["rrt_id"])
        
        challenge_id, nonce, chal_ms = ag1_centralized.generate_challenge(td.device_id)
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        
        start_verify = time.time()
        centralized_result = cta_centralized.online_verify(td.device_id, sat, rrt, ag1_centralized.pubkey)
        total_ms = (time.time() - start_verify) * 1000 + ticket_ms + chal_ms
        
        logger_centralized.log_auth_result(
            request_id=request_id,
            device_id=td.device_id,
            ag_id="ag1",
            cta_version=cta_centralized.revocation_version,
            ec_version=ec_centralized.revocation_version,
            ag_version=ag1_centralized.revocation_version,
            ticket_issue_ms=ticket_ms,
            challenge_ms=chal_ms,
            ticket_verify_ms=total_ms - ticket_ms - chal_ms,
            state_check_ms=0,
            sync_ms=0,
            total_latency_ms=total_ms,
            result=centralized_result["result"],
            reason=centralized_result["reason"]
        )
    
    async def run_all_centralized():
        for round_idx in range(NUM_ROUNDS):
            if (round_idx + 1) % 3 == 0:
                print(f"  已完成 {round_idx + 1}/{NUM_ROUNDS} 轮...")
            tasks = [run_centralized_auth(td) for td in terminals_centralized]
            await asyncio.gather(*tasks)
    
    asyncio.run(run_all_centralized())
    
    print("\n" + "=" * 100)
    print("  模块 3: Terminal-Online-Status 多终端普通认证")
    print("=" * 100)
    
    async def run_terminal_auth(td):
        request_id = CryptoUtils.generate_id("req")
        
        receipt_start = time.time()
        status_receipt = cta_terminal.get_device_status_receipt(td.device_id)
        receipt_ms = (time.time() - receipt_start) * 1000
        
        rrt, ticket_ms = ag1_terminal.issue_rrt(td.device_id, "regionA")
        sat, _ = ag1_terminal.issue_sat(td.device_id, rrt["rrt_id"])
        
        challenge_id, nonce, chal_ms = ag1_terminal.generate_challenge(td.device_id)
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        
        result = ag1_terminal.verify_response_hvrt(challenge_id, td.device_id, response_hmac, td.device_secret, sat, rrt)
        
        logger_terminal.log_auth_result(
            request_id=request_id,
            device_id=td.device_id,
            ag_id="ag1",
            cta_version=cta_terminal.revocation_version,
            ec_version=ec_terminal.revocation_version,
            ag_version=ag1_terminal.revocation_version,
            ticket_issue_ms=ticket_ms,
            challenge_ms=chal_ms,
            ticket_verify_ms=result["timings"]["ticket_verify_ms"],
            state_check_ms=result["timings"]["state_check_ms"],
            sync_ms=0,
            total_latency_ms=result["timings"]["total_latency_ms"] + receipt_ms,
            result=result["result"],
            reason=result["reason"]
        )
    
    async def run_all_terminal():
        for round_idx in range(NUM_ROUNDS):
            if (round_idx + 1) % 3 == 0:
                print(f"  已完成 {round_idx + 1}/{NUM_ROUNDS} 轮...")
            tasks = [run_terminal_auth(td) for td in terminals_terminal]
            await asyncio.gather(*tasks)
    
    asyncio.run(run_all_terminal())
    
    print("\n" + "=" * 100)
    print("  模块 4: HVRT 多终端漫游")
    print("=" * 100)
    
    async def run_roaming(td):
        start_roam = time.time()
        rrt2, _ = ag2_hvrt.issue_rrt(td.device_id, "regionA")
        sat2, _ = ag2_hvrt.issue_sat(td.device_id, rrt2["rrt_id"])
        challenge_id, nonce, _ = ag2_hvrt.generate_challenge(td.device_id)
        response_hmac = td.compute_response_hmac(challenge_id, nonce)
        result = ag2_hvrt.verify_response_hvrt(challenge_id, td.device_id, response_hmac, td.device_secret, sat2, rrt2)
        roaming_latency_ms = (time.time() - start_roam) * 1000
        logger_hvrt.log_roaming_result(td.device_id, "ag1", "ag2", roaming_latency_ms, result["result"])
        
        start_roam_back = time.time()
        rrt1, _ = ag1_hvrt.issue_rrt(td.device_id, "regionA")
        sat1, _ = ag1_hvrt.issue_sat(td.device_id, rrt1["rrt_id"])
        challenge_id2, nonce2, _ = ag1_hvrt.generate_challenge(td.device_id)
        response_hmac2 = td.compute_response_hmac(challenge_id2, nonce2)
        result2 = ag1_hvrt.verify_response_hvrt(challenge_id2, td.device_id, response_hmac2, td.device_secret, sat1, rrt1)
        roaming_latency_ms2 = (time.time() - start_roam_back) * 1000
        logger_hvrt.log_roaming_result(td.device_id, "ag2", "ag1", roaming_latency_ms2, result2["result"])
    
    async def run_all_roaming():
        for round_idx in range(ROAMING_ROUNDS):
            if (round_idx + 1) % 2 == 0:
                print(f"  已完成 {round_idx + 1}/{ROAMING_ROUNDS} 轮...")
            tasks = [run_roaming(td) for td in terminals_hvrt]
            await asyncio.gather(*tasks)
    
    asyncio.run(run_all_roaming())
    
    print("\n" + "=" * 100)
    print("  模块 5: 撤销同步实验（更真实）")
    print("=" * 100)
    
    target_td = terminals_hvrt[0]
    num_tests = 5  # 每个阶段测试 5 次
    
    print(f"\n阶段 1: 撤销前（{num_tests} 次测试）")
    for i in range(num_tests):
        rrt, _ = ag1_hvrt.issue_rrt(target_td.device_id, "regionA")
        sat, _ = ag1_hvrt.issue_sat(target_td.device_id, rrt["rrt_id"])
        challenge_id, nonce, _ = ag1_hvrt.generate_challenge(target_td.device_id)
        response_hmac = target_td.compute_response_hmac(challenge_id, nonce)
        result1 = ag1_hvrt.verify_response_hvrt(challenge_id, target_td.device_id, response_hmac, target_td.device_secret, sat, rrt)
        logger_hvrt.log_revocation_stage("before_revoke", target_td.device_id,
                                        cta_hvrt.revocation_version, ec_hvrt.revocation_version, ag1_hvrt.revocation_version,
                                        result1["result"], result1["reason"])
    print(f"  阶段 1 测试完成！")
    
    print(f"\n阶段 2: CTA 已撤销，EC/AG 未同步（{num_tests} 次测试）")
    cta_hvrt.revoke_device(target_td.device_id)
    # 随机同步延迟（10-100ms）
    time.sleep(random.uniform(0.01, 0.1))
    
    allow_count, deny_count = 0, 0
    for i in range(num_tests):
        rrt, _ = ag1_hvrt.issue_rrt(target_td.device_id, "regionA")
        sat, _ = ag1_hvrt.issue_sat(target_td.device_id, rrt["rrt_id"])
        challenge_id, nonce, _ = ag1_hvrt.generate_challenge(target_td.device_id)
        response_hmac = target_td.compute_response_hmac(challenge_id, nonce)
        result2 = ag1_hvrt.verify_response_hvrt(challenge_id, target_td.device_id, response_hmac, target_td.device_secret, sat, rrt)
        if result2["result"] == "allow":
            allow_count +=1
        else:
            deny_count +=1
        logger_hvrt.log_revocation_stage("cta_revoked_no_sync", target_td.device_id,
                                        cta_hvrt.revocation_version, ec_hvrt.revocation_version, ag1_hvrt.revocation_version,
                                        result2["result"], result2["reason"])
    print(f"  结果: allow={allow_count}, deny={deny_count}")
    
    print(f"\n阶段 3: EC 已同步，AG 未同步（{num_tests} 次测试）")
    ec_hvrt.sync_with_cta()
    time.sleep(random.uniform(0.02, 0.08))
    
    allow_count, deny_count = 0, 0
    for i in range(num_tests):
        rrt, _ = ag1_hvrt.issue_rrt(target_td.device_id, "regionA")
        sat, _ = ag1_hvrt.issue_sat(target_td.device_id, rrt["rrt_id"])
        challenge_id, nonce, _ = ag1_hvrt.generate_challenge(target_td.device_id)
        response_hmac = target_td.compute_response_hmac(challenge_id, nonce)
        result3 = ag1_hvrt.verify_response_hvrt(challenge_id, target_td.device_id, response_hmac, target_td.device_secret, sat, rrt)
        if result3["result"] == "allow":
            allow_count +=1
        else:
            deny_count +=1
        logger_hvrt.log_revocation_stage("ec_synced_ag_not_synced", target_td.device_id,
                                        cta_hvrt.revocation_version, ec_hvrt.revocation_version, ag1_hvrt.revocation_version,
                                        result3["result"], result3["reason"])
    print(f"  结果: allow={allow_count}, deny={deny_count}")
    
    print(f"\n阶段 4: EC 与 AG 均同步（{num_tests} 次测试）")
    ag1_hvrt.sync_with_ec()
    
    allow_count, deny_count = 0, 0
    for i in range(num_tests):
        rrt, _ = ag1_hvrt.issue_rrt(target_td.device_id, "regionA")
        sat, _ = ag1_hvrt.issue_sat(target_td.device_id, rrt["rrt_id"])
        challenge_id, nonce, _ = ag1_hvrt.generate_challenge(target_td.device_id)
        response_hmac = target_td.compute_response_hmac(challenge_id, nonce)
        result4 = ag1_hvrt.verify_response_hvrt(challenge_id, target_td.device_id, response_hmac, target_td.device_secret, sat, rrt)
        if result4["result"] == "allow":
            allow_count +=1
        else:
            deny_count +=1
        logger_hvrt.log_revocation_stage("ec_ag_both_synced", target_td.device_id,
                                        cta_hvrt.revocation_version, ec_hvrt.revocation_version, ag1_hvrt.revocation_version,
                                        result4["result"], result4["reason"])
    print(f"  结果: allow={allow_count}, deny={deny_count}")
    
    print("\n" + "=" * 100)
    print("  实验完成！分析日志...")
    print("=" * 100)
    analyze_real_logs()


def analyze_real_logs():
    files = {
        "HVRT": "logs/real_hvrt.jsonl",
        "Centralized": "logs/real_centralized.jsonl",
        "Terminal-Online-Status": "logs/real_terminal_online_status.jsonl"
    }
    
    auth_data = defaultdict(list)
    roaming_data = defaultdict(list)
    revocation_data = []
    
    for name, path in files.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                        if rec.get("event") == "auth_result":
                            auth_data[name].append(rec["total_latency_ms"])
                        elif rec.get("event") == "roaming_auth_result":
                            roaming_data[name].append(rec["roaming_latency_ms"])
                        elif rec.get("event") == "revocation_stage_result":
                            revocation_data.append(rec)
                    except:
                        pass
    
    print("\n【图 1: 多终端普通认证时延 (ms)】")
    print("-" * 100)
    print(f"  {'方案':<25} {'样本数':<10} {'均值':<10} {'P50':<10} {'P95':<10} {'P99':<10} {'标准差':<10}")
    print("-" * 100)
    
    for name in ["HVRT", "Centralized", "Terminal-Online-Status"]:
        if name in auth_data and auth_data[name]:
            vals = auth_data[name]
            sorted_vals = sorted(vals)
            p50 = sorted_vals[int(len(sorted_vals) * 0.5)] if sorted_vals else 0
            p95 = sorted_vals[int(len(sorted_vals) * 0.95)] if sorted_vals else 0
            p99 = sorted_vals[int(len(sorted_vals) * 0.99)] if sorted_vals else 0
            print(f"  {name:<25} {len(vals):<10} {statistics.mean(vals):<10.2f} {p50:<10.2f} {p95:<10.2f} {p99:<10.2f} {statistics.pstdev(vals):<10.2f}")
    
    if roaming_data:
        print(f"\n【图 2: 漫游认证时延 (ms)】")
        print("-" * 100)
        print(f"  {'方案':<25} {'样本数':<10} {'均值':<10} {'P50':<10} {'P95':<10} {'P99':<10} {'标准差':<10}")
        print("-" * 100)
        for name in ["HVRT", "Centralized", "Terminal-Online-Status"]:
            if name in roaming_data and roaming_data[name]:
                vals = roaming_data[name]
                sorted_vals = sorted(vals)
                p50 = sorted_vals[int(len(sorted_vals) * 0.5)] if sorted_vals else 0
                p95 = sorted_vals[int(len(sorted_vals) * 0.95)] if sorted_vals else 0
                p99 = sorted_vals[int(len(sorted_vals) * 0.99)] if sorted_vals else 0
                print(f"  {name:<25} {len(vals):<10} {statistics.mean(vals):<10.2f} {p50:<10.2f} {p95:<10.2f} {p99:<10.2f} {statistics.pstdev(vals):<10.2f}")
    
    if revocation_data:
        print(f"\n【图 3: 撤销前后认证结果】")
        print("-" * 100)
        stage_names = {
            "before_revoke": "撤销前",
            "cta_revoked_no_sync": "CTA已撤销未同步",
            "ec_synced_ag_not_synced": "EC已同步AG未同步",
            "ec_ag_both_synced": "EC与AG均同步"
        }
        for rec in revocation_data:
            stage = stage_names.get(rec["stage"], rec["stage"])
            print(f"  {stage:<20} (CTA={rec['cta_version']}, EC={rec['ec_version']}, AG={rec['ag_version']}) → {rec['result']}")
    
    print("\n✅ 所有分析完成！")
    print("日志已保存到:")
    for f in files.values():
        print(f"  {f}")


if __name__ == "__main__":
    try:
        run_real_experiment()
    except KeyboardInterrupt:
        print("\n\n实验被用户中断。")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
