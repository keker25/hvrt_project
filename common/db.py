import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager


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


class SQLiteDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
        self._initialize_db()
    
    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _initialize_db(self):
        with self._get_connection() as conn:
            # Meta 表 - 存储键值对元数据
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # CTA 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cta_devices (
                    device_id TEXT PRIMARY KEY,
                    secret TEXT NOT NULL,
                    region TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    registered_at REAL NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cta_revocation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL UNIQUE,
                    event_data TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            
            # EC 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ec_device_states (
                    device_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ec_device_secrets (
                    device_id TEXT PRIMARY KEY,
                    secret TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ec_ag_whitelist (
                    ag_id TEXT PRIMARY KEY
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ec_revocation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL UNIQUE,
                    event_data TEXT NOT NULL
                )
            """)
            
            # AG 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ag_device_states (
                    device_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ag_device_secrets (
                    device_id TEXT PRIMARY KEY,
                    secret TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ag_rrts (
                    rrt_id TEXT PRIMARY KEY,
                    rrt_data TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ag_sats (
                    sat_id TEXT PRIMARY KEY,
                    sat_data TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ag_challenges (
                    challenge_id TEXT PRIMARY KEY,
                    challenge_data TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ag_sessions (
                    session_id TEXT PRIMARY KEY,
                    session_data TEXT NOT NULL
                )
            """)
    
    # ============== Meta 操作 ==============
    def meta_get(self, key: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT value FROM meta WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None
    
    def meta_set(self, key: str, value: str):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO meta (key, value)
                VALUES (?, ?)
            """, (key, value))
    
    def meta_get_int(self, key: str, default: int = 0) -> int:
        value = self.meta_get(key)
        return int(value) if value is not None else default
    
    def meta_set_int(self, key: str, value: int):
        self.meta_set(key, str(value))
    
    def meta_get_json(self, key: str) -> Optional[Any]:
        value = self.meta_get(key)
        return json.loads(value) if value is not None else None
    
    def meta_set_json(self, key: str, value: Any):
        self.meta_set(key, json.dumps(value, ensure_ascii=False))
    
    # ============== CTA 操作 ==============
    def cta_save_device(self, device_id: str, secret: str, region: str, status: str = "active"):
        import time
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cta_devices 
                (device_id, secret, region, status, registered_at)
                VALUES (?, ?, ?, ?, ?)
            """, (device_id, secret, region, status, time.time()))
    
    def cta_get_device(self, device_id: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cta_devices WHERE device_id = ?", (device_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def cta_get_all_devices(self) -> Dict[str, Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cta_devices")
            devices = {}
            for row in cursor:
                devices[row["device_id"]] = dict(row)
            return devices
    
    def cta_update_device_status(self, device_id: str, status: str):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE cta_devices SET status = ? WHERE device_id = ?
            """, (status, device_id))
    
    def cta_add_revocation_event(self, version: int, event_data: Dict):
        import time
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cta_revocation_events 
                (version, event_data, created_at)
                VALUES (?, ?, ?)
            """, (version, json.dumps(event_data, ensure_ascii=False), time.time()))
    
    def cta_get_revocation_events_from(self, from_version: int) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT event_data FROM cta_revocation_events 
                WHERE version > ? ORDER BY version ASC
            """, (from_version,))
            events = []
            for row in cursor:
                events.append(json.loads(row["event_data"]))
            return events
    
    # ============== EC 操作 ==============
    def ec_save_device_state(self, device_id: str, status: str):
        import time
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ec_device_states 
                (device_id, status, updated_at)
                VALUES (?, ?, ?)
            """, (device_id, status, time.time()))
    
    def ec_save_device_states(self, states: Dict[str, str]):
        import time
        with self._get_connection() as conn:
            for device_id, status in states.items():
                conn.execute("""
                    INSERT OR REPLACE INTO ec_device_states 
                    (device_id, status, updated_at)
                    VALUES (?, ?, ?)
                """, (device_id, status, time.time()))
    
    def ec_get_device_states(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT device_id, status FROM ec_device_states")
            states = {}
            for row in cursor:
                states[row["device_id"]] = row["status"]
            return states
    
    def ec_save_device_secret(self, device_id: str, secret: str):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ec_device_secrets 
                (device_id, secret)
                VALUES (?, ?)
            """, (device_id, secret))
    
    def ec_get_device_secret(self, device_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT secret FROM ec_device_secrets WHERE device_id = ?", (device_id,))
            row = cursor.fetchone()
            return row["secret"] if row else None
    
    def ec_get_device_secrets(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT device_id, secret FROM ec_device_secrets")
            secrets = {}
            for row in cursor:
                secrets[row["device_id"]] = row["secret"]
            return secrets
    
    def ec_add_ag_to_whitelist(self, ag_id: str):
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO ec_ag_whitelist (ag_id) VALUES (?)", (ag_id,))
    
    def ec_get_ag_whitelist(self) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT ag_id FROM ec_ag_whitelist")
            return [row["ag_id"] for row in cursor]
    
    def ec_add_revocation_event(self, version: int, event_data: Dict):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ec_revocation_events 
                (version, event_data)
                VALUES (?, ?)
            """, (version, json.dumps(event_data, ensure_ascii=False)))
    
    def ec_get_revocation_events_from(self, from_version: int) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT event_data FROM ec_revocation_events 
                WHERE version > ? ORDER BY version ASC
            """, (from_version,))
            events = []
            for row in cursor:
                events.append(json.loads(row["event_data"]))
            return events
    
    def ec_get_all_revocation_events(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT event_data FROM ec_revocation_events ORDER BY version ASC
            """)
            events = []
            for row in cursor:
                events.append(json.loads(row["event_data"]))
            return events
    
    # ============== AG 操作 ==============
    def ag_save_device_state(self, device_id: str, status: str):
        import time
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ag_device_states 
                (device_id, status, updated_at)
                VALUES (?, ?, ?)
            """, (device_id, status, time.time()))
    
    def ag_save_device_states(self, states: Dict[str, str]):
        import time
        with self._get_connection() as conn:
            for device_id, status in states.items():
                conn.execute("""
                    INSERT OR REPLACE INTO ag_device_states 
                    (device_id, status, updated_at)
                    VALUES (?, ?, ?)
                """, (device_id, status, time.time()))
    
    def ag_get_device_states(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT device_id, status FROM ag_device_states")
            states = {}
            for row in cursor:
                states[row["device_id"]] = row["status"]
            return states
    
    def ag_save_device_secret(self, device_id: str, secret: str):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ag_device_secrets 
                (device_id, secret)
                VALUES (?, ?)
            """, (device_id, secret))
    
    def ag_get_device_secret(self, device_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT secret FROM ag_device_secrets WHERE device_id = ?", (device_id,))
            row = cursor.fetchone()
            return row["secret"] if row else None
    
    def ag_get_device_secrets(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT device_id, secret FROM ag_device_secrets")
            secrets = {}
            for row in cursor:
                secrets[row["device_id"]] = row["secret"]
            return secrets
    
    def ag_save_rrt(self, rrt_id: str, rrt_data: Dict):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ag_rrts (rrt_id, rrt_data)
                VALUES (?, ?)
            """, (rrt_id, json.dumps(rrt_data, ensure_ascii=False)))
    
    def ag_get_rrt(self, rrt_id: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT rrt_data FROM ag_rrts WHERE rrt_id = ?", (rrt_id,))
            row = cursor.fetchone()
            return json.loads(row["rrt_data"]) if row else None
    
    def ag_save_sat(self, sat_id: str, sat_data: Dict):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ag_sats (sat_id, sat_data)
                VALUES (?, ?)
            """, (sat_id, json.dumps(sat_data, ensure_ascii=False)))
    
    def ag_get_sat(self, sat_id: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT sat_data FROM ag_sats WHERE sat_id = ?", (sat_id,))
            row = cursor.fetchone()
            return json.loads(row["sat_data"]) if row else None
    
    def ag_save_challenge(self, challenge_id: str, challenge_data: Dict):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ag_challenges (challenge_id, challenge_data)
                VALUES (?, ?)
            """, (challenge_id, json.dumps(challenge_data, ensure_ascii=False)))
    
    def ag_get_challenge(self, challenge_id: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT challenge_data FROM ag_challenges WHERE challenge_id = ?", (challenge_id,))
            row = cursor.fetchone()
            return json.loads(row["challenge_data"]) if row else None
    
    def ag_delete_challenge(self, challenge_id: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM ag_challenges WHERE challenge_id = ?", (challenge_id,))
    
    def ag_save_session(self, session_id: str, session_data: Dict):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ag_sessions (session_id, session_data)
                VALUES (?, ?)
            """, (session_id, json.dumps(session_data, ensure_ascii=False)))
    
    def ag_get_session(self, session_id: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT session_data FROM ag_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return json.loads(row["session_data"]) if row else None
