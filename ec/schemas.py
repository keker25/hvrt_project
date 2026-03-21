from pydantic import BaseModel
from typing import List, Dict
from common.models import RevocationEvent


class StateCurrentResponse(BaseModel):
    region_id: str
    revocation_version: int
    device_states: Dict[str, str]


class StateDeltaResponse(BaseModel):
    from_version: int
    to_version: int
    changes: List[RevocationEvent]


class GTTSummaryResponse(BaseModel):
    gtt_id: str
    root_pubkey: str
    policy_version: int
    revocation_version: int
