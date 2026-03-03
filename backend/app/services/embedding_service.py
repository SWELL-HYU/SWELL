"""
Description embedding 생성 서비스

sentence-transformers/distiluse-base-multilingual-cased-v2 모델을 사용하여
텍스트를 512차원 벡터로 변환합니다.
"""

from typing import List

from sentence_transformers import SentenceTransformer

# TODO: 데이터주입이 끝나면 모두 주석처리
from functools import lru_cache

class EmbeddingService:
    """Description embedding을 생성하는 서비스 (Singleton)"""
    
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            # 모델 초기화 (한 번만 실행)
            model_name = "sentence-transformers/distiluse-base-multilingual-cased-v2"
            cls._model = SentenceTransformer(model_name)
        return cls._instance

    def __init__(self):
        """
        Embedding 모델 초기화
        
        모델: distiluse-base-multilingual-cased-v2
        차원: 512
        """
        # __init__은 매번 호출되지만 모델은 __new__에서 한 번만 로드됨
        self.dimension = 512
    
    @lru_cache(maxsize=1000)
    def generate_embedding(self, text: str) -> List[float]:
        """
        텍스트를 embedding 벡터로 변환
        
        Args:
            text: 변환할 텍스트
            
        Returns:
            embedding 벡터 (512차원 리스트)
        """
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        try:
            # _model 클래스 변수 사용
            embedding = self._model.encode(
                text,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            return embedding.tolist()
        except Exception as e:
            print(f"Embedding 생성 실패: {e}")
            return [0.0] * self.dimension

