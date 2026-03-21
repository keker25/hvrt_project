from pydantic import BaseModel
from typing import Dict, Optional
from common.models import RRT, SAT


class IssueRRTRequest(BaseModel):
    device_id: str
    region_id: str


class IssueRRTResponse(BaseModel):
    rrt: dict


class IssueSATRequest(BaseModel):
    device_id: str
    rrt_id: str


class IssueSATResponse(BaseModel):
    sat: dict


class AccessRequest(BaseModel):
    request_id: str
    device_id: str
    sat: dict
    rrt: dict
    mode: Optional[str] = "default"


class AccessRequestResponse(BaseModel):
    request_id: str
    challenge_id: str
    nonce: str
    timestamp: str


class AccessRespond(BaseModel):
    request_id: str
    challenge_id: str
    device_id: str
    response_hmac: str


class AccessRespondResponse(BaseModel):
    request_id: str
    result: str
    reason: str
    session_id: Optional[str] = None


class StateCurrentResponse(BaseModel):
    region_id: str
    revocation_version: int
    device_states: Dict[str, str]
