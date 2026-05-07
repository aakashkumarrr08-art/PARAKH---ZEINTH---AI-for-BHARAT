from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import create_access_token, get_current_user, verify_password
from app.db import get_database
from app.models.user import TokenResponse, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> TokenResponse:
    record = await db.users.find_one({"username": username})
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    user = User(**record)
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    token = create_access_token(user.username, user.role)
    return TokenResponse(access_token=token, username=user.username, role=user.role)


@router.get("/me", response_model=User, response_model_exclude={"hashed_password"})
async def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
