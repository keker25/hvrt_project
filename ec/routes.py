from fastapi import APIRouter, HTTPException
from .schemas import (
    StateCurrentResponse,
    StateDeltaResponse,
    GTTSummaryResponse,
)
from .service import ECService

router = APIRouter(prefix="/ec", tags=["ec"])
service = ECService()


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
