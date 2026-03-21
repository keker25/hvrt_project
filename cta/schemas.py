# from pydantic import BaseModel
# from typing import List, Optional
# from common.models import GTT, RevocationEvent
#
#
# class RegisterDeviceRequest(BaseModel):
#     device_id: str
#     region_id: str
#
#
# class RegisterDeviceResponse(BaseModel):
#     device_id: str
#     device_secret: str
#     status: str
#
#
# class GTTCurrentResponse(BaseModel):
#     gtt: GTT
#
#
# class RevocationDeltaResponse(BaseModel):
#     from_version: int
#     to_version: int
#     changes: List[RevocationEvent]
#
#
# class RevokeDeviceRequest(BaseModel):
#     device_id: str
#     reason: Optional[str] = None
#
#
# class RevokeDeviceResponse(BaseModel):
#     device_id: str
#     status: str
#     new_version: int
#
#
# class OnlineVerifyRequest(BaseModel):
#     device_id: str
#     sat: dict
#     rrt: dict
#
#
# class OnlineVerifyResponse(BaseModel):
#     result: str
#     reason: str
#     revocation_version: int

from pydantic import BaseModel
from typing import Optional, Dict, Any


class RegisterDeviceRequest(BaseModel):
    device_id: str
    region_id: str


class RegisterDeviceResponse(BaseModel):
    device_id: str
    device_secret: str
    status: str


class RevokeDeviceRequest(BaseModel):
    device_id: str
    reason: Optional[str] = None


class RevokeDeviceResponse(BaseModel):
    device_id: str
    status: str
    new_version: int


class GTTCurrentResponse(BaseModel):
    gtt: Dict[str, Any]


class RevocationDeltaResponse(BaseModel):
    from_version: int
    to_version: int
    changes: list[Dict[str, Any]]


class OnlineVerifyRequest(BaseModel):
    device_id: str
    sat: Dict[str, Any]
    rrt: Dict[str, Any]
    ec_pubkey: str
    ag_pubkey: str


class OnlineVerifyResponse(BaseModel):
    result: str
    reason: str
    revocation_version: Optional[int] = None


class StatusReceiptRequest(BaseModel):
    device_id: str


class StatusReceiptResponse(BaseModel):
    receipt: Dict[str, Any]
