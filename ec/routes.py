from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .schemas import (
    StateCurrentResponse,
    StateDeltaResponse,
    GTTSummaryResponse,
)
from .service import ECService
from common import get_logger

router = APIRouter(prefix="/ec", tags=["ec"])
service = ECService()


class IssueRRTRequest(BaseModel):
    device_id: str
    region_id: str


@router.get("/state/current")
async def get_state_current():
    return service.get_state_current()


@router.get("/state/delta")
async def get_state_delta(from_version: int):
    return service.get_state_delta(from_version)


@router.get("/gtt/current")
async def get_gtt_current():
    try:
        return {"gtt": service.get_gtt_current()}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rrt/issue")
async def issue_rrt(request: IssueRRTRequest):
    try:
        return service.issue_rrt(request.device_id, request.region_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/state/sync")
async def sync_state():
    try:
        from .sync_worker import ECSyncWorker
        worker = ECSyncWorker(service.storage)
        await worker.sync_with_cta()
        return {"status": "synced"}
    except Exception as e:
        logger = get_logger("ec_routes")
        logger.error(f"Sync state failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
