"""
Warm-Start 추천 서비스.
NeMF 모델을 로드하고, DB에 저장된 최신 유저 임베딩을 반영하여 개인화된 추천을 제공합니다.
"""

import os
import torch
import numpy as np
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.ml.neumf_model import NeMF
from app.models.user_embedding import UserEmbedding
from app.models.item_embedding import ItemEmbedding
from app.models.user import User
from app.models.coordi import Coordi

logger = logging.getLogger(__name__)

class WarmRecommendationService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WarmRecommendationService, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_path: Optional[str] = None):
        # Singleton 초기화 방지
        if hasattr(self, "model"):
            return

        self.device = 'cpu'  # 추론은 CPU로 충분함
        self.model: Optional[NeMF] = None
        self.user_id_to_index = {}
        self.item_id_to_index = {}
        self.index_to_item_id = {}
        self.is_ready = False

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str):
        """모델 체크포인트를 로드합니다."""
        if not os.path.exists(model_path):
            logger.warning(f"Model file not found at {os.path.abspath(model_path)}")
            return

        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            
            # 메타데이터 로드
            self.user_id_to_index = checkpoint['user_id_to_index']
            self.item_id_to_index = checkpoint['item_id_to_index']
            
            # 역매핑 생성 (Index -> Item ID)
            self.index_to_item_id = {v: k for k, v in self.item_id_to_index.items()}
            
            num_users = checkpoint['num_users']
            num_items = checkpoint['num_items']
            embedding_dim = checkpoint['embedding_dim']
            hidden_dims = checkpoint.get('hidden_dims', [128])
            
            # 모델 초기화
            self.model = NeMF(
                num_users=num_users,
                num_items=num_items,
                embedding_dim=embedding_dim,
                hidden_dims=hidden_dims
            ).to(self.device)
            
            # 가중치 로드
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            self.is_ready = True
            logger.info(f"Warm model loaded successfully from {model_path}")
            
        except Exception as e:
            logger.error(f"Error loading warm model: {e}")
            self.is_ready = False

    def recommend(
        self, 
        db: Session, 
        user_id: int, 
        page: int = 1,
        limit: int = 20
    ) -> tuple[List[int], int]:
        """
        사용자에게 코디를 추천합니다. (Only Day Model)
        
        Args:
            db: DB 세션
            user_id: 사용자 ID (DB PK)
            page: 페이지 번호 (1부터 시작)
            limit: 추천 개수
            
        Returns:
            tuple[List[int], int]: (추천된 coordi_id 리스트, 전체 아이템 수)
        """
        if not self.is_ready or not self.model:
            return [], 0

        user_id_str = str(user_id)
        
        # 1. 모델 인덱스 확인
        if user_id_str not in self.user_id_to_index:
            return [], 0
            
        user_idx = self.user_id_to_index[user_id_str]

        # 2. 동적 임베딩 주입 (Day Embedding ONLY)
        # 무조건 'day_v1' 임베딩만 사용
        user_embedding_record = db.execute(
            select(UserEmbedding).where(
                UserEmbedding.user_id == user_id,
                UserEmbedding.model_version == 'day_v1'
            )
        ).scalar_one_or_none()

        # Day 임베딩이 없으면 Warm Start 대상이 아님 -> 빈 리스트 반환 (Cold Start 로직으로 넘어감)
        # 수정: 모델에 유저가 존재한다면(위에서 체크함), Day 임베딩이 없어도 모델 원래 가중치(Night v1)로 추천 가능함.
        if not user_embedding_record or user_embedding_record.vector is None:
            logger.info(f"Day embedding not found for user {user_id}. Using internal model weights (Night v1).")
        else:
            try:
                vector_data = np.array(user_embedding_record.vector, dtype=np.float32)
                with torch.no_grad():
                        self.model.user_embedding.weight.data[user_idx] = torch.from_numpy(vector_data)
            except Exception as e:
                logger.error(f"Error injecting user embedding: {e}")
                # 주입 실패 시에도 모델 원래 가중치 사용
                pass

        # 3. 추론
        num_items = self.model.item_embedding.num_embeddings
        
        user_tensor = torch.tensor([user_idx] * num_items, dtype=torch.long).to(self.device)
        item_tensor = torch.tensor(list(range(num_items)), dtype=torch.long).to(self.device)
        
        with torch.no_grad():
            scores = self.model(user_tensor, item_tensor).numpy()

        # [Filter 0] Gender Filtering (성별 필터링)
        # 사용자의 성별을 가져옴
        user = db.get(User, user_id)
        if user and user.gender:
            # 해당 성별에 맞는 Coordi ID만 조회
            valid_gender_coordis = db.execute(
                select(Coordi.coordi_id).where(Coordi.gender == user.gender)
            ).scalars().all()
            
            # 모델 인덱스로 변환
            valid_indices = []
            for cid in valid_gender_coordis:
                cid_str = str(cid)
                if cid_str in self.item_id_to_index:
                    valid_indices.append(self.item_id_to_index[cid_str])
            
            # numpy 마스킹: 유효하지 않은 인덱스(성별 불일치)는 -inf 처리
            # 전체 아이템에 대해 True(마스킹 대상)로 초기화
            gender_mask = np.ones(num_items, dtype=bool)
            if valid_indices:
                gender_mask[valid_indices] = False  # 유효한 인덱스만 False(마스킹 해제)
            
            scores[gender_mask] = -np.inf
            
        # [Filter] 이미 상호작용한 아이템 제외 (Seen Items filtering)
        # DB에서 사용자가 인터랙션한 coordi_id 조회
        from app.models.user_coordi_interaction import UserCoordiInteraction
        
        seen_interactions = db.execute(
            select(UserCoordiInteraction.coordi_id).where(
                UserCoordiInteraction.user_id == user_id
            )
        ).scalars().all()
        
        seen_indices = []
        for coordi_id in seen_interactions:
            cid_str = str(coordi_id)
            if cid_str in self.item_id_to_index:
                seen_indices.append(self.item_id_to_index[cid_str])
        
        # 이미 본 아이템의 점수를 -무한대로 설정하여 추천에서 제외
        if seen_indices:
            scores[seen_indices] = -np.inf

        # 4. Top-K 추출 (페이지네이션)
        offset = (page - 1) * limit
        sorted_indices = np.argsort(scores)[::-1]
        
        # 전체 유효 아이템 수 (이미 본 것 제외한 유효 아이템 수로 조정 가능하나, 
        # 여기서는 min(-inf) 체크 등으로 필터링된 개수를 뺄 수도 있음. 
        # 일단 전체 풀 사이즈 유지하거나, seen을 뺀 갯수로 할 수 있음)
        # -inf인 것들은 맨 뒤로 갔을 것임.
        
        # 유효한 추천(점수가 -inf가 아닌) 개수 카운트
        valid_count = np.count_nonzero(scores != -np.inf)
        total_items = valid_count
        
        # 슬라이싱 (유효 범위 내에서)
        if offset >= total_items:
            return [], total_items
            
        top_indices = sorted_indices[offset : offset + limit]
        
        # 5. DB ID로 변환
        recommended_ids = []
        for idx in top_indices:
            # 점수가 -inf면 추천 안 함 (혹시 모를 경계값 처리)
            if scores[idx] == -np.inf:
                continue
                
            item_id_str = self.index_to_item_id.get(idx)
            if item_id_str and item_id_str.isdigit():
                recommended_ids.append(int(item_id_str))
                
        return recommended_ids, total_items

# 전역 인스턴스 (lazy loading을 위해 None으로 시작)
_warm_service_instance = None

def get_warm_recommendation_service(model_path: str = None) -> WarmRecommendationService:
    global _warm_service_instance
    if _warm_service_instance is None:
        if model_path is None:
            # 현재 파일 위치: backend/app/services/warm_recommendation_service.py
            # 목표 파일 위치: backend/data/model_artifacts/neumf_night_model.pth
            
            current_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/app/services
            app_dir = os.path.dirname(current_dir) # .../backend/app
            backend_dir = os.path.dirname(app_dir) # .../backend
            
            # 절대 경로 생성
            model_path = os.path.join(backend_dir, "data", "model_artifacts", "neumf_night_model.pth")
            
        _warm_service_instance = WarmRecommendationService(model_path)
    return _warm_service_instance
