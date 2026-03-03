"""
ItemEmbedding 모델.
Warm-Start 추천을 위한 아이템(코디) 임베딩 벡터를 저장합니다.
"""

from sqlalchemy import BigInteger, Column, DateTime, String, ForeignKey
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.database import Base


class ItemEmbedding(Base):
    """`item_embeddings` 테이블 모델."""

    __tablename__ = "item_embeddings"

    coordi_id = Column(
        BigInteger, 
        ForeignKey("coordis.coordi_id", ondelete="CASCADE"), 
        primary_key=True
    )
    model_version = Column(
        String(50), 
        primary_key=True, 
        default="neumf_v1",
        comment="모델 버전 (e.g. 'neumf_v1')"
    )
    vector = Column(
        Vector(512), 
        nullable=False,
        comment="Learned item latent vector (512 dims)"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"ItemEmbedding(coordi_id={self.coordi_id}, model={self.model_version})"
