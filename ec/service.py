from common import get_logger
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
            "device_states": self.storage.get_device_states()
        }
    
    def get_state_delta(self, from_version: int):
        all_events = []
        current_version = self.storage.get_revocation_version()
        
        return {
            "from_version": from_version,
            "to_version": current_version,
            "changes": []
        }
    
    def get_gtt_summary(self):
        gtt = self.storage.get_gtt()
        if not gtt:
            raise ValueError("GTT not available")
        
        return {
            "gtt_id": gtt["gtt_id"],
            "root_pubkey": gtt["root_pubkey"],
            "policy_version": gtt["policy_version"],
            "revocation_version": gtt["revocation_version"]
        }
