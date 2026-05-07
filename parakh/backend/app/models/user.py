from enum import Enum

from pydantic import BaseModel

from app.models.common import MongoModel


class Role(str, Enum):
    ADMIN = "ADMIN"
    OFFICER = "OFFICER"


class User(MongoModel):
    username: str
    full_name: str
    hashed_password: str
    role: Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: Role


class TokenPayload(BaseModel):
    sub: str
    role: Role
    exp: int
