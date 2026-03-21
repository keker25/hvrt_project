# from fastapi import APIRouter, HTTPException
# from .schemas import (
#     RegisterDeviceRequest,
#     RegisterDeviceResponse,
#     GTTCurrentResponse,
#     RevocationDeltaResponse,
#     RevokeDeviceRequest,
#     RevokeDeviceResponse,
#     OnlineVerifyRequest,
#     OnlineVerifyResponse,
# )
# from .service import CTAService
#
# router = APIRouter(prefix="/cta", tags=["cta"])
# service = CTAService()
#
#
# @router.post("/register_device", response_model=RegisterDeviceResponse)
# async def register_device(request: RegisterDeviceRequest):
#     try:
#         device = service.register_device(request.device_id, request.region_id)
#         return RegisterDeviceResponse(
#             device_id=device.device_id,
#             device_secret=device.device_secret,
#             status=device.status
#         )
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
#
# @router.get("/gtt/current")
# async def get_current_gtt():
#     gtt = service.get_current_gtt()
#     return {"gtt": gtt}
#
#
# @router.get("/revocation/delta")
# async def get_revocation_delta(from_version: int):
#     delta = service.get_revocation_delta(from_version)
#     return delta
#
#
# @router.post("/revoke_device")
# async def revoke_device(request: RevokeDeviceRequest):
#     try:
#         result = service.revoke_device(request.device_id, request.reason)
#         return result
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
#
# @router.post("/auth/online_verify")
# async def online_verify(request: OnlineVerifyRequest):
#     result = service.online_verify(request.device_id, request.sat, request.rrt)
#     return result
from fastapi import APIRouter, HTTPException
from .schemas import (
    RegisterDeviceRequest,
    RegisterDeviceResponse,
    GTTCurrentResponse,
    RevocationDeltaResponse,
    RevokeDeviceRequest,
    RevokeDeviceResponse,
    OnlineVerifyRequest,
    OnlineVerifyResponse,
    StatusReceiptRequest,
    StatusReceiptResponse,
)
from .service import CTAService

router = APIRouter(prefix="/cta", tags=["cta"])
service = CTAService()


@router.post("/register_device", response_model=RegisterDeviceResponse)
async def register_device(request: RegisterDeviceRequest):
    try:
        device = service.register_device(request.device_id, request.region_id)
        return RegisterDeviceResponse(
            device_id=device.device_id,
            device_secret=device.device_secret,
            status=device.status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/gtt/current", response_model=GTTCurrentResponse)
async def get_current_gtt():
    return {"gtt": service.get_current_gtt()}


@router.get("/revocation/delta", response_model=RevocationDeltaResponse)
async def get_revocation_delta(from_version: int):
    return service.get_revocation_delta(from_version)


@router.post("/revoke_device", response_model=RevokeDeviceResponse)
async def revoke_device(request: RevokeDeviceRequest):
    try:
        return service.revoke_device(request.device_id, request.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/online_verify", response_model=OnlineVerifyResponse)
async def online_verify(request: OnlineVerifyRequest):
    return service.online_verify(
        request.device_id,
        request.sat,
        request.rrt,
        request.ec_pubkey,
        request.ag_pubkey
    )


@router.post("/device/status_receipt", response_model=StatusReceiptResponse)
async def issue_status_receipt(request: StatusReceiptRequest):
    try:
        return {"receipt": service.issue_status_receipt(request.device_id, request.request_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
