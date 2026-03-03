"""
아이템 관련 비즈니스 로직.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ItemNotFoundError
from app.models.item import Item


def get_item_by_id(db: Session, item_id: int) -> Item:
    """아이템 상세 정보를 조회합니다."""
    item = (
        db.execute(
            select(Item)
            .options(selectinload(Item.images))
            .where(Item.item_id == item_id)
        )
        .scalars()
        .first()
    )

    if item is None:
        raise ItemNotFoundError()

    return item


