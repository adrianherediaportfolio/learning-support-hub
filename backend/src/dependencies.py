import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.models import Student, User

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    database: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token") from None
    user = database.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def owned_student(database: Session, student_id: int, user_id: int) -> Student:
    student = database.scalar(
        select(Student).where(Student.id == student_id, Student.owner_id == user_id)
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student
