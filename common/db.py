import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class SimpleDB:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, collection: str) -> Path:
        return self.data_dir / f"{collection}.json"
    
    def load(self, collection: str) -> Dict[str, Any]:
        file_path = self._get_file_path(collection)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def save(self, collection: str, data: Dict[str, Any]):
        file_path = self._get_file_path(collection)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get(self, collection: str, key: str) -> Optional[Any]:
        data = self.load(collection)
        return data.get(key)
    
    def set(self, collection: str, key: str, value: Any):
        data = self.load(collection)
        data[key] = value
        self.save(collection, data)
    
    def delete(self, collection: str, key: str) -> bool:
        data = self.load(collection)
        if key in data:
            del data[key]
            self.save(collection, data)
            return True
        return False
