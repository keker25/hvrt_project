from pathlib import Path
from common import SQLiteDB
from common.models import Device, GTT, RevocationEvent, DeltaEvent
from typing import List, Dict, Union


class CTAStorage:
    def __init__(self, db_path: str = "cta/data/cta.db"):
        self.db = SQLiteDB(db_path)
        self._initialize()
    
    def _initialize(self):
        if self.db.meta_get_int("revocation_version") == 0:
            self.db.meta_set_int("revocation_version", 0)
    
    def save_device(self, device: Device):
        self.db.cta_save_device(
            device.device_id,
            device.device_secret,
            device.region_id,
            device.status
        )
    
    def get_device(self, device_id: str) -> Dict:
        device_data = self.db.cta_get_device(device_id)
        if device_data:
            return {
                "device_id": device_data["device_id"],
                "device_secret": device_data["secret"],
                "region_id": device_data["region"],
                "status": device_data["status"]
            }
        return None
    
    def get_all_devices(self) -> Dict:
        devices = self.db.cta_get_all_devices()
        result = {}
        for device_id, device_data in devices.items():
            result[device_id] = {
                "device_id": device_data["device_id"],
                "device_secret": device_data["secret"],
                "region_id": device_data["region"],
                "status": device_data["status"]
            }
        return result
    
    def update_device_status(self, device_id: str, status: str):
        self.db.cta_update_device_status(device_id, status)
    
    def save_gtt(self, gtt: GTT):
        self.db.meta_set_json("current_gtt", gtt.dict())
    
    def get_gtt(self) -> Dict:
        return self.db.meta_get_json("current_gtt")
    
    def set_root_keypair(self, privkey: str, pubkey: str):
        self.db.meta_set("root_privkey", privkey)
        self.db.meta_set("root_pubkey", pubkey)
    
    def get_root_privkey(self) -> str:
        return self.db.meta_get("root_privkey")
    
    def get_root_pubkey(self) -> str:
        return self.db.meta_get("root_pubkey")
    
    def get_revocation_version(self) -> int:
        return self.db.meta_get_int("revocation_version", 0)
    
    def set_revocation_version(self, version: int):
        self.db.meta_set_int("revocation_version", version)
    
    def add_revocation_event(self, event: Union[RevocationEvent, DeltaEvent]):
        event_dict = event.dict()
        version = event_dict.get("version", self.get_revocation_version() + 1)
        self.db.cta_add_revocation_event(version, event_dict)
    
    def get_revocation_events_from(self, from_version: int) -> List[Dict]:
        return self.db.cta_get_revocation_events_from(from_version)
