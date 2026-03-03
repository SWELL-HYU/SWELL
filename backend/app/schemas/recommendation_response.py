"""
코디 추천 관련 응답 스키마 정의.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginationPayload


class OutfitItemPayload(BaseModel):
    """코디에 포함된 아이템 페이로드."""

    id: int
    category: str
    brand: Optional[str] = None
    name: str
    price: Optional[int] = None
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    purchase_url: Optional[str] = Field(default=None, alias="purchaseUrl")
    is_saved: bool = Field(alias="isSaved")

    class Config:
        populate_by_name = True


class OutfitPayload(BaseModel):
    """코디 페이로드."""

    id: int
    image_url: str = Field(alias="imageUrl")
    gender: str
    season: str
    style: str
    description: str
    is_favorited: bool = Field(alias="isFavorited")
    llm_message: Optional[str] = Field(default=None, alias="llmMessage")
    items: List[OutfitItemPayload]
    created_at: datetime = Field(alias="createdAt")

    class Config:
        populate_by_name = True


class RecommendationsResponseData(BaseModel):
    """코디 추천 응답 데이터."""

    outfits: List[OutfitPayload]
    pagination: PaginationPayload


class RecommendationsResponse(BaseModel):
    """코디 추천 응답 래퍼."""

    success: bool = True
    data: RecommendationsResponseData

