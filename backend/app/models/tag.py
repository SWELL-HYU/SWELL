"""
태그(Tag) 엔티티 모델.

`Tags` 테이블은 사용자 선호 태그 목록을 관리한다.
"""

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Tag(Base):
    """`Tags` 테이블 모델."""

    __tablename__ = "tags"

    tag_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="태그 이름 (예: #캐주얼)",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 종속 엔티티들과의 양방향 관계 설정
    user_preferred_tags = relationship(
        "UserPreferredTag",
        back_populates="tag",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Tag(tag_id={self.tag_id}, name={self.name})"

