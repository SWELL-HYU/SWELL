"""
코디 이미지(CoordiImage) 엔티티 모델.

코디에 매핑되는 대표 및 상세 이미지를 관리한다.
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class CoordiImage(Base):
    """`Coordi_Images` 테이블 모델."""

    __tablename__ = "coordi_images"

    image_id = Column(BigInteger, primary_key=True, autoincrement=True)
    coordi_id = Column(
        BigInteger,
        ForeignKey("coordis.coordi_id", ondelete="CASCADE"),
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

    __table_args__ = (Index("idx_coordi_images_coordi", "coordi_id", "is_main"),)

    coordi = relationship(
        "Coordi",
        back_populates="images",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"CoordiImage(image_id={self.image_id}, coordi_id={self.coordi_id})"

