from pathlib import Path
from common import SQLiteDB
from typing import Dict


class AGStorage:
    def __init__(self, db_path: str = "ag/data/ag.db"):
        self.db = SQLiteDB(db_path)
        self._initialize()
    
    def _initialize(self):
        if self.db.meta_get_int("revocation_version") == 0:
            self.db.meta_set_int("revocation_version", 0)
        if not self.db.meta_get("gateway_id"):
            self.db.meta_set("gateway_id", "ag_001")
    
    def get_gateway_id(self) -> str:
        return self.db.meta_get("gateway_id")
    
    def save_gtt(self, gtt_data: Dict):
        self.db.meta_set_json("current_gtt", gtt_data)
    
    def get_gtt(self) -> Dict:
        return self.db.meta_get_json("current_gtt")
    
    def get_revocation_version(self) -> int:
        return self.db.meta_get_int("revocation_version", 0)
    
    def set_revocation_version(self, version: int):
        self.db.meta_set_int("revocation_version", version)
    
    def save_device_states(self, states: Dict[str, str]):
        self.db.ag_save_device_states(states)
    
    def get_device_states(self) -> Dict[str, str]:
        return self.db.ag_get_device_states()
    
    def save_rrt(self, rrt_id: str, rrt_data: Dict):
        self.db.ag_save_rrt(rrt_id, rrt_data)
    
    def get_rrt(self, rrt_id: str) -> Dict:
        return self.db.ag_get_rrt(rrt_id)
    
    def save_sat(self, sat_id: str, sat_data: Dict):
        self.db.ag_save_sat(sat_id, sat_data)
    
    def get_sat(self, sat_id: str) -> Dict:
        return self.db.ag_get_sat(sat_id)
    
    def save_challenge(self, challenge_id: str, challenge_data: Dict):
        self.db.ag_save_challenge(challenge_id, challenge_data)
    
    def get_challenge(self, challenge_id: str) -> Dict:
        return self.db.ag_get_challenge(challenge_id)
    
    def delete_challenge(self, challenge_id: str):
        self.db.ag_delete_challenge(challenge_id)
    
    def save_session(self, session_id: str, session_data: Dict):
        self.db.ag_save_session(session_id, session_data)
    
    def get_session(self, session_id: str) -> Dict:
        return self.db.ag_get_session(session_id)
    
    def set_keypair(self, privkey: str, pubkey: str):
        self.db.meta_set("ag_privkey", privkey)
        self.db.meta_set("ag_pubkey", pubkey)
    
    def get_ag_privkey(self) -> str:
        return self.db.meta_get("ag_privkey")
    
    def get_ag_pubkey(self) -> str:
        return self.db.meta_get("ag_pubkey")
    
    def save_device_secret(self, device_id: str, device_secret: str):
        self.db.ag_save_device_secret(device_id, device_secret)
    
    def get_device_secret(self, device_id: str) -> str:
        return self.db.ag_get_device_secret(device_id)
    
    def set_ec_pubkey(self, ec_pubkey: str):
        self.db.meta_set("ec_pubkey", ec_pubkey)
    
    def get_ec_pubkey(self) -> str:
        return self.db.meta_get("ec_pubkey")
