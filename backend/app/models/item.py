"""
상품(Item) 엔티티 모델.

`Items` 테이블은 쇼핑 상품 메타데이터와 브랜드 문자열을 보관한다.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Item(Base):
    """`Items` 테이블 모델."""

    __tablename__ = "items"

    item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    item_name = Column(String(255), nullable=False)
    category = Column(
        Enum("top", "bottom", "outer", name="item_category_enum"),
        nullable=False,
    )
    brand_name_ko = Column(String(100))
    price = Column(Numeric(10, 2))
    purchase_url = Column(String(1024))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_items_category", "category"),
        Index("idx_items_brand_ko", "brand_name_ko"),
    )

    # 종속 엔티티들과의 관계
    fitting_results = relationship(
        "FittingResult",
        secondary="fitting_result_items",
        back_populates="items",
        passive_deletes=True,
    )
    fitting_result_items = relationship(
        "FittingResultItem",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    images = relationship(
        "ItemImage",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    coordi_items = relationship(
        "CoordiItem",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    closet_items = relationship(
        "UserClosetItem",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Item(item_id={self.item_id}, item_name={self.item_name})"

