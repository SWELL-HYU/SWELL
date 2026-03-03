"""
사용자-코디 상호작용(UserCoordiInteraction) 엔티티 모델.

스와이프와 같은 명시적 피드백을 저장한다.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class UserCoordiInteraction(Base):
    """`User_Coordi_Interactions` 테이블 모델."""

    __tablename__ = "user_coordi_interactions"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "coordi_id"),
        Index("idx_user_coordi_interactions_coordi", "coordi_id", "action_type"),
    )

    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    coordi_id = Column(
        BigInteger,
        ForeignKey("coordis.coordi_id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type = Column(
        Enum("like", "skip", "preference", name="coordi_action_enum"),
        nullable=False,
    )
    is_trained = Column(Boolean, default=False, nullable=False, server_default="false")
    interacted_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User",
        back_populates="coordi_interactions",
        passive_deletes=True,
    )
    coordi = relationship(
        "Coordi",
        back_populates="interactions",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"UserCoordiInteraction(user_id={self.user_id}, coordi_id={self.coordi_id}, action_type={self.action_type})"

