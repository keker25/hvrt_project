# from datetime import datetime, timedelta
# from typing import Dict, Any
# from .models import GTT, RRT, SAT
# from .crypto_utils import generate_id, sign_with_ed25519, verify_with_ed25519
# from .config import Config
#
#
# def create_gtt(root_privkey: str, root_pubkey: str, revocation_version: int = 1) -> GTT:
#     valid_from = datetime.utcnow()
#     valid_to = valid_from + timedelta(days=Config.GTT_VALID_DAYS)
#
#     gtt_data = {
#         "gtt_id": generate_id("gtt"),
#         "root_pubkey": root_pubkey,
#         "policy_version": 1,
#         "revocation_version": revocation_version,
#         "valid_from": valid_from.isoformat() + "Z",
#         "valid_to": valid_to.isoformat() + "Z"
#     }
#
#     signature = sign_with_ed25519(root_privkey, gtt_data)
#
#     return GTT(**gtt_data, signature=signature)
#
#
# def verify_gtt(gtt: GTT, root_pubkey: str) -> bool:
#     gtt_dict = gtt.dict()
#     signature = gtt_dict.pop("signature")
#
#     if not verify_with_ed25519(root_pubkey, gtt_dict, signature):
#         return False
#
#     now = datetime.utcnow()
#     valid_from = datetime.fromisoformat(gtt.valid_from.replace("Z", "+00:00"))
#     valid_to = datetime.fromisoformat(gtt.valid_to.replace("Z", "+00:00"))
#
#     if not (valid_from <= now <= valid_to):
#         return False
#
#     return True
#
#
# def create_rrt(ag_privkey: str, device_id: str, region_id: str, gtt_id: str) -> RRT:
#     issue_time = datetime.utcnow()
#     expire_time = issue_time + timedelta(hours=Config.RRT_VALID_HOURS)
#
#     rrt_data = {
#         "rrt_id": generate_id("rrt"),
#         "device_id": device_id,
#         "region_id": region_id,
#         "gtt_id": gtt_id,
#         "issue_time": issue_time.isoformat() + "Z",
#         "expire_time": expire_time.isoformat() + "Z",
#         "policy_tag": "default"
#     }
#
#     signature = sign_with_ed25519(ag_privkey, rrt_data)
#
#     return RRT(**rrt_data, signature=signature)
#
#
# def verify_rrt(rrt: RRT, ag_pubkey: str, expected_gtt_id: str) -> bool:
#     rrt_dict = rrt.dict()
#     signature = rrt_dict.pop("signature")
#
#     if not verify_with_ed25519(ag_pubkey, rrt_dict, signature):
#         return False
#
#     if rrt.gtt_id != expected_gtt_id:
#         return False
#
#     now = datetime.utcnow()
#     expire_time = datetime.fromisoformat(rrt.expire_time.replace("Z", "+00:00"))
#
#     if now > expire_time:
#         return False
#
#     return True
#
#
# def create_sat(ag_privkey: str, device_id: str, rrt_id: str) -> SAT:
#     issue_time = datetime.utcnow()
#     expire_time = issue_time + timedelta(minutes=Config.SAT_VALID_MINUTES)
#
#     sat_data = {
#         "sat_id": generate_id("sat"),
#         "device_id": device_id,
#         "rrt_id": rrt_id,
#         "issue_time": issue_time.isoformat() + "Z",
#         "expire_time": expire_time.isoformat() + "Z",
#         "auth_scope": "local_access"
#     }
#
#     signature = sign_with_ed25519(ag_privkey, sat_data)
#
#     return SAT(**sat_data, signature=signature)
#
#
# def verify_sat(sat: SAT, ag_pubkey: str, expected_rrt_id: str, expected_device_id: str) -> bool:
#     sat_dict = sat.dict()
#     signature = sat_dict.pop("signature")
#
#     if not verify_with_ed25519(ag_pubkey, sat_dict, signature):
#         return False
#
#     if sat.rrt_id != expected_rrt_id:
#         return False
#
#     if sat.device_id != expected_device_id:
#         return False
#
#     now = datetime.utcnow()
#     expire_time = datetime.fromisoformat(sat.expire_time.replace("Z", "+00:00"))
#
#     if now > expire_time:
#         return False
#
#     return True


from datetime import datetime, timedelta, timezone
from .models import GTT, RRT, SAT
from .crypto_utils import generate_id, sign_with_ed25519, verify_with_ed25519
from .config import Config


def _utcnow():
    return datetime.now(timezone.utc)


def _parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def create_gtt(root_privkey: str, root_pubkey: str, revocation_version: int = 1) -> GTT:
    valid_from = _utcnow()
    valid_to = valid_from + timedelta(days=Config.GTT_VALID_DAYS)

    gtt_data = {
        "gtt_id": generate_id("gtt"),
        "root_pubkey": root_pubkey,
        "policy_version": 1,
        "revocation_version": revocation_version,
        "valid_from": valid_from.isoformat().replace("+00:00", "Z"),
        "valid_to": valid_to.isoformat().replace("+00:00", "Z")
    }

    signature = sign_with_ed25519(root_privkey, gtt_data)
    return GTT(**gtt_data, signature=signature)


def verify_gtt(gtt: GTT, root_pubkey: str) -> bool:
    gtt_dict = gtt.model_dump()
    signature = gtt_dict.pop("signature")

    if not verify_with_ed25519(root_pubkey, gtt_dict, signature):
        return False

    now = _utcnow()
    valid_from = _parse_utc(gtt.valid_from)
    valid_to = _parse_utc(gtt.valid_to)
    return valid_from <= now <= valid_to


def create_rrt(ag_privkey: str, device_id: str, region_id: str, gtt_id: str, status_version: int = 1) -> RRT:
    issue_time = _utcnow()
    expire_time = issue_time + timedelta(hours=Config.RRT_VALID_HOURS)

    rrt_data = {
        "rrt_id": generate_id("rrt"),
        "device_id": device_id,
        "region_id": region_id,
        "gtt_id": gtt_id,
        "issue_time": issue_time.isoformat().replace("+00:00", "Z"),
        "expire_time": expire_time.isoformat().replace("+00:00", "Z"),
        "policy_tag": "default",
        "status_version": status_version,
        "access_scope": "regionwide"
    }

    signature = sign_with_ed25519(ag_privkey, rrt_data)
    return RRT(**rrt_data, signature=signature)


def verify_rrt(rrt: RRT, ag_pubkey: str, expected_gtt_id: str) -> bool:
    rrt_dict = rrt.model_dump()
    signature = rrt_dict.pop("signature")

    if not verify_with_ed25519(ag_pubkey, rrt_dict, signature):
        return False
    if rrt.gtt_id != expected_gtt_id:
        return False

    return _utcnow() <= _parse_utc(rrt.expire_time)


def create_sat(ag_privkey: str, device_id: str, rrt_id: str) -> SAT:
    issue_time = _utcnow()
    expire_time = issue_time + timedelta(minutes=Config.SAT_VALID_MINUTES)
    nonce_seed = generate_id("nseed")

    sat_data = {
        "sat_id": generate_id("sat"),
        "device_id": device_id,
        "rrt_id": rrt_id,
        "issue_time": issue_time.isoformat().replace("+00:00", "Z"),
        "expire_time": expire_time.isoformat().replace("+00:00", "Z"),
        "auth_scope": "local_access",
        "gateway_scope": "current",
        "nonce_seed": nonce_seed
    }

    signature = sign_with_ed25519(ag_privkey, sat_data)
    return SAT(**sat_data, signature=signature)


def verify_sat(sat: SAT, ag_pubkey: str, expected_rrt_id: str, expected_device_id: str) -> bool:
    sat_dict = sat.model_dump()
    signature = sat_dict.pop("signature")

    if not verify_with_ed25519(ag_pubkey, sat_dict, signature):
        return False
    if sat.rrt_id != expected_rrt_id:
        return False
    if sat.device_id != expected_device_id:
        return False

    return _utcnow() <= _parse_utc(sat.expire_time)

