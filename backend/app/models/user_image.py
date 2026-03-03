"""
사용자 이미지(UserImage) 엔티티 모델.

가상 피팅이나 프로필에 사용되는 원본 사진 URL을 관리한다.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class UserImage(Base):
    """`User_Images` 테이블 모델."""

    __tablename__ = "user_images"

    image_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    image_url = Column(
        String(1024),
        nullable=False,
        comment="사용자의 전신 사진 URL",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_user_images_user", "user_id"),)

    user = relationship(
        "User",
        back_populates="images",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"UserImage(image_id={self.image_id}, user_id={self.user_id})"

