from typing import Dict, List, Optional
from datetime import datetime
from .models import RevocationEvent


def apply_delta(
    current_states: Dict[str, str],
    current_version: int,
    delta: List[RevocationEvent]
) -> tuple[Dict[str, str], int]:
    new_states = current_states.copy()
    max_version = current_version
    
    for event in delta:
        new_states[event.device_id] = event.new_status
        if event.version > max_version:
            max_version = event.version
    
    return new_states, max_version


def create_revocation_event(
    device_id: str,
    new_status: str,
    version: int
) -> RevocationEvent:
    return RevocationEvent(
        event_id=f"evt_{version}",
        device_id=device_id,
        new_status=new_status,
        version=version,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
