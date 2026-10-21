from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User
from src.schemas import LoginInput, UserInput
from src.services.auth import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(payload: UserInput, database: Session = Depends(get_db)) -> dict:
    email = payload.email.lower()
    if database.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=email, full_name=payload.full_name, password_hash=hash_password(payload.password)
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    return {"access_token": create_token(user.id), "token_type": "bearer"}


@router.post("/login")
def login(payload: LoginInput, database: Session = Depends(get_db)) -> dict:
    user = database.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(user.id), "token_type": "bearer"}
