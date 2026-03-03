"""
가상 피팅 결과 이미지(FittingResultImage) 엔티티 모델.

AI가 생성한 가상 피팅 결과물을 저장하는 테이블을 표현한다.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class FittingResultImage(Base):
    """`Fitting_Result_Images` 테이블 모델."""

    __tablename__ = "fitting_result_images"

    image_id = Column(BigInteger, primary_key=True, autoincrement=True)
    fitting_id = Column(
        BigInteger,
        ForeignKey("fitting_results.fitting_id", ondelete="CASCADE"),
        nullable=False,
    )
    image_url = Column(
        String(1024),
        nullable=False,
        comment="AI가 생성한 피팅 결과물 URL",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_fitting_result_images_fitting", "fitting_id"),)

    fitting_result = relationship(
        "FittingResult",
        back_populates="images",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"FittingResultImage(image_id={self.image_id}, fitting_id={self.fitting_id})"

