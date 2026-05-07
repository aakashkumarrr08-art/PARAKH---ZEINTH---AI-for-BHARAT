from datetime import date, datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def generate_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def mongo_compatible(value):
    if isinstance(value, BaseModel):
        return mongo_compatible(value.model_dump(by_alias=True))
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: mongo_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mongo_compatible(item) for item in value]
    return value


class MongoModel(BaseModel):
    id: str = Field(default_factory=generate_id, alias="_id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
