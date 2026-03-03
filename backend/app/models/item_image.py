"""
아이템 이미지(ItemImage) 엔티티 모델.

상품의 썸네일 및 상세 이미지 정보를 보관한다.
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ItemImage(Base):
    """`Item_Images` 테이블 모델."""

    __tablename__ = "item_images"

    image_id = Column(BigInteger, primary_key=True, autoincrement=True)
    item_id = Column(
        BigInteger,
        ForeignKey("items.item_id", ondelete="CASCADE"),
        nullable=False,
    )
    image_url = Column(String(1024), nullable=False)
    is_main = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="대표 썸네일 여부",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_item_images_item", "item_id", "is_main"),)

    item = relationship(
        "Item",
        back_populates="images",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"ItemImage(image_id={self.image_id}, item_id={self.item_id})"

