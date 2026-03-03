"""
사용자 프로필 및 선호도 관련 스키마 정의.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserGender(str, Enum):
    male = "male"
    female = "female"


class PreferredTagPayload(BaseModel):
    """선호 태그 페이로드."""
    id: int
    name: str


class HashtagOptionPayload(BaseModel):
    """해시태그 옵션 페이로드."""
    id: int
    name: str


class SampleOutfitOptionPayload(BaseModel):
    """예시 코디 옵션 페이로드."""
    id: int
    image_url: str = Field(alias="imageUrl")
    style: Optional[str] = None
    season: Optional[str] = None

    class Config:
        populate_by_name = True


class PreferredCoordiPayload(BaseModel):
    """선호 코디 페이로드."""
    id: int
    style: Optional[str] = None
    season: Optional[str] = None
    gender: Optional[str] = None
    description: Optional[str] = None
    main_image_url: Optional[str] = Field(
        default=None,
        alias="mainImageUrl",
    )
    preferred_at: datetime = Field(alias="preferredAt")

    class Config:
        populate_by_name = True


class UserPayload(BaseModel):
    id: int = Field(alias="id")
    email: EmailStr
    name: str
    gender: Optional[UserGender] = None
    profile_image_url: Optional[str] = Field(
        default=None,
        alias="profileImageUrl",
    )
    preferred_tags: Optional[List[PreferredTagPayload]] = Field(
        default=None,
        alias="preferredTags",
    )
    preferred_coordis: Optional[List[PreferredCoordiPayload]] = Field(
        default=None,
        alias="preferredCoordis",
    )
    has_completed_onboarding: bool = Field(alias="hasCompletedOnboarding")
    created_at: datetime = Field(alias="createdAt")

    class Config:
        # populate_by_name=True: 내부 snake_case 필드명을 그대로 사용하면서, JSON 직렬화 시 alias(camelCase)를 출력 가능하도록 설정.
        # orm_mode=True: SQLAlchemy ORM 객체를 직접 Pydantic 모델로 변환할 수 있게 허용.
        populate_by_name = True
        orm_mode = True


# 사용자 선호도 설정 요청 스키마
class UserPreferencesRequest(BaseModel):
    hashtag_ids: List[int] = Field(alias="hashtagIds")
    sample_outfit_ids: List[int] = Field(alias="sampleOutfitIds")

    class Config:
        populate_by_name = True


# 내 정보 조회 응답 데이터 스키마 1
class MeResponseData(BaseModel):
    user: UserPayload


# 내 정보 조회 응답 데이터 스키마 2
class MeResponse(BaseModel):
    success: bool = True
    data: MeResponseData


# 선호도 설정 옵션 응답 데이터 스키마 1
class PreferencesOptionsResponseData(BaseModel):
    hashtags: List[HashtagOptionPayload]
    sample_outfits: List[SampleOutfitOptionPayload] = Field(alias="sampleOutfits")

    class Config:
        populate_by_name = True


# 선호도 설정 옵션 응답 데이터 스키마 2
class PreferencesOptionsResponse(BaseModel):
    success: bool = True
    data: PreferencesOptionsResponseData


# 선호도 설정 응답 데이터 스키마 1
class PreferencesResponseUser(BaseModel):
    """선호도 설정 응답의 사용자 정보."""
    id: int
    has_completed_onboarding: bool = Field(alias="hasCompletedOnboarding")

    class Config:
        populate_by_name = True


# 선호도 설정 응답 데이터 스키마 2
class PreferencesResponseData(BaseModel):
    message: str
    user: PreferencesResponseUser


# 선호도 설정 응답 데이터 스키마 3
class PreferencesResponse(BaseModel):
    success: bool = True
    data: PreferencesResponseData


# 프로필 사진 업로드 응답 데이터 스키마 1
class ProfilePhotoUploadResponseData(BaseModel):
    """프로필 사진 업로드 응답 데이터."""
    photo_url: str = Field(alias="photoUrl")
    created_at: datetime = Field(alias="createdAt")

    class Config:
        populate_by_name = True


# 프로필 사진 업로드 응답 데이터 스키마 2
class ProfilePhotoUploadResponse(BaseModel):
    success: bool = True
    data: ProfilePhotoUploadResponseData


# 프로필 사진 삭제 응답 데이터 스키마 1
class ProfilePhotoDeleteResponseData(BaseModel):
    """프로필 사진 삭제 응답 데이터."""
    message: str
    deleted_at: datetime = Field(alias="deletedAt")

    class Config:
        populate_by_name = True


# 프로필 사진 삭제 응답 데이터 스키마 2
class ProfilePhotoDeleteResponse(BaseModel):
    success: bool = True
    data: ProfilePhotoDeleteResponseData

