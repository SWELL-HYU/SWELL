"""
UserEmbedding 모델.
Warm-Start 추천을 위한 유저 임베딩 벡터를 저장합니다.
"""

from sqlalchemy import BigInteger, Column, DateTime, String, ForeignKey
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.database import Base


class UserEmbedding(Base):
    """`user_embeddings` 테이블 모델."""

    __tablename__ = "user_embeddings"

    user_id = Column(
        BigInteger, 
        ForeignKey("users.user_id", ondelete="CASCADE"), 
        primary_key=True
    )
    model_version = Column(
        String(50), 
        primary_key=True, 
        default="neumf_v1",
        comment="모델 버전 (e.g. 'neumf_v1', 'neumf_v2')"
    )
    vector = Column(
        Vector(512), 
        nullable=False,
        comment="Learned user latent vector (512 dims)"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"UserEmbedding(user_id={self.user_id}, model={self.model_version})"
