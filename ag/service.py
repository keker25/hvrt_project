from datetime import datetime
import httpx
from common import (
    generate_ed25519_keypair,
    generate_nonce,
    generate_id,
    create_rrt,
    create_sat,
    verify_gtt,
    verify_rrt,
    verify_sat,
    verify_hmac_sha256,
    verify_with_ed25519,
    get_logger,
    Config,
)
from .storage import AGStorage

logger = get_logger("ag_service")


class AGService:
    def __init__(self):
        self.storage = AGStorage()
        self.region_id = "regionA"
        self.ag_id = self.storage.get_gateway_id() or "ag_default"
        self._initialize_keys()

    def _initialize_keys(self):
        if not self.storage.get_ag_privkey():
            logger.info("Generating new AG keypair")
            privkey, pubkey = generate_ed25519_keypair()
            self.storage.set_keypair(privkey, pubkey)

    async def sync_with_ec(self):
        from .sync_worker import AGSyncWorker
        worker = AGSyncWorker(self.storage)
        await worker.sync_with_ec()

    async def issue_rrt(self, device_id: str, region_id: str, ec_url: str = None):
        if ec_url is None:
            ec_url = Config.EC_URL
        
        gtt = self.storage.get_gtt()
        if not gtt:
            raise ValueError("GTT not available")
        
        device_states = self.storage.get_device_states()
        if device_id not in device_states:
            raise ValueError(f"Device {device_id} not registered")
        if device_states[device_id] != "active":
            raise ValueError(f"Device {device_id} is {device_states[device_id]}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{ec_url}/ec/rrt/issue",
                json={"device_id": device_id, "region_id": region_id}
            )
            response.raise_for_status()
            result = response.json()
        
        rrt_data = result["rrt"]
        self.storage.save_rrt(rrt_data["rrt_id"], rrt_data)
        logger.info(f"Issued RRT for device {device_id}: {rrt_data['rrt_id']}, status_version: {rrt_data['status_version']}")
        return {"rrt": rrt_data}

    def issue_sat(self, device_id: str, rrt_id: str):
        rrt = self.storage.get_rrt(rrt_id)
        if not rrt:
            raise ValueError("RRT not found")

        sat = create_sat(
            self.storage.get_ag_privkey(),
            device_id,
            rrt_id
        )
        self.storage.save_sat(sat.sat_id, sat.model_dump())
        logger.info(f"Issued SAT for device {device_id}: {sat.sat_id}")
        return {"sat": sat.model_dump()}

    def create_access_challenge(self, request_id: str, device_id: str, sat: dict, rrt: dict, status_receipt=None):
        nonce = generate_nonce()
        challenge_id = generate_id("chl")
        timestamp = datetime.utcnow().isoformat() + "Z"

        challenge = {
            "request_id": request_id,
            "device_id": device_id,
            "nonce": nonce,
            "sat": sat,
            "rrt": rrt,
            "timestamp": timestamp,
            "status_receipt": status_receipt
        }
        self.storage.save_challenge(challenge_id, challenge)

        return {
            "request_id": request_id,
            "challenge_id": challenge_id,
            "nonce": nonce,
            "timestamp": timestamp
        }

    async def verify_access_response(self, request_id: str, challenge_id: str, device_id: str, response_hmac: str, mode: str = "default"):
        challenge = self.storage.get_challenge(challenge_id)
        if not challenge:
            return {"result": "deny", "reason": "challenge not found"}
        if challenge["device_id"] != device_id:
            return {"result": "deny", "reason": "device mismatch"}
        if challenge["request_id"] != request_id:
            return {"result": "deny", "reason": "request mismatch"}

        gtt = self.storage.get_gtt()
        if not gtt:
            return {"result": "deny", "reason": "GTT not available"}

        message = f"{challenge_id}:{challenge['nonce']}:{device_id}"
        device_secret = self.storage.get_device_secret(device_id)
        if not device_secret:
            return {"result": "deny", "reason": "device secret unavailable"}
        if not verify_hmac_sha256(device_secret, message, response_hmac):
            return {"result": "deny", "reason": "invalid HMAC"}

        if mode == "centralized":
            ec_pubkey = self.storage.get_ec_pubkey()
            if not ec_pubkey:
                return {"result": "deny", "reason": "EC public key not available - please sync first"}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{Config.CTA_URL}/cta/auth/online_verify",
                    json={
                        "device_id": device_id,
                        "sat": challenge["sat"],
                        "rrt": challenge["rrt"],
                        "ec_pubkey": ec_pubkey,
                        "ag_pubkey": self.storage.get_ag_pubkey()
                    }
                )
                cta_result = response.json()
                if cta_result["result"] == "allow":
                    session_id = generate_id("sess")
                    self.storage.delete_challenge(challenge_id)
                    return {
                        "request_id": request_id,
                        "result": "allow",
                        "reason": "verified by CTA",
                        "session_id": session_id
                    }
                return {"request_id": request_id, "result": "deny", "reason": cta_result["reason"]}

        gtt_obj = type("GTT", (object,), {**gtt, "model_dump": lambda self=None: dict(gtt)})()
        if not verify_gtt(gtt_obj, gtt["root_pubkey"]):
            return {"result": "deny", "reason": "GTT verification failed"}

        rrt_data = challenge["rrt"]
        rrt_obj = type("RRT", (object,), {**rrt_data, "model_dump": lambda self=None: dict(rrt_data)})()
        ec_pubkey = self.storage.get_ec_pubkey()
        if not ec_pubkey:
            return {"result": "deny", "reason": "EC public key not available - please sync first"}
        if not verify_rrt(rrt_obj, ec_pubkey, gtt["gtt_id"]):
            return {"result": "deny", "reason": "RRT verification failed"}
        
        local_revocation_version = self.storage.get_revocation_version()
        if rrt_data.get("status_version", 0) < local_revocation_version:
            return {"result": "deny", "reason": "RRT status version too old"}
        
        if rrt_data.get("access_scope") not in ["regionwide", self.region_id]:
            return {"result": "deny", "reason": "RRT access scope not allowed"}

        sat_data = challenge["sat"]
        sat_obj = type("SAT", (object,), {**sat_data, "model_dump": lambda self=None: dict(sat_data)})()
        if not verify_sat(sat_obj, self.storage.get_ag_pubkey(), rrt_data["rrt_id"], device_id):
            return {"result": "deny", "reason": "SAT verification failed"}
        
        if sat_data.get("gateway_scope") not in ["current", "any", self.ag_id]:
            return {"result": "deny", "reason": "SAT gateway scope not allowed"}

        if mode == "terminal_online_status":
            receipt = challenge.get("status_receipt")
            if not receipt:
                return {"result": "deny", "reason": "missing status receipt"}
            receipt_payload = dict(receipt)
            signature = receipt_payload.pop("signature", None)
            if not signature:
                return {"result": "deny", "reason": "invalid status receipt"}
            if receipt_payload.get("device_id") != device_id:
                return {"result": "deny", "reason": "status receipt device mismatch"}
            if not verify_with_ed25519(gtt["root_pubkey"], receipt_payload, signature):
                return {"result": "deny", "reason": "status receipt verification failed"}
            if receipt_payload.get("status") != "active":
                return {"result": "deny", "reason": f"device is {receipt_payload.get('status')}"}
            
            if receipt_payload.get("revocation_version", 0) < local_revocation_version:
                return {"result": "deny", "reason": "status receipt revocation version too old"}
            
            receipt_request_id = receipt_payload.get("request_id")
            if receipt_request_id and receipt_request_id != request_id:
                return {"result": "deny", "reason": "status receipt request id mismatch"}
            
            from datetime import datetime, timezone
            expire_at = receipt_payload.get("expire_at")
            if expire_at:
                expire_dt = datetime.fromisoformat(expire_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if now > expire_dt:
                    return {"result": "deny", "reason": "status receipt expired"}
        else:
            device_states = self.storage.get_device_states()
            if device_id not in device_states:
                return {"result": "deny", "reason": "device not registered"}
            if device_states[device_id] != "active":
                return {"result": "deny", "reason": f"device is {device_states[device_id]}"}

        session_id = generate_id("sess")
        self.storage.save_session(session_id, {
            "device_id": device_id,
            "started_at": datetime.utcnow().isoformat() + "Z"
        })
        self.storage.delete_challenge(challenge_id)

        return {
            "request_id": request_id,
            "result": "allow",
            "reason": "local verification success" if mode == "default" else mode,
            "session_id": session_id
        }

    def get_state_current(self):
        return {
            "region_id": self.region_id,
            "revocation_version": self.storage.get_revocation_version(),
            "device_states": self.storage.get_device_states(),
            "device_secrets": self.storage.db.ag_get_device_secrets(),
            "ec_pubkey": self.storage.get_ec_pubkey()
        }
