"""
보안 관련 유틸리티 함수 모음.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.core.exceptions import UnauthorizedError


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
PASSWORD_SALT = os.getenv("PASSWORD_SALT", "")


def hash_password(password: str) -> str:
    """
    비밀번호를 SHA-256으로 해싱하여 반환합니다. 
    `PASSWORD_SALT` 환경변수를 사용하여 간단한 솔팅을 추가합니다.
    """
    digest = hashlib.sha256()
    digest.update(f"{PASSWORD_SALT}{password}".encode("utf-8"))
    return digest.hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """입력된 비밀번호가 저장된 해시와 일치하는지 검증합니다."""
    return hmac.compare_digest(hash_password(password), hashed_password)


def create_access_token(
    *,
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    JWT 액세스 토큰을 생성합니다.

    Args:
        subject: 토큰의 주체 (예: 사용자 ID)
        expires_delta: 토큰 만료 시간. 미지정 시 기본 설정 60분 사용.
        claims: 토큰 페이로드에 포함할 추가 정보 딕셔너리
        
    Returns:
        str: 생성된 JWT 문자열
    """
    to_encode: Dict[str, Any] = {}

    if claims:
        to_encode.update(claims)

    to_encode.update({"sub": str(subject)})

    expire_delta = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_at = datetime.now(timezone.utc) + expire_delta
    to_encode["exp"] = expire_at

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    JWT 액세스 토큰을 복호화하고 검증합니다.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError(message="토큰이 만료되었습니다") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(message="유효하지 않은 토큰입니다") from exc

    return payload


def extract_bearer_token(authorization_header: str) -> str:
    """
    Authorization 헤더에서 Bearer 토큰을 추출합니다.
    """
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError(message="유효하지 않은 토큰 형식입니다")
    return token


