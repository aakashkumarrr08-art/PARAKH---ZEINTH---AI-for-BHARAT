from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import get_current_user, require_roles
from app.db import get_database
from app.models.manifest import CriteriaManifestVersion
from app.models.tender import ManifestUpdateRequest, Tender, TenderCreate
from app.models.user import Role, User
from app.services import tue_service

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=list[Tender])
async def list_tenders(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> list[Tender]:
    return await tue_service.list_tenders(db)


@router.post("", response_model=Tender)
async def create_tender(
    payload: TenderCreate,
    user: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> Tender:
    return await tue_service.create_tender(db, payload, user.username)


@router.get("/{tender_id}", response_model=Tender)
async def get_tender(
    tender_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> Tender:
    return await tue_service.get_tender(db, tender_id)


@router.post("/{tender_id}/documents", response_model=Tender)
async def upload_tender_document(
    tender_id: str,
    doc_type: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> Tender:
    return await tue_service.upload_tender_document(db, tender_id, doc_type, file)


@router.post("/{tender_id}/generate_manifest", response_model=CriteriaManifestVersion)
async def generate_manifest(
    tender_id: str,
    user: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CriteriaManifestVersion:
    return await tue_service.generate_manifest(db, tender_id, user.username)


@router.get("/{tender_id}/manifests/latest", response_model=CriteriaManifestVersion)
async def latest_manifest(
    tender_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CriteriaManifestVersion:
    return await tue_service.get_latest_manifest(db, tender_id)


@router.put("/{tender_id}/manifests/{manifest_id}", response_model=CriteriaManifestVersion)
async def update_manifest(
    tender_id: str,
    manifest_id: str,
    payload: ManifestUpdateRequest,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CriteriaManifestVersion:
    return await tue_service.update_manifest(db, tender_id, manifest_id, payload)


@router.put("/{tender_id}/manifests/{manifest_id}/approve", response_model=CriteriaManifestVersion)
async def approve_manifest(
    tender_id: str,
    manifest_id: str,
    user: Annotated[User, Depends(require_roles(Role.ADMIN, Role.OFFICER))],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CriteriaManifestVersion:
    return await tue_service.approve_manifest(db, tender_id, manifest_id, user.username)
