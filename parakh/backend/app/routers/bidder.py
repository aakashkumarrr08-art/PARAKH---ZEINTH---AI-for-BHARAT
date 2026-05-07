from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import get_current_user, require_roles
from app.db import get_database
from app.models.bidder import Bidder, BidderCreate, ChecklistStatusItem
from app.models.evidence import ExtractedEvidence
from app.models.user import Role, User
from app.services import bdi_service

router = APIRouter(tags=["bidders"])


@router.get("/tenders/{tender_id}/bidders", response_model=list[Bidder])
async def list_bidders(
    tender_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> list[Bidder]:
    return await bdi_service.list_bidders(db, tender_id)


@router.post("/tenders/{tender_id}/bidders", response_model=Bidder)
async def create_bidder(
    tender_id: str,
    payload: BidderCreate,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> Bidder:
    return await bdi_service.register_bidder(db, tender_id, payload)


@router.get("/tenders/{tender_id}/bidders/{bidder_id}", response_model=Bidder)
async def get_bidder(
    tender_id: str,
    bidder_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> Bidder:
    return await bdi_service.get_bidder(db, tender_id, bidder_id)


@router.post("/tenders/{tender_id}/bidders/{bidder_id}/documents", response_model=Bidder)
async def upload_bidder_document(
    tender_id: str,
    bidder_id: str,
    doc_name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> Bidder:
    return await bdi_service.upload_bidder_document(db, tender_id, bidder_id, doc_name, file)


@router.post("/tenders/{tender_id}/bidders/{bidder_id}/ingest", response_model=list[ExtractedEvidence])
async def ingest_bidder_docs(
    tender_id: str,
    bidder_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> list[ExtractedEvidence]:
    return await bdi_service.ingest_bidder_documents(db, tender_id, bidder_id)


@router.get("/tenders/{tender_id}/bidders/{bidder_id}/checklist", response_model=list[ChecklistStatusItem])
async def bidder_checklist(
    tender_id: str,
    bidder_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> list[ChecklistStatusItem]:
    return await bdi_service.get_bidder_checklist(db, tender_id, bidder_id)


@router.get("/tenders/{tender_id}/bidders/{bidder_id}/evidence", response_model=list[ExtractedEvidence])
async def bidder_evidence(
    tender_id: str,
    bidder_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> list[ExtractedEvidence]:
    return await bdi_service.get_extracted_evidence(db, tender_id, bidder_id)
