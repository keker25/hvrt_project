from pathlib import Path
from common import SimpleDB
from common.models import Device, GTT, RevocationEvent
from typing import List, Dict


class CTAStorage:
    def __init__(self, data_dir: str = "cta/data"):
        self.db = SimpleDB(data_dir)
        self._initialize()
    
    def _initialize(self):
        if not self.db.load("devices"):
            self.db.save("devices", {})
        if not self.db.load("revocation_events"):
            self.db.save("revocation_events", [])
        if not self.db.get("meta", "revocation_version"):
            self.db.set("meta", "revocation_version", 0)
    
    def save_device(self, device: Device):
        devices = self.db.load("devices")
        devices[device.device_id] = device.dict()
        self.db.save("devices", devices)
    
    def get_device(self, device_id: str) -> Dict:
        return self.db.get("devices", device_id)
    
    def get_all_devices(self) -> Dict:
        return self.db.load("devices")
    
    def update_device_status(self, device_id: str, status: str):
        devices = self.db.load("devices")
        if device_id in devices:
            devices[device_id]["status"] = status
            self.db.save("devices", devices)
    
    def save_gtt(self, gtt: GTT):
        self.db.set("meta", "current_gtt", gtt.dict())
    
    def get_gtt(self) -> Dict:
        return self.db.get("meta", "current_gtt")
    
    def set_root_keypair(self, privkey: str, pubkey: str):
        self.db.set("meta", "root_privkey", privkey)
        self.db.set("meta", "root_pubkey", pubkey)
    
    def get_root_privkey(self) -> str:
        return self.db.get("meta", "root_privkey")
    
    def get_root_pubkey(self) -> str:
        return self.db.get("meta", "root_pubkey")
    
    def get_revocation_version(self) -> int:
        return self.db.get("meta", "revocation_version") or 0
    
    def set_revocation_version(self, version: int):
        self.db.set("meta", "revocation_version", version)
    
    def add_revocation_event(self, event: RevocationEvent):
        events = self.db.load("revocation_events")
        events.append(event.dict())
        self.db.save("revocation_events", events)
    
    def get_revocation_events_from(self, from_version: int) -> List[Dict]:
        events = self.db.load("revocation_events")
        return [e for e in events if e["version"] > from_version]
