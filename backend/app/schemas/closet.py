"""
옷장 관련 스키마 정의.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginationPayload


# 옷장에 아이템 저장 요청 스키마
class SaveClosetItemRequest(BaseModel):
    item_id: int = Field(alias="itemId", description="아이템 고유 ID")

    class Config:
        populate_by_name = True


# 옷장 아이템 페이로드
class ClosetItemPayload(BaseModel):
    id: int
    category: str
    brand: Optional[str] = None
    name: str
    price: Optional[int] = None
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    purchase_url: Optional[str] = Field(default=None, alias="purchaseUrl")
    saved_at: datetime = Field(alias="savedAt")

    class Config:
        populate_by_name = True


# 카테고리별 개수 페이로드
class CategoryCountsPayload(BaseModel):
    top: int
    bottom: int
    outer: int

    class Config:
        populate_by_name = True


# 옷장에 아이템 저장 응답 데이터 스키마 1
class SaveClosetItemResponseData(BaseModel):
    message: str
    saved_at: datetime = Field(alias="savedAt")

    class Config:
        populate_by_name = True


# 옷장에 아이템 저장 응답 데이터 스키마 2
class SaveClosetItemResponse(BaseModel):
    success: bool = True
    data: SaveClosetItemResponseData


# 옷장에서 아이템 삭제 응답 데이터 스키마 1
class DeleteClosetItemResponseData(BaseModel):
    message: str
    deleted_at: datetime = Field(alias="deletedAt")

    class Config:
        populate_by_name = True


# 옷장에서 아이템 삭제 응답 데이터 스키마 2
class DeleteClosetItemResponse(BaseModel):
    success: bool = True
    data: DeleteClosetItemResponseData


# 옷장 아이템 목록 조회 응답 데이터 스키마 1
class ClosetItemsResponseData(BaseModel):
    items: List[ClosetItemPayload]
    pagination: PaginationPayload
    category_counts: CategoryCountsPayload = Field(alias="categoryCounts")

    class Config:
        populate_by_name = True


# 옷장 아이템 목록 조회 응답 데이터 스키마 2
class ClosetItemsResponse(BaseModel):
    success: bool = True
    data: ClosetItemsResponseData

