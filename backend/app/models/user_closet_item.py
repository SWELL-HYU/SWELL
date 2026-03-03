"""
사용자 가상 옷장(UserClosetItem) 엔티티 모델.

사용자가 저장한 아이템 목록을 표현한다.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class UserClosetItem(Base):
    """`User_Closet_Items` 테이블 모델."""

    __tablename__ = "user_closet_items"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "item_id"),
        Index("idx_user_closet_items_item", "item_id"),
    )

    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        BigInteger,
        ForeignKey("items.item_id", ondelete="CASCADE"),
        nullable=False,
    )
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User",
        back_populates="closet_items",
        passive_deletes=True,
    )
    item = relationship(
        "Item",
        back_populates="closet_items",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"UserClosetItem(user_id={self.user_id}, item_id={self.item_id})"

