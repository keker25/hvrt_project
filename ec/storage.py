from common import SQLiteDB, generate_ed25519_keypair, get_logger
from typing import Dict, List


class ECStorage:
    def __init__(self, db_path: str = "ec/data/ec.db"):
        self.db = SQLiteDB(db_path)
        self._initialize()

    def _initialize(self):
        if self.db.meta_get_int("revocation_version") == 0:
            self.db.meta_set_int("revocation_version", 0)
        
        # 初始化 AG 白名单
        if not self.db.ec_get_ag_whitelist():
            for ag_id in ["ag1", "ag2"]:
                self.db.ec_add_ag_to_whitelist(ag_id)
        
        if not self.db.meta_get("ec_privkey"):
            privkey, pubkey = generate_ed25519_keypair()
            self.db.meta_set("ec_privkey", privkey)
            self.db.meta_set("ec_pubkey", pubkey)

    def save_gtt(self, gtt_data: Dict):
        self.db.meta_set_json("current_gtt", gtt_data)

    def get_gtt(self) -> Dict:
        return self.db.meta_get_json("current_gtt")

    def get_revocation_version(self) -> int:
        return self.db.meta_get_int("revocation_version", 0)

    def set_revocation_version(self, version: int):
        self.db.meta_set_int("revocation_version", version)

    def save_device_states(self, states: Dict[str, str]):
        self.db.ec_save_device_states(states)

    def get_device_states(self) -> Dict[str, str]:
        return self.db.ec_get_device_states()

    def _event_key(self, event: Dict) -> str:
        if event.get("event_id"):
            return event["event_id"]
        return f"{event.get('type','unknown')}:{event.get('device_id','')}:{event.get('version','')}"

    def add_revocation_events(self, events: List[Dict]):
        try:
            current = self.db.ec_get_all_revocation_events()
            known = {self._event_key(e) for e in current}
            for event in events:
                key = self._event_key(event)
                if key not in known:
                    version = event.get("version", 0)
                    self.db.ec_add_revocation_event(version, event)
                    known.add(key)
        except Exception as e:
            logger = get_logger("ec_storage")
            logger.error(f"Failed to add revocation events: {e}")

    def get_revocation_events_from(self, from_version: int) -> List[Dict]:
        return self.db.ec_get_revocation_events_from(from_version)
    
    def save_device_secret(self, device_id: str, device_secret: str):
        self.db.ec_save_device_secret(device_id, device_secret)
    
    def get_device_secret(self, device_id: str) -> str:
        return self.db.ec_get_device_secret(device_id)
    
    def get_ec_privkey(self) -> str:
        return self.db.meta_get("ec_privkey")
    
    def get_ec_pubkey(self) -> str:
        return self.db.meta_get("ec_pubkey")
