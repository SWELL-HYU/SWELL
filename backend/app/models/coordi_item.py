"""
코디-아이템 매핑(CoordiItem) 엔티티 모델.

하나의 코디를 구성하는 상품 정보를 N:M 관계로 저장한다.
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Index, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class CoordiItem(Base):
    """`Coordi_Items` 테이블 모델."""

    __tablename__ = "coordi_items"
    __table_args__ = (
        PrimaryKeyConstraint("coordi_id", "item_id"),
        Index("idx_coordi_items_item", "item_id"),
    )

    coordi_id = Column(
        BigInteger,
        ForeignKey("coordis.coordi_id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        BigInteger,
        ForeignKey("items.item_id", ondelete="CASCADE"),
        nullable=False,
    )

    coordi = relationship(
        "Coordi",
        back_populates="coordi_items",
        passive_deletes=True,
    )
    item = relationship(
        "Item",
        back_populates="coordi_items",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"CoordiItem(coordi_id={self.coordi_id}, item_id={self.item_id})"

