"""
아이템 관련 응답 스키마 정의.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# 아이템 상세 정보를 표현하는 페이로드 스키마
class ItemDetailPayload(BaseModel):
    id: str
    category: str
    brand: Optional[str] = None
    name: str
    price: Optional[float] = None
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    purchase_url: Optional[str] = Field(default=None, alias="purchaseUrl")
    created_at: datetime = Field(alias="createdAt")

    class Config:
        # populate_by_name=True: 내부 필드명을 유지하면서 JSON 직렬화 시 alias(camelCase)를 출력
        # orm_mode=True: SQLAlchemy ORM 객체를 Pydantic 모델로 바로 변환 가능
        populate_by_name = True
        orm_mode = True


# 아이템 상세 응답 본문 스키마
class ItemDetailResponseData(BaseModel):
    item: ItemDetailPayload


# 아이템 상세 응답 래퍼 스키마
class ItemDetailResponse(BaseModel):
    success: bool = True
    data: ItemDetailResponseData

