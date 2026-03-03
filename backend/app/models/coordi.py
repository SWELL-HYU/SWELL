"""
코디(Coordi) 엔티티 모델.

`Coordis` 테이블은 시즌, 스타일 정보와 자유 텍스트 설명을 보관한다.
"""

from sqlalchemy import BigInteger, Column, DateTime, Enum, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.database import Base


class Coordi(Base):
    """`Coordis` 테이블 모델."""

    __tablename__ = "coordis"

    coordi_id = Column(BigInteger, primary_key=True, autoincrement=True)
    season = Column(
        Enum("spring", "summer", "fall", "winter", name="coordi_season_enum")
    )
    style = Column(
        Enum("casual", "street", "sporty", "minimal", name="coordi_style_enum")
    )
    gender = Column(
        Enum("male", "female", name="coordi_gender_enum"),
        comment="코디 대상 성별",
    )
    description = Column(Text, comment="태그 포함 설명 문구")
    description_embedding = Column(
        Vector(512),
        nullable=True,
        comment="Description embedding vector for semantic search (512 dimensions)"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_coordis_season_style", "season", "style"),
        Index("idx_coordis_style", "style"),
    )

    images = relationship(
        "CoordiImage",
        back_populates="coordi",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    coordi_items = relationship(
        "CoordiItem",
        back_populates="coordi",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    interactions = relationship(
        "UserCoordiInteraction",
        back_populates="coordi",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    view_logs = relationship(
        "UserCoordiViewLog",
        back_populates="coordi",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Coordi(coordi_id={self.coordi_id}, style={self.style})"

