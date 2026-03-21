from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class GTT(BaseModel):
    gtt_id: str
    root_pubkey: str
    policy_version: int
    revocation_version: int
    valid_from: str
    valid_to: str
    signature: str


class RRT(BaseModel):
    rrt_id: str
    device_id: str
    region_id: str
    gtt_id: str
    issue_time: str
    expire_time: str
    policy_tag: str = "default"
    signature: str


class SAT(BaseModel):
    sat_id: str
    device_id: str
    rrt_id: str
    issue_time: str
    expire_time: str
    auth_scope: str = "local_access"
    signature: str


class RevocationEvent(BaseModel):
    event_id: str
    device_id: str
    new_status: str
    version: int
    timestamp: str


class Device(BaseModel):
    device_id: str
    device_secret: Optional[str] = None
    status: str = "active"
    region_id: str
    created_at: str
