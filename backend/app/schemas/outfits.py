"""
코디 관련 스키마 정의.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# 코디 좋아요 추가 응답 데이터 스키마 1
class AddFavoriteResponseData(BaseModel):
    outfit_id: int = Field(alias="outfitId")
    is_favorited: bool = Field(alias="isFavorited")
    favorited_at: datetime = Field(alias="favoritedAt")

    class Config:
        populate_by_name = True


# 코디 좋아요 추가 응답 데이터 스키마 2
class AddFavoriteResponse(BaseModel):
    success: bool = True
    data: AddFavoriteResponseData


# 코디 좋아요 취소 응답 데이터 스키마 1
class RemoveFavoriteResponseData(BaseModel):
    outfit_id: int = Field(alias="outfitId")
    is_favorited: bool = Field(alias="isFavorited")
    unfavorited_at: datetime = Field(alias="unfavoritedAt")

    class Config:
        populate_by_name = True


# 코디 좋아요 취소 응답 데이터 스키마 2
class RemoveFavoriteResponse(BaseModel):
    success: bool = True
    data: RemoveFavoriteResponseData


# 코디 스킵 기록 응답 데이터 스키마 1
class SkipOutfitResponseData(BaseModel):
    outfit_id: int = Field(alias="outfitId")
    is_skipped: bool = Field(alias="isSkipped", default=True)
    skipped_at: datetime = Field(alias="skippedAt")

    class Config:
        populate_by_name = True


# 코디 스킵 기록 응답 데이터 스키마 2
class SkipOutfitResponse(BaseModel):
    success: bool = True
    data: SkipOutfitResponseData


# 코디 조회 로그 기록 요청 스키마
class RecordViewLogRequest(BaseModel):
    duration_seconds: int = Field(alias="durationSeconds", ge=0, description="조회 시간 (초)")

    class Config:
        populate_by_name = True


# 코디 조회 로그 기록 응답 데이터 스키마 1
class RecordViewLogResponseData(BaseModel):
    message: str
    recorded_at: datetime = Field(alias="recordedAt")

    class Config:
        populate_by_name = True


# 코디 조회 로그 기록 응답 데이터 스키마 2
class RecordViewLogResponse(BaseModel):
    success: bool = True
    data: RecordViewLogResponseData

