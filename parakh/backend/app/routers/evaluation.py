from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import get_current_user, require_roles
from app.db import get_database
from app.models.evaluation import EvaluationOverview, OverrideRequest
from app.models.user import Role, User
from app.services import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/metadata/reason-codes", response_model=list[str])
async def reason_codes(_: Annotated[User, Depends(get_current_user)]) -> list[str]:
    return evaluation_service.reason_codes()


@router.post("/{tender_id}/{bidder_id}", response_model=EvaluationOverview)
async def evaluate(
    tender_id: str,
    bidder_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> EvaluationOverview:
    return await evaluation_service.evaluate_bidder(db, tender_id, bidder_id)


@router.get("/{tender_id}/{bidder_id}", response_model=EvaluationOverview)
async def get_evaluation(
    tender_id: str,
    bidder_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> EvaluationOverview:
    return await evaluation_service.get_evaluation_overview(db, tender_id, bidder_id)


@router.post("/{tender_id}/{bidder_id}/{criterion_id}/override", response_model=EvaluationOverview)
async def override(
    tender_id: str,
    bidder_id: str,
    criterion_id: str,
    payload: OverrideRequest,
    user: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> EvaluationOverview:
    return await evaluation_service.override_criterion(db, tender_id, bidder_id, criterion_id, payload, user)

