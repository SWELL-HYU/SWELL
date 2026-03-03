"""
가상 피팅 결과(FittingResult) 엔티티 모델.

사용자와 아이템의 조합으로 생성된 가상 피팅 수행 내역을 기록한다.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class FittingResult(Base):
    """`Fitting_Results` 테이블 모델."""

    __tablename__ = "fitting_results"

    fitting_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(
            "processing",
            "completed",
            "failed",
            "timeout",
            name="fitting_result_status_enum",
        ),
        nullable=False,
        server_default="processing",
        comment="피팅 작업 상태",
    )
    current_step = Column(
        Enum("top", "bottom", "outer", name="fitting_step_enum"),
        comment="현재 처리 단계 (processing 상태일 때)",
    )
    failed_step = Column(
        Enum("top", "bottom", "outer", name="fitting_step_enum"),
        comment="실패한 단계 (failed 상태일 때)",
    )
    llm_message = Column(Text, comment="LLM 평가 메시지")
    finished_at = Column(
        DateTime(timezone=True),
        comment="작업 완료/실패/타임아웃 시점 (status가 completed/failed/timeout일 때)",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_fitting_results_user", "user_id"),)

    user = relationship(
        "User",
        back_populates="fitting_results",
        passive_deletes=True,
    )
    items = relationship(
        "Item",
        secondary="fitting_result_items",
        back_populates="fitting_results",
        passive_deletes=True,
    )
    fitting_result_items = relationship(
        "FittingResultItem",
        back_populates="fitting_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    images = relationship(
        "FittingResultImage",
        back_populates="fitting_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"FittingResult(fitting_id={self.fitting_id}, user_id={self.user_id})"

