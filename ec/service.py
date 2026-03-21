# from common import get_logger
# from .storage import ECStorage
#
# logger = get_logger("ec_service")
#
#
# class ECService:
#     def __init__(self):
#         self.storage = ECStorage()
#         self.region_id = "regionA"
#
#     def get_state_current(self):
#         return {
#             "region_id": self.region_id,
#             "revocation_version": self.storage.get_revocation_version(),
#             "device_states": self.storage.get_device_states()
#         }
#
#     def get_state_delta(self, from_version: int):
#         all_events = []
#         current_version = self.storage.get_revocation_version()
#
#         return {
#             "from_version": from_version,
#             "to_version": current_version,
#             "changes": []
#         }
#
#     def get_gtt_summary(self):
#         gtt = self.storage.get_gtt()
#         if not gtt:
#             raise ValueError("GTT not available")
#
#         return {
#             "gtt_id": gtt["gtt_id"],
#             "root_pubkey": gtt["root_pubkey"],
#             "policy_version": gtt["policy_version"],
#             "revocation_version": gtt["revocation_version"]
#         }

from common import get_logger, create_rrt
from .storage import ECStorage

logger = get_logger("ec_service")


class ECService:
    def __init__(self):
        self.storage = ECStorage()
        self.region_id = "regionA"

    def get_state_current(self):
        return {
            "region_id": self.region_id,
            "revocation_version": self.storage.get_revocation_version(),
            "device_states": self.storage.get_device_states(),
            "device_secrets": self.storage.db.load("device_secrets") or {},
            "ec_pubkey": self.storage.get_ec_pubkey()
        }

    def get_state_delta(self, from_version: int):
        current_version = self.storage.get_revocation_version()
        return {
            "from_version": from_version,
            "to_version": current_version,
            "changes": self.storage.get_revocation_events_from(from_version)
        }

    def get_gtt_current(self):
        gtt = self.storage.get_gtt()
        if not gtt:
            raise ValueError("GTT not available")
        return gtt
    
    def issue_rrt(self, device_id: str, region_id: str):
        gtt = self.storage.get_gtt()
        if not gtt:
            raise ValueError("GTT not available")
        
        device_states = self.storage.get_device_states()
        if device_id not in device_states:
            raise ValueError(f"Device {device_id} not registered")
        if device_states[device_id] != "active":
            raise ValueError(f"Device {device_id} is {device_states[device_id]}")

        status_version = self.storage.get_revocation_version()
        rrt = create_rrt(
            self.storage.get_ec_privkey(),
            device_id,
            region_id,
            gtt["gtt_id"],
            status_version
        )
        logger.info(f"Issued RRT for device {device_id}: {rrt.rrt_id}, status_version: {status_version}")
        return {"rrt": rrt.model_dump()}
