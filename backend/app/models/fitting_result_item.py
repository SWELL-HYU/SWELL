"""
가상 피팅 결과-아이템 매핑(FittingResultItem) 엔티티 모델.

하나의 가상 피팅 결과에 연결된 여러 상품을 N:M 관계로 저장한다.
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Index, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class FittingResultItem(Base):
    """`Fitting_Result_Items` 테이블 모델."""

    __tablename__ = "fitting_result_items"
    __table_args__ = (
        PrimaryKeyConstraint("fitting_id", "item_id"),
        Index("idx_fitting_result_items_item", "item_id"),
    )

    fitting_id = Column(
        BigInteger,
        ForeignKey("fitting_results.fitting_id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        BigInteger,
        ForeignKey("items.item_id", ondelete="CASCADE"),
        nullable=False,
    )

    fitting_result = relationship(
        "FittingResult",
        back_populates="fitting_result_items",
        passive_deletes=True,
    )
    item = relationship(
        "Item",
        back_populates="fitting_result_items",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"FittingResultItem(fitting_id={self.fitting_id}, item_id={self.item_id})"


