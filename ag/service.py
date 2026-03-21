# from datetime import datetime
# import httpx
# from common import (
#     generate_ed25519_keypair,
#     generate_nonce,
#     generate_id,
#     create_rrt,
#     create_sat,
#     verify_gtt,
#     verify_rrt,
#     verify_sat,
#     verify_hmac_sha256,
#     generate_hmac_sha256,
#     get_logger,
#     Config,
# )
# from .storage import AGStorage
#
# logger = get_logger("ag_service")
#
#
# class AGService:
#     def __init__(self):
#         self.storage = AGStorage()
#         self.region_id = "regionA"
#         self._initialize_keys()
#
#     def _initialize_keys(self):
#         if not self.storage.get_ag_privkey():
#             logger.info("Generating new AG keypair")
#             privkey, pubkey = generate_ed25519_keypair()
#             self.storage.set_keypair(privkey, pubkey)
#
#     async def sync_with_ec(self):
#         from .sync_worker import AGSyncWorker
#         worker = AGSyncWorker(self.storage)
#         await worker.sync_with_ec()
#
#     def issue_rrt(self, device_id: str, region_id: str):
#         gtt = self.storage.get_gtt()
#         if not gtt:
#             raise ValueError("GTT not available")
#
#         rrt = create_rrt(
#             self.storage.get_ag_privkey(),
#             device_id,
#             region_id,
#             gtt["gtt_id"]
#         )
#         self.storage.save_rrt(rrt.rrt_id, rrt.dict())
#         logger.info(f"Issued RRT for device {device_id}: {rrt.rrt_id}")
#         return {"rrt": rrt.dict()}
#
#     def issue_sat(self, device_id: str, rrt_id: str):
#         rrt = self.storage.get_rrt(rrt_id)
#         if not rrt:
#             raise ValueError("RRT not found")
#
#         sat = create_sat(
#             self.storage.get_ag_privkey(),
#             device_id,
#             rrt_id
#         )
#         self.storage.save_sat(sat.sat_id, sat.dict())
#         logger.info(f"Issued SAT for device {device_id}: {sat.sat_id}")
#         return {"sat": sat.dict()}
#
#     def create_access_challenge(self, request_id: str, device_id: str, sat: dict, rrt: dict):
#         nonce = generate_nonce()
#         challenge_id = generate_id("chl")
#         timestamp = datetime.utcnow().isoformat() + "Z"
#
#         challenge = {
#             "request_id": request_id,
#             "device_id": device_id,
#             "nonce": nonce,
#             "sat": sat,
#             "rrt": rrt,
#             "timestamp": timestamp
#         }
#         self.storage.save_challenge(challenge_id, challenge)
#
#         return {
#             "request_id": request_id,
#             "challenge_id": challenge_id,
#             "nonce": nonce,
#             "timestamp": timestamp
#         }
#
#     async def verify_access_response(
#         self,
#         request_id: str,
#         challenge_id: str,
#         device_id: str,
#         response_hmac: str,
#         mode: str = "default"
#     ):
#         challenge = self.storage.get_challenge(challenge_id)
#         if not challenge:
#             return {"result": "deny", "reason": "challenge not found"}
#
#         if challenge["device_id"] != device_id:
#             return {"result": "deny", "reason": "device mismatch"}
#
#         if challenge["request_id"] != request_id:
#             return {"result": "deny", "reason": "request mismatch"}
#
#         gtt = self.storage.get_gtt()
#         if not gtt:
#             return {"result": "deny", "reason": "GTT not available"}
#
#         if mode == "centralized":
#             async with httpx.AsyncClient() as client:
#                 response = await client.post(
#                     f"{Config.CTA_URL}/cta/auth/online_verify",
#                     json={
#                         "device_id": device_id,
#                         "sat": challenge["sat"],
#                         "rrt": challenge["rrt"]
#                     }
#                 )
#                 cta_result = response.json()
#                 if cta_result["result"] == "allow":
#                     session_id = generate_id("sess")
#                     self.storage.delete_challenge(challenge_id)
#                     return {
#                         "request_id": request_id,
#                         "result": "allow",
#                         "reason": "verified by CTA",
#                         "session_id": session_id
#                     }
#                 return {
#                     "request_id": request_id,
#                     "result": "deny",
#                     "reason": cta_result["reason"]
#                 }
#
#         try:
#             device_secret = f"secret_{device_id}"
#             message = f"{challenge_id}:{challenge['nonce']}:{device_id}"
#             expected_hmac = generate_hmac_sha256(device_secret, message)
#
#             if not verify_hmac_sha256(device_secret, message, response_hmac):
#                 return {"result": "deny", "reason": "invalid HMAC"}
#         except Exception as e:
#             logger.warning(f"Could not verify HMAC with real secret: {e}")
#
#         gtt_obj = type('GTT', (object,), gtt)
#         if not verify_gtt(gtt_obj, gtt["root_pubkey"]):
#             return {"result": "deny", "reason": "GTT verification failed"}
#
#         rrt_data = challenge["rrt"]
#         rrt_obj = type('RRT', (object,), rrt_data)
#         if not verify_rrt(rrt_obj, self.storage.get_ag_pubkey(), gtt["gtt_id"]):
#             return {"result": "deny", "reason": "RRT verification failed"}
#
#         sat_data = challenge["sat"]
#         sat_obj = type('SAT', (object,), sat_data)
#         if not verify_sat(sat_obj, self.storage.get_ag_pubkey(), rrt_data["rrt_id"], device_id):
#             return {"result": "deny", "reason": "SAT verification failed"}
#
#         device_states = self.storage.get_device_states()
#         if device_id in device_states and device_states[device_id] != "active":
#             return {"result": "deny", "reason": f"device is {device_states[device_id]}"}
#
#         session_id = generate_id("sess")
#         self.storage.save_session(session_id, {
#             "device_id": device_id,
#             "started_at": datetime.utcnow().isoformat() + "Z"
#         })
#         self.storage.delete_challenge(challenge_id)
#
#         return {
#             "request_id": request_id,
#             "result": "allow",
#             "reason": "local verification success",
#             "session_id": session_id
#         }
#
#     def get_state_current(self):
#         return {
#             "region_id": self.region_id,
#             "revocation_version": self.storage.get_revocation_version(),
#             "device_states": self.storage.get_device_states()
#         }
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

    def issue_rrt(self, device_id: str, region_id: str):
        gtt = self.storage.get_gtt()
        if not gtt:
            raise ValueError("GTT not available")

        status_version = self.storage.get_revocation_version()
        rrt = create_rrt(
            self.storage.get_ag_privkey(),
            device_id,
            region_id,
            gtt["gtt_id"],
            status_version
        )
        self.storage.save_rrt(rrt.rrt_id, rrt.model_dump())
        logger.info(f"Issued RRT for device {device_id}: {rrt.rrt_id}, status_version: {status_version}")
        return {"rrt": rrt.model_dump()}

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
            device_secret = f"secret_{device_id}"
        if not verify_hmac_sha256(device_secret, message, response_hmac):
            return {"result": "deny", "reason": "invalid HMAC"}

        if mode == "centralized":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{Config.CTA_URL}/cta/auth/online_verify",
                    json={
                        "device_id": device_id,
                        "sat": challenge["sat"],
                        "rrt": challenge["rrt"],
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
        if not verify_rrt(rrt_obj, self.storage.get_ag_pubkey(), gtt["gtt_id"]):
            return {"result": "deny", "reason": "RRT verification failed"}

        sat_data = challenge["sat"]
        sat_obj = type("SAT", (object,), {**sat_data, "model_dump": lambda self=None: dict(sat_data)})()
        if not verify_sat(sat_obj, self.storage.get_ag_pubkey(), rrt_data["rrt_id"], device_id):
            return {"result": "deny", "reason": "SAT verification failed"}

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
        else:
            device_states = self.storage.get_device_states()
            if device_id in device_states and device_states[device_id] != "active":
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
            "device_states": self.storage.get_device_states()
        }
