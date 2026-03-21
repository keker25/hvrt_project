import json
import os
from pathlib import Path


class TDStorage:
    def __init__(self, data_dir: str = "td_client/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, device_id: str) -> Path:
        return self.data_dir / f"{device_id}.json"
    
    def save_device(self, device_id: str, device_secret: str):
        data = {
            "device_id": device_id,
            "device_secret": device_secret,
            "rrt": None,
            "sat": None
        }
        file_path = self._get_file_path(device_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_device(self, device_id: str):
        file_path = self._get_file_path(device_id)
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def save_tickets(self, device_id: str, rrt=None, sat=None):
        data = self.load_device(device_id)
        if not data:
            raise ValueError(f"Device {device_id} not found")
        
        if rrt is not None:
            data["rrt"] = rrt
        if sat is not None:
            data["sat"] = sat
        
        file_path = self._get_file_path(device_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
