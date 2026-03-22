# import secrets
# from datetime import datetime
# from common import (
#     generate_ed25519_keypair,
#     create_gtt,
#     verify_gtt,
#     verify_rrt,
#     verify_sat,
#     create_revocation_event,
#     get_logger,
# )
# from common.models import Device, RevocationEvent
# from .storage import CTAStorage
#
# logger = get_logger("cta_service")
#
#
# class CTAService:
#     def __init__(self):
#         self.storage = CTAStorage()
#         self._initialize_keys()
#
#     def _initialize_keys(self):
#         if not self.storage.get_root_privkey():
#             logger.info("Generating new root keypair")
#             privkey, pubkey = generate_ed25519_keypair()
#             self.storage.set_root_keypair(privkey, pubkey)
#             self._generate_initial_gtt()
#
#     def _generate_initial_gtt(self):
#         privkey = self.storage.get_root_privkey()
#         pubkey = self.storage.get_root_pubkey()
#         gtt = create_gtt(privkey, pubkey, 1)
#         self.storage.save_gtt(gtt)
#         self.storage.set_revocation_version(1)
#         logger.info(f"Generated initial GTT: {gtt.gtt_id}")
#
#     def register_device(self, device_id: str, region_id: str) -> Device:
#         existing = self.storage.get_device(device_id)
#         if existing:
#             raise ValueError(f"Device {device_id} already exists")
#
#         device_secret = secrets.token_urlsafe(32)
#         device = Device(
#             device_id=device_id,
#             device_secret=device_secret,
#             status="active",
#             region_id=region_id,
#             created_at=datetime.utcnow().isoformat() + "Z"
#         )
#         self.storage.save_device(device)
#         logger.info(f"Registered device: {device_id} in region {region_id}")
#         return device
#
#     def get_current_gtt(self):
#         return self.storage.get_gtt()
#
#     def get_revocation_delta(self, from_version: int):
#         events = self.storage.get_revocation_events_from(from_version)
#         to_version = self.storage.get_revocation_version()
#         return {
#             "from_version": from_version,
#             "to_version": to_version,
#             "changes": events
#         }
#
#     def revoke_device(self, device_id: str, reason: str = None):
#         device = self.storage.get_device(device_id)
#         if not device:
#             raise ValueError(f"Device {device_id} not found")
#
#         if device["status"] == "revoked":
#             raise ValueError(f"Device {device_id} is already revoked")
#
#         new_version = self.storage.get_revocation_version() + 1
#         self.storage.update_device_status(device_id, "revoked")
#         self.storage.set_revocation_version(new_version)
#
#         event = create_revocation_event(device_id, "revoked", new_version)
#         self.storage.add_revocation_event(event)
#
#         logger.info(f"Revoked device: {device_id}, new version: {new_version}")
#
#         return {
#             "device_id": device_id,
#             "status": "revoked",
#             "new_version": new_version
#         }
#
#     def online_verify(self, device_id: str, sat: dict, rrt: dict):
#         device = self.storage.get_device(device_id)
#         if not device:
#             return {"result": "deny", "reason": "device not found"}
#
#         if device["status"] != "active":
#             return {
#                 "result": "deny",
#                 "reason": f"device is {device['status']}",
#                 "revocation_version": self.storage.get_revocation_version()
#             }
#
#         gtt_data = self.storage.get_gtt()
#         root_pubkey = self.storage.get_root_pubkey()
#
#         if not verify_gtt(type('GTT', (object,), gtt_data), root_pubkey):
#             return {"result": "deny", "reason": "GTT verification failed"}
#
#         return {
#             "result": "allow",
#             "reason": "verified by CTA",
#             "revocation_version": self.storage.get_revocation_version()
#         }


import secrets
from datetime import datetime, timezone, timedelta
from common import (
    generate_ed25519_keypair,
    create_gtt,
    verify_gtt,
    verify_rrt,
    verify_sat,
    create_revocation_event,
    sign_with_ed25519,
    get_logger,
    generate_id,
)
from common.models import Device, DeltaEvent
from .storage import CTAStorage

logger = get_logger("cta_service")


class CTAService:
    def __init__(self):
        self.storage = CTAStorage()
        self._initialize_keys()

    def _initialize_keys(self):
        if not self.storage.get_root_privkey():
            logger.info("Generating new root keypair")
            privkey, pubkey = generate_ed25519_keypair()
            self.storage.set_root_keypair(privkey, pubkey)
            self._generate_initial_gtt()

    def _generate_initial_gtt(self):
        privkey = self.storage.get_root_privkey()
        pubkey = self.storage.get_root_pubkey()
        gtt = create_gtt(privkey, pubkey, 1)
        self.storage.save_gtt(gtt)
        self.storage.set_revocation_version(1)
        logger.info(f"Generated initial GTT: {gtt.gtt_id}")

    def register_device(self, device_id: str, region_id: str) -> Device:
        existing = self.storage.get_device(device_id)
        if existing:
            if existing["status"] == "active":
                logger.info(f"Device {device_id} already exists and active")
                return Device(**existing)
            # 如果设备被撤销，重新激活
            device_secret = existing["device_secret"]
            existing["status"] = "active"
            existing["region_id"] = region_id
            existing["created_at"] = datetime.utcnow().isoformat() + "Z"
            device = Device(**existing)
            self.storage.save_device(device)
        else:
            device_secret = secrets.token_urlsafe(32)
            device = Device(
                device_id=device_id,
                device_secret=device_secret,
                status="active",
                region_id=region_id,
                created_at=datetime.utcnow().isoformat() + "Z"
            )
            self.storage.save_device(device)
        
        new_version = self.storage.get_revocation_version() + 1
        self.storage.set_revocation_version(new_version)
        
        registration_event = DeltaEvent(
            event_id=generate_id("evt"),
            version=new_version,
            type="device_register",
            device_id=device_id,
            status="active",
            region_id=region_id,
            device_secret=device_secret,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        self.storage.add_revocation_event(registration_event)
        
        logger.info(f"Registered device: {device_id} in region {region_id}, version: {new_version}")
        return device

    def get_current_gtt(self):
        return self.storage.get_gtt()

    def get_revocation_delta(self, from_version: int):
        events = self.storage.get_revocation_events_from(from_version)
        to_version = self.storage.get_revocation_version()
        return {
            "from_version": from_version,
            "to_version": to_version,
            "changes": events
        }

    def revoke_device(self, device_id: str, reason: str = None):
        device = self.storage.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        if device["status"] == "revoked":
            logger.info(f"Device {device_id} is already revoked")
            return {
                "device_id": device_id,
                "status": "revoked",
                "new_version": self.storage.get_revocation_version()
            }

        new_version = self.storage.get_revocation_version() + 1
        self.storage.update_device_status(device_id, "revoked")
        self.storage.set_revocation_version(new_version)

        revocation_event = DeltaEvent(
            event_id=generate_id("evt"),
            version=new_version,
            type="revoke",
            device_id=device_id,
            status="revoked",
            region_id=device.get("region_id"),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        self.storage.add_revocation_event(revocation_event)

        logger.info(f"Revoked device: {device_id}, new version: {new_version}")
        return {
            "device_id": device_id,
            "status": "revoked",
            "new_version": new_version
        }

    def online_verify(self, device_id: str, sat: dict, rrt: dict, ec_pubkey: str, ag_pubkey: str):
        device = self.storage.get_device(device_id)
        if not device:
            return {"result": "deny", "reason": "device not found"}

        if device["status"] != "active":
            return {
                "result": "deny",
                "reason": f"device is {device['status']}",
                "revocation_version": self.storage.get_revocation_version()
            }

        gtt_data = self.storage.get_gtt()
        root_pubkey = self.storage.get_root_pubkey()
        gtt_obj = type("GTT", (object,), {
            **gtt_data,
            "model_dump": lambda self=None: dict(gtt_data),
        })()

        if not verify_gtt(gtt_obj, root_pubkey):
            return {"result": "deny", "reason": "GTT verification failed"}

        rrt_obj = type("RRT", (object,), {
            **rrt,
            "model_dump": lambda self=None: dict(rrt),
        })()
        if not verify_rrt(rrt_obj, ec_pubkey, gtt_data["gtt_id"]):
            return {"result": "deny", "reason": "RRT verification failed"}

        sat_obj = type("SAT", (object,), {
            **sat,
            "model_dump": lambda self=None: dict(sat),
        })()
        if not verify_sat(sat_obj, ag_pubkey, rrt["rrt_id"], device_id):
            return {"result": "deny", "reason": "SAT verification failed"}

        return {
            "result": "allow",
            "reason": "verified by CTA",
            "revocation_version": self.storage.get_revocation_version()
        }

    def issue_status_receipt(self, device_id: str, request_id: str = None):
        device = self.storage.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        now = datetime.now(timezone.utc)
        expire_at = now + timedelta(minutes=5)
        
        receipt_data = {
            "device_id": device_id,
            "status": device["status"],
            "revocation_version": self.storage.get_revocation_version(),
            "issued_at": now.isoformat().replace("+00:00", "Z"),
            "expire_at": expire_at.isoformat().replace("+00:00", "Z")
        }
        if request_id:
            receipt_data["request_id"] = request_id
        signature = sign_with_ed25519(self.storage.get_root_privkey(), receipt_data)
        return {**receipt_data, "signature": signature}
