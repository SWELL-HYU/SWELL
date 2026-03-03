"""
인증 관련 API 라우터.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token, extract_bearer_token
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginResponse,
    LoginResponseData,
    LogoutResponse,
    SignupResponse,
    SignupResponseData,
    UserCreateRequest,
    UserLoginRequest,
)
from app.schemas.users import (
    MeResponse,
    MeResponseData,
    PreferredCoordiPayload,
    PreferredTagPayload,
    UserPayload,
)
from app.services.auth_service import authenticate_user, get_user_from_token, register_user

# 인증 API 라우터 (접두사: /auth)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _build_user_payload(user: User) -> UserPayload:
    """
    사용자 데이터베이스 객체를 API 응답용 페이로드(UserPayload)로 변환합니다.
    """

    # 프로필 이미지 URL 추출
    profile_image_url = (
        user.images[0].image_url if getattr(user, "images", []) else None
    )

    # 선호 태그 추출
    preferred_tags = None
    if user.preferred_tags:
        preferred_tags = [
            PreferredTagPayload(id=tag.tag.tag_id, name=tag.tag.name)
            for tag in user.preferred_tags
        ]

    # 선호 코디 추출
    preferred_coordis = None
    preference_interactions = [
        interaction for interaction in user.coordi_interactions 
        if interaction.action_type == 'preference'
    ]
    if preference_interactions:
        preferred_coordis = []
        for interaction in preference_interactions:
            coordi = interaction.coordi
            # 메인 이미지 찾기 (is_main=True 우선, 없으면 첫 번째 이미지)
            main_image = next(
                (img for img in coordi.images if img.is_main),
                coordi.images[0] if coordi.images else None
            )
            main_image_url = main_image.image_url if main_image else None
            
            preferred_coordis.append(
                PreferredCoordiPayload(
                    id=coordi.coordi_id,
                    style=coordi.style,
                    season=coordi.season,
                    gender=coordi.gender,
                    description=coordi.description,
                    mainImageUrl=main_image_url,
                    preferredAt=interaction.interacted_at
                )
    )

    # 사용자 페이로드 생성
    return UserPayload.model_validate(
        {
            "id": user.user_id,
            "email": user.email,
            "name": user.name,
            "gender": user.gender,
            "profileImageUrl": profile_image_url,
            "preferredTags": preferred_tags,
            "preferredCoordis": preferred_coordis,
            "hasCompletedOnboarding": user.has_completed_onboarding,
            "createdAt": user.created_at,
        },
        from_attributes=False,
    )

@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=SignupResponse,
)
def signup(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
) -> SignupResponse:
    """
    신규 사용자 회원가입 처리를 수행합니다.
    
    데이터베이스에 새 사용자를 등록하고, 변환된 사용자 정보와 인증/가입 관련 응답을 반환합니다.
    """
    # 사용자 데이터 저장
    user = register_user(db, payload)

    # API 응답용 페이로드 생성
    user_payload = _build_user_payload(user)
    return SignupResponse(
        data=SignupResponseData(
            user=user_payload,
        )
    )


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=LoginResponse,
)
def login(
    payload: UserLoginRequest, 
    db: Session = Depends(get_db)
) -> LoginResponse:
    """
    기존 사용자의 로그인을 처리하고 JWT 토큰을 발급합니다.
    
    이메일과 비밀번호를 검증한 뒤, 유효할 경우 새로운 액세스 토큰(JWT)과 사용자 정보를 반환합니다.
    """
    user, token = authenticate_user(db, payload)
    user_payload = _build_user_payload(user)
    return LoginResponse(
        data=LoginResponseData(
            user=user_payload,
            token=token,
        )
    )

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    response_model=LogoutResponse,
)
def logout(authorization: str = Header(...)) -> LogoutResponse:
    """
    사용자의 로그아웃을 처리합니다.
    
    요청 헤더에 포함된 JWT 토큰을 단순히 검증하여 세션 종료 여부를 확인합니다.
    (실제 무효화 처리는 클라이언트나 Redis 등 추가 아키텍처에서 관리할 수 있습니다.)
    """
    # Authorization 헤더 검증 및 토큰 디코딩
    token = extract_bearer_token(authorization)
    decode_access_token(token)
    return LogoutResponse(
        success=True,
        message="로그아웃되었습니다",
    )

@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=MeResponse,
)
def read_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> MeResponse:
    """
    현재 로그인된 사용자의 프로필 정보를 조회합니다.
    
    헤더의 유효한 토큰을 기반으로 데이터베이스에서 사용자를 매핑하여 반환합니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)
    user_payload = _build_user_payload(user)
    return MeResponse(
        data=MeResponseData(
            user=user_payload,
        )
    )


