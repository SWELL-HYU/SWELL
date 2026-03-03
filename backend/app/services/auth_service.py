"""
인증 관련 비즈니스 로직.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateEmailError, InvalidCredentialsError, UnauthorizedError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserCreateRequest, UserLoginRequest


def register_user(db: Session, payload: UserCreateRequest) -> User:
    """
    신규 사용자를 등록합니다.
    """
    existing_user = db.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none()

    if existing_user is not None:
        raise DuplicateEmailError(payload.email)

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        gender=payload.gender.value,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateEmailError(payload.email)

    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: UserLoginRequest) -> tuple[User, str]:
    """
    사용자를 인증하고 액세스 토큰을 발급합니다.
    """
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise InvalidCredentialsError()

    token = create_access_token(
        subject=user.user_id,
        expires_delta=timedelta(days=1),
        claims={
            "email": user.email,
        },
    )

    return user, token


def get_user_from_token(db: Session, token: str) -> User:
    """액세스 토큰으로 현재 사용자를 조회합니다."""
    payload = decode_access_token(token)
    subject = payload.get("sub")
    
    if subject is None:
        raise UnauthorizedError()

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise UnauthorizedError() from None

    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError()

    return user


