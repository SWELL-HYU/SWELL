"""
사용자 코디 조회 로그(UserCoordiViewLog) 엔티티 모델.

코디 상세 화면에서의 체류 시간을 기록한다.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class UserCoordiViewLog(Base):
    """`User_Coordi_View_Logs` 테이블 모델."""

    __tablename__ = "user_coordi_view_logs"
    __table_args__ = (
        Index("idx_user_coordi", "user_id", "coordi_id"),
        Index("idx_coordi_view_logs_coordi_time", "coordi_id", "view_started_at"),
    )

    log_id = Column(BigInteger, autoincrement=True, primary_key=True)
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
    view_started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="조회 시작 시간",
    )
    duration_seconds = Column(
        Integer,
        nullable=False,
        comment="머무른 시간 (초)",
    )

    user = relationship(
        "User",
        back_populates="coordi_view_logs",
        passive_deletes=True,
    )
    coordi = relationship(
        "Coordi",
        back_populates="view_logs",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"UserCoordiViewLog(log_id={self.log_id}, user_id={self.user_id}, coordi_id={self.coordi_id})"

