from pathlib import Path
from common import SimpleDB
from typing import Dict


class AGStorage:
    def __init__(self, data_dir: str = "ag/data"):
        self.db = SimpleDB(data_dir)
        self._initialize()
    
    def _initialize(self):
        if not self.db.get("meta", "revocation_version"):
            self.db.set("meta", "revocation_version", 0)
        if not self.db.load("device_states"):
            self.db.save("device_states", {})
        if not self.db.load("device_secrets"):
            self.db.save("device_secrets", {})
        if not self.db.load("rrts"):
            self.db.save("rrts", {})
        if not self.db.load("sats"):
            self.db.save("sats", {})
        if not self.db.load("challenges"):
            self.db.save("challenges", {})
        if not self.db.load("sessions"):
            self.db.save("sessions", {})
    
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
    
    def save_rrt(self, rrt_id: str, rrt_data: Dict):
        rrts = self.db.load("rrts")
        rrts[rrt_id] = rrt_data
        self.db.save("rrts", rrts)
    
    def get_rrt(self, rrt_id: str) -> Dict:
        return self.db.get("rrts", rrt_id)
    
    def save_sat(self, sat_id: str, sat_data: Dict):
        sats = self.db.load("sats")
        sats[sat_id] = sat_data
        self.db.save("sats", sats)
    
    def get_sat(self, sat_id: str) -> Dict:
        return self.db.get("sats", sat_id)
    
    def save_challenge(self, challenge_id: str, challenge_data: Dict):
        challenges = self.db.load("challenges")
        challenges[challenge_id] = challenge_data
        self.db.save("challenges", challenges)
    
    def get_challenge(self, challenge_id: str) -> Dict:
        return self.db.get("challenges", challenge_id)
    
    def delete_challenge(self, challenge_id: str):
        challenges = self.db.load("challenges")
        if challenge_id in challenges:
            del challenges[challenge_id]
            self.db.save("challenges", challenges)
    
    def save_session(self, session_id: str, session_data: Dict):
        sessions = self.db.load("sessions")
        sessions[session_id] = session_data
        self.db.save("sessions", sessions)
    
    def get_session(self, session_id: str) -> Dict:
        return self.db.get("sessions", session_id)
    
    def set_keypair(self, privkey: str, pubkey: str):
        self.db.set("meta", "ag_privkey", privkey)
        self.db.set("meta", "ag_pubkey", pubkey)
    
    def get_ag_privkey(self) -> str:
        return self.db.get("meta", "ag_privkey")
    
    def get_ag_pubkey(self) -> str:
        return self.db.get("meta", "ag_pubkey")
    
    def save_device_secret(self, device_id: str, device_secret: str):
        device_secrets = self.db.load("device_secrets")
        device_secrets[device_id] = device_secret
        self.db.save("device_secrets", device_secrets)
    
    def get_device_secret(self, device_id: str) -> str:
        device_secrets = self.db.load("device_secrets")
        return device_secrets.get(device_id)
    
    def set_ec_pubkey(self, ec_pubkey: str):
        self.db.set("meta", "ec_pubkey", ec_pubkey)
    
    def get_ec_pubkey(self) -> str:
        return self.db.get("meta", "ec_pubkey")
