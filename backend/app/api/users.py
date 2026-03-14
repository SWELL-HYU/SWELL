"""
사용자 관련 API 라우터.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, status, UploadFile
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, extract_bearer_token
from app.db.database import get_db
from app.core.storage import get_storage_service
from app.schemas.users import (
    PreferencesOptionsResponse,
    PreferencesOptionsResponseData,
    PreferencesResponse,
    PreferencesResponseData,
    PreferencesResponseUser,
    ProfilePhotoDeleteResponse,
    ProfilePhotoDeleteResponseData,
    ProfilePhotoUploadResponse,
    ProfilePhotoUploadResponseData,
    UserPreferencesRequest,
)
from app.services.auth_service import get_user_from_token
from app.services.users_service import (
    delete_profile_photo,
    get_preferences_options_data,
    set_user_preferences,
    upload_profile_photo,
)

# 사용자 관련 API 라우터 (접두사: /users)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/preferences/options",
    status_code=status.HTTP_200_OK,
    response_model=PreferencesOptionsResponse,
)
def get_preferences_options(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> PreferencesOptionsResponse:
    """
    온보딩 시나리오 등에서 사용자가 선택할 수 있는 선호도 데이터(해시태그, 샘플 코디 등)를 반환합니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)

    hashtags, sample_outfits = get_preferences_options_data(db, user.gender)

    return PreferencesOptionsResponse(
        data=PreferencesOptionsResponseData(
            hashtags=hashtags,
            sampleOutfits=sample_outfits,
        )
    )


@router.post(
    "/preferences",
    status_code=status.HTTP_200_OK,
    response_model=PreferencesResponse,
)
def set_preferences(
    payload: UserPreferencesRequest,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> PreferencesResponse:
    """
    사용자의 스타일 및 해시태그 취향을 저장(갱신)합니다.
    
    - 완료 시 사용자의 온보딩 완료 상태가 업데이트됩니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)

    updated_user = set_user_preferences(db, user.user_id, payload)

    return PreferencesResponse(
        data=PreferencesResponseData(
            message="선호도가 저장되었습니다",
            user=PreferencesResponseUser(
                id=updated_user.user_id,
                hasCompletedOnboarding=updated_user.has_completed_onboarding,
            ),
        )
    )


@router.post(
    "/profile-photo",
    status_code=status.HTTP_200_OK,
    response_model=ProfilePhotoUploadResponse,
)
async def upload_profile_photo_endpoint(
    photo: UploadFile = File(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> ProfilePhotoUploadResponse:
    """
    로그인한 사용자의 프로필 이미지를 업로드(저장)합니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)

    user_image = await upload_profile_photo(db, user.user_id, photo)

    storage_service = get_storage_service()
    photo_presigned_url = await storage_service.get_presigned_url(
        user_image.image_url, expiration=3600
    )

    return ProfilePhotoUploadResponse(
        data=ProfilePhotoUploadResponseData(
            photoUrl=photo_presigned_url,
            createdAt=user_image.created_at,
        )
    )


@router.delete(
    "/profile-photo",
    status_code=status.HTTP_200_OK,
    response_model=ProfilePhotoDeleteResponse,
)
async def delete_profile_photo_endpoint(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> ProfilePhotoDeleteResponse:
    """
    로그인한 사용자의 프로필 이미지를 삭제합니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)

    deleted_at, had_photo = await delete_profile_photo(db, user.user_id)
    message = "사진이 삭제되었습니다" if had_photo else "삭제할 사진이 없습니다"

    return ProfilePhotoDeleteResponse(
        data=ProfilePhotoDeleteResponseData(
            message=message,
            deletedAt=deleted_at,
        )
    )

