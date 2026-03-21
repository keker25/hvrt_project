# from fastapi import APIRouter, HTTPException
# from .schemas import (
#     IssueRRTRequest,
#     IssueSATRequest,
#     AccessRequest,
#     AccessRespond,
# )
# from .service import AGService
#
# router = APIRouter(prefix="/ag", tags=["ag"])
# service = AGService()
#
#
# @router.post("/issue_rrt")
# async def issue_rrt(request: IssueRRTRequest):
#     try:
#         return service.issue_rrt(request.device_id, request.region_id)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
#
# @router.post("/issue_sat")
# async def issue_sat(request: IssueSATRequest):
#     try:
#         return service.issue_sat(request.device_id, request.rrt_id)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
#
# @router.post("/access/request")
# async def access_request(request: AccessRequest):
#     result = service.create_access_challenge(
#         request.request_id,
#         request.device_id,
#         request.sat,
#         request.rrt
#     )
#     return result
#
#
# @router.post("/access/respond")
# async def access_respond(request: AccessRespond):
#     result = await service.verify_access_response(
#         request.request_id,
#         request.challenge_id,
#         request.device_id,
#         request.response_hmac
#     )
#     return result
#
#
# @router.get("/state/current")
# async def get_state_current():
#     return service.get_state_current()
#
#
# @router.post("/state/sync")
# async def sync_state():
#     await service.sync_with_ec()
#     return {"status": "synced"}


from fastapi import APIRouter, HTTPException
from .schemas import (
    IssueRRTRequest,
    IssueSATRequest,
    AccessRequest,
    AccessRespond,
)
from .service import AGService

router = APIRouter(prefix="/ag", tags=["ag"])
service = AGService()


@router.post("/issue_rrt")
async def issue_rrt(request: IssueRRTRequest):
    try:
        return await service.issue_rrt(request.device_id, request.region_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/issue_sat")
async def issue_sat(request: IssueSATRequest):
    try:
        return service.issue_sat(request.device_id, request.rrt_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/access/request")
async def access_request(request: AccessRequest):
    return service.create_access_challenge(
        request.request_id,
        request.device_id,
        request.sat,
        request.rrt,
        request.status_receipt
    )


@router.post("/access/respond")
async def access_respond(request: AccessRespond):
    return await service.verify_access_response(
        request.request_id,
        request.challenge_id,
        request.device_id,
        request.response_hmac,
        request.mode
    )


@router.get("/state/current")
async def get_state_current():
    return service.get_state_current()


@router.post("/state/sync")
async def sync_state():
    await service.sync_with_ec()
    return {"status": "synced"}
