# from pathlib import Path
# from common import SimpleDB
# from typing import Dict
#
#
# class ECStorage:
#     def __init__(self, data_dir: str = "ec/data"):
#         self.db = SimpleDB(data_dir)
#         self._initialize()
#
#     def _initialize(self):
#         if not self.db.get("meta", "revocation_version"):
#             self.db.set("meta", "revocation_version", 0)
#         if not self.db.load("device_states"):
#             self.db.save("device_states", {})
#         if not self.db.load("ag_whitelist"):
#             self.db.save("ag_whitelist", ["ag1", "ag2"])
#
#     def save_gtt(self, gtt_data: Dict):
#         self.db.set("meta", "current_gtt", gtt_data)
#
#     def get_gtt(self) -> Dict:
#         return self.db.get("meta", "current_gtt")
#
#     def get_revocation_version(self) -> int:
#         return self.db.get("meta", "revocation_version") or 0
#
#     def set_revocation_version(self, version: int):
#         self.db.set("meta", "revocation_version", version)
#
#     def save_device_states(self, states: Dict[str, str]):
#         self.db.save("device_states", states)
#
#     def get_device_states(self) -> Dict[str, str]:
#         return self.db.load("device_states")


from common import SimpleDB, generate_ed25519_keypair
from typing import Dict, List


class ECStorage:
    def __init__(self, data_dir: str = "ec/data"):
        self.db = SimpleDB(data_dir)
        self._initialize()

    def _initialize(self):
        if not self.db.get("meta", "revocation_version"):
            self.db.set("meta", "revocation_version", 0)
        if not self.db.load("device_states"):
            self.db.save("device_states", {})
        if not self.db.load("device_secrets"):
            self.db.save("device_secrets", {})
        if not self.db.load("ag_whitelist"):
            self.db.save("ag_whitelist", ["ag1", "ag2"])
        if not self.db.load("revocation_events"):
            self.db.save("revocation_events", [])
        if not self.db.get("meta", "ec_privkey"):
            privkey, pubkey = generate_ed25519_keypair()
            self.db.set("meta", "ec_privkey", privkey)
            self.db.set("meta", "ec_pubkey", pubkey)

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

    def add_revocation_events(self, events: List[Dict]):
        current = self.db.load("revocation_events")
        known = {e["event_id"] for e in current}
        for event in events:
            if event["event_id"] not in known:
                current.append(event)
        current.sort(key=lambda e: e["version"])
        self.db.save("revocation_events", current)

    def get_revocation_events_from(self, from_version: int) -> List[Dict]:
        events = self.db.load("revocation_events")
        return [e for e in events if e["version"] > from_version]
    
    def save_device_secret(self, device_id: str, device_secret: str):
        device_secrets = self.db.load("device_secrets")
        device_secrets[device_id] = device_secret
        self.db.save("device_secrets", device_secrets)
    
    def get_device_secret(self, device_id: str) -> str:
        device_secrets = self.db.load("device_secrets")
        return device_secrets.get(device_id)
    
    def get_ec_privkey(self) -> str:
        return self.db.get("meta", "ec_privkey")
    
    def get_ec_pubkey(self) -> str:
        return self.db.get("meta", "ec_pubkey")
