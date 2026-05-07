from collections.abc import AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> AsyncIOMotorDatabase:
    global client, database
    settings = get_settings()
    if database is None:
        client = AsyncIOMotorClient(settings.mongo_uri)
        database = client[settings.mongo_db]
    return database


async def close_mongo_connection() -> None:
    global client, database
    if client is not None:
        client.close()
    client = None
    database = None


async def get_database() -> AsyncIterator[AsyncIOMotorDatabase]:
    db = await connect_to_mongo()
    yield db


async def create_indexes() -> None:
    db = await connect_to_mongo()
    await db.users.create_index("username", unique=True)
    await db.tenders.create_index([("status", 1), ("created_at", -1)])
    await db.criteria_manifest_versions.create_index(
        [("tender_id", 1), ("version", -1)],
        unique=True,
    )
    await db.criteria_manifest_versions.create_index([("tender_id", 1), ("status", 1)])
    await db.bidders.create_index([("tender_id", 1), ("name", 1)], unique=True)
    await db.bidders.create_index([("tender_id", 1), ("hard_disqualified", 1)])
    await db.extracted_evidence.create_index(
        [("tender_id", 1), ("bidder_id", 1), ("document_id", 1)],
        unique=True,
    )
    await db.extracted_evidence.create_index([("tender_id", 1), ("bidder_id", 1), ("created_at", -1)])
    await db.evaluation_events.create_index([("tender_id", 1), ("bidder_id", 1), ("sequence", 1)], unique=True)
    await db.evaluation_events.create_index([("tender_id", 1), ("bidder_id", 1), ("criterion_id", 1), ("created_at", -1)])
    await db.evaluation_events.create_index("event_hash", unique=True)
    await db.clarification_requests.create_index([("tender_id", 1), ("bidder_id", 1), ("status", 1)])

