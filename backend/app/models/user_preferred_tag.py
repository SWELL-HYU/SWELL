"""
사용자 선호 태그(UserPreferredTag) 엔티티 모델.

사용자와 선호 태그의 N:M 관계를 표현한다.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class UserPreferredTag(Base):
    """`User_Preferred_Tags` 테이블 모델."""

    __tablename__ = "user_preferred_tags"
    __table_args__ = (PrimaryKeyConstraint("user_id", "tag_id"),)

    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id = Column(
        BigInteger,
        ForeignKey("tags.tag_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User",
        back_populates="preferred_tags",
        passive_deletes=True,
    )
    tag = relationship(
        "Tag",
        back_populates="user_preferred_tags",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"UserPreferredTag(user_id={self.user_id}, tag_id={self.tag_id})"

