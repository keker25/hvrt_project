from pathlib import Path
from common import SimpleDB
from typing import Dict


class ECStorage:
    def __init__(self, data_dir: str = "ec/data"):
        self.db = SimpleDB(data_dir)
        self._initialize()
    
    def _initialize(self):
        if not self.db.get("meta", "revocation_version"):
            self.db.set("meta", "revocation_version", 0)
        if not self.db.load("device_states"):
            self.db.save("device_states", {})
        if not self.db.load("ag_whitelist"):
            self.db.save("ag_whitelist", ["ag1", "ag2"])
    
    def save_gtt(self, gtt_data: Dict):
        self.db.set("meta", "current_gtt", gtt_data)
    
    def get_gtt(self) -> Dict:
        return self.db.get("meta", "current_gtt")
    
    def get_revocation_version(self) -> int:
        return self.db.get("meta", "revocation_version") or 0
    
    def set_revocation_version(self, version: int):
        self.db.set("meta", "revocation_version", version)
    
    def save_device_states(self, states: Dict[str, str]):
        self.db.save("device_states", states)
    
    def get_device_states(self) -> Dict[str, str]:
        return self.db.load("device_states")
