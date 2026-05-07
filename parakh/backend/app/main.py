from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.security import hash_password
from app.db import close_mongo_connection, connect_to_mongo, create_indexes
from app.models.common import mongo_compatible
from app.models.user import Role, User
from app.routers import audit, auth, bidder, evaluation, tender
from app.services.tue_service import ensure_sample_tender


async def _seed_users() -> None:
    db = await connect_to_mongo()
    settings = get_settings()
    users = [
        User(username=settings.demo_admin_username, full_name="PARAKH Demo Admin", hashed_password=hash_password(settings.demo_admin_password), role=Role.ADMIN),
        User(username=settings.demo_officer_username, full_name="PARAKH Demo Officer", hashed_password=hash_password(settings.demo_officer_password), role=Role.OFFICER),
    ]
    for user in users:
        await db.users.update_one(
            {"username": user.username},
            {"$setOnInsert": mongo_compatible(user)},
            upsert=True,
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.upload_root.mkdir(parents=True, exist_ok=True)
    settings.audit_export_root.mkdir(parents=True, exist_ok=True)
    await connect_to_mongo()
    await create_indexes()
    await _seed_users()
    await ensure_sample_tender(await connect_to_mongo())
    yield
    await close_mongo_connection()


app = FastAPI(
    title="PARAKH API",
    version="0.1.0",
    description="Procurement Audit-Ready Assessment & Knowledge Harnessing",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=settings.upload_root), name="uploads")
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(tender.router, prefix=settings.api_prefix)
app.include_router(bidder.router, prefix=settings.api_prefix)
app.include_router(evaluation.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "parakh-api"}
