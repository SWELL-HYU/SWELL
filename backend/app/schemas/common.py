"""
공통 스키마 정의.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationPayload(BaseModel):
    """페이지네이션 정보 페이로드."""

    current_page: int = Field(alias="currentPage")
    total_pages: int = Field(alias="totalPages")
    total_items: int = Field(alias="totalItems")
    has_next: bool = Field(alias="hasNext")
    has_prev: bool = Field(alias="hasPrev")

    class Config:
        populate_by_name = True

