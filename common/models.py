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
    status_version: int  # 添加：状态版本
    access_scope: str = "regionwide"  # 添加：访问作用域
    signature: str


class SAT(BaseModel):
    sat_id: str
    device_id: str
    rrt_id: str
    issue_time: str
    expire_time: str
    auth_scope: str = "local_access"
    gateway_scope: str = "current"  # 添加：网关作用域
    nonce_seed: str  # 添加：随机数种子
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


class DeltaEvent(BaseModel):
    event_id: str
    version: int
    type: str
    device_id: str
    status: Optional[str] = None
    region_id: Optional[str] = None
    device_secret: Optional[str] = None
    timestamp: str
