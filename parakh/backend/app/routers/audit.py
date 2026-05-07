from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import get_current_user
from app.db import get_database
from app.models.user import User
from app.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/stats", response_model=dict[str, int])
async def dashboard_stats(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> dict[str, int]:
    return await audit_service.get_dashboard_stats(db)


@router.get("/{tender_id}/{bidder_id}", response_model=dict)
async def audit_history(
    tender_id: str,
    bidder_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> dict:
    history = await audit_service.get_audit_history(db, tender_id, bidder_id)
    return {criterion: [event.model_dump(by_alias=True) for event in events] for criterion, events in history.items()}


@router.get("/{tender_id}/{bidder_id}/export")
async def export_audit(
    tender_id: str,
    bidder_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    export_format: Annotated[str, Query(alias="format")] = "xlsx",
) -> FileResponse:
    path = await audit_service.export_audit_report(db, tender_id, bidder_id, export_format)
    media_type = "application/pdf" if export_format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(path, media_type=media_type, filename=path.name)
