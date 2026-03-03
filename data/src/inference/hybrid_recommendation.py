"""
하이브리드 추천 시스템
밤 모델 임베딩(아이템 정보) + 낮 모델 임베딩(유저 정보)을 결합하여 추천합니다.
"""
import os
import sys
import torch
import numpy as np
from typing import List, Dict, Optional

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from data.src.models.neumf_model import NeMF
# user_embedding_utils 함수들을 인라인화
import json

# CSV 파일에서 임베딩 로드 함수
def load_item_embeddings_from_csv(csv_file: str) -> Dict[str, np.ndarray]:
    """
    CSV 파일에서 outfit_id별 임베딩을 로드합니다.
    
    Args:
        csv_file: CSV 파일 경로 (outfit_id, outfit_embedding 컬럼)
    
    Returns:
        Dict[str, np.ndarray]: outfit_id -> embedding 매핑
    """
    import csv
    import ast
    item_id_to_embedding = {}
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            outfit_id = str(row['outfit_id']).strip()
            embedding_str = row['outfit_embedding'].strip()
            
            # 문자열을 리스트로 변환
            try:
                embedding_list = ast.literal_eval(embedding_str)
                embedding = np.array(embedding_list, dtype=np.float32)
                
                # 정규화
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                
                item_id_to_embedding[outfit_id] = embedding
            except (ValueError, SyntaxError) as e:
                print(f"Warning: outfit_id {outfit_id}의 임베딩 파싱 실패: {e}")
                continue
    
    return item_id_to_embedding


class HybridRecommender:
    """
    하이브리드 추천 시스템
    - 밤 모델: 아이템 임베딩 (고정)
    - 낮 모델: 유저 임베딩 (동적, 있으면 사용, 없으면 밤 모델 사용)
    """
    
    def __init__(
        self,
        night_model_path: str,
        night_user_embedding_path: str,
        outfit_embeddings_csv: str,
        day_user_embedding_path: str,
        device: str = None
    ):
        """
        Args:
            night_model_path: 밤 모델 체크포인트 경로
            night_user_embedding_path: 밤 모델 유저 임베딩 경로
            outfit_embeddings_csv: Item Embedding CSV 파일 경로 (outfit_id, outfit_embedding)
            day_user_embedding_path: 낮 모델 유저 임베딩 경로
            device: 사용할 디바이스
        """
        self.night_model_path = night_model_path
        self.night_user_embedding_path = night_user_embedding_path
        self.outfit_embeddings_csv = outfit_embeddings_csv
        self.day_user_embedding_path = day_user_embedding_path
        
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device
        
        # 모델 로드
        self._load_model()
        
        # 임베딩 로드
        self._load_embeddings()
    
    def _load_model(self):
        """밤 모델을 로드합니다."""
        checkpoint = torch.load(self.night_model_path, map_location=self.device)
        
        self.user_id_to_index = checkpoint['user_id_to_index']
        self.item_id_to_index = checkpoint['item_id_to_index']
        self.num_users = checkpoint['num_users']
        self.num_items = checkpoint['num_items']
        self.embedding_dim = checkpoint['embedding_dim']
        self.hidden_dims = checkpoint.get('hidden_dims', [128, 64, 32])
        
        # 모델 초기화
        self.model = NeMF(
            num_users=self.num_users,
            num_items=self.num_items,
            embedding_dim=self.embedding_dim,
            hidden_dims=self.hidden_dims
        ).to(self.device)
        
        # 밤 모델 가중치 로드
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        # 평가 모드
        self.model.eval()
        
        print(f"밤 모델 로드 완료: {self.night_model_path}")
    
    def _load_embeddings(self):
        """임베딩을 로드합니다."""
        # Item Embedding 로드 (CSV 파일에서)
        print(f"Item Embedding 로드 (CSV 파일): {self.outfit_embeddings_csv}")
        item_id_to_embedding = load_item_embeddings_from_csv(self.outfit_embeddings_csv)
        
        # Item Embedding 설정
        item_embedding_set_count = 0
        with torch.no_grad():
            for item_id_str, item_idx in self.item_id_to_index.items():
                if item_id_str in item_id_to_embedding:
                    embedding = item_id_to_embedding[item_id_str]
                    
                    # 차원 맞춤
                    if embedding.shape[0] != self.embedding_dim:
                        if embedding.shape[0] > self.embedding_dim:
                            embedding = embedding[:self.embedding_dim]
                        else:
                            padding = np.zeros(self.embedding_dim - embedding.shape[0])
                            embedding = np.concatenate([embedding, padding])
                    
                    self.model.item_embedding.weight.data[item_idx] = torch.from_numpy(embedding).float()
                    item_embedding_set_count += 1
        
        print(f"Item Embedding 로드 완료: {item_embedding_set_count}개 (CSV 파일에서)")
        
        # 낮 모델 유저 임베딩 로드 (있으면)
        if os.path.exists(self.day_user_embedding_path):
            with open(self.day_user_embedding_path, 'r', encoding='utf-8') as f:
                day_user_embeddings = json.load(f)
            print(f"낮 모델 유저 임베딩 로드: {len(day_user_embeddings)}개")
            self.day_user_embeddings = day_user_embeddings
        else:
            print("낮 모델 유저 임베딩 없음. 밤 모델 사용")
            self.day_user_embeddings = {}
        
        # 밤 모델 유저 임베딩 로드 (백업용)
        if os.path.exists(self.night_user_embedding_path):
            with open(self.night_user_embedding_path, 'r', encoding='utf-8') as f:
                night_user_embeddings = json.load(f)
        else:
            night_user_embeddings = {}
        self.night_user_embeddings = night_user_embeddings
        print(f"밤 모델 유저 임베딩 로드: {len(night_user_embeddings)}개")
    
    def _inject_user_embedding(self, user_id: str):
        """
        특정 유저의 임베딩을 모델에 주입합니다.
        낮 모델 임베딩이 있으면 사용, 없으면 밤 모델 임베딩 사용.
        
        Args:
            user_id: 사용자 ID
        """
        # 낮 모델 임베딩 우선 사용
        if user_id in self.day_user_embeddings:
            embedding_list = self.day_user_embeddings[user_id]
            source = "낮 모델"
        elif user_id in self.night_user_embeddings:
            embedding_list = self.night_user_embeddings[user_id]
            source = "밤 모델"
        else:
            raise ValueError(f"User {user_id}의 임베딩을 찾을 수 없습니다.")
        
        if user_id in self.user_id_to_index:
            user_idx = self.user_id_to_index[user_id]
            embedding = np.array(embedding_list)
            
            # 차원 맞춤
            if embedding.shape[0] != self.embedding_dim:
                if embedding.shape[0] > self.embedding_dim:
                    embedding = embedding[:self.embedding_dim]
                else:
                    padding = np.zeros(self.embedding_dim - embedding.shape[0])
                    embedding = np.concatenate([embedding, padding])
            
            with torch.no_grad():
                self.model.user_embedding.weight.data[user_idx] = torch.from_numpy(embedding).float()
            
            return source
        else:
            raise ValueError(f"User {user_id}의 인덱스를 찾을 수 없습니다.")
    
    def recommend(
        self,
        target_user_id: str,
        candidate_item_ids: List[str],
        top_k: int = 30
    ) -> List[Dict[str, float]]:
        """
        추천을 수행합니다.
        
        Args:
            target_user_id: 추천을 받을 사용자 ID
            candidate_item_ids: 추천 대상 아이템 ID 리스트
            top_k: 추천할 아이템 개수
        
        Returns:
            List[Dict[str, float]]: [{'item_id': str, 'score': float}, ...]
        """
        # 유저 임베딩 주입
        source = self._inject_user_embedding(target_user_id)
        print(f"User {target_user_id} 임베딩 주입 완료 ({source})")
        
        # 아이템 인덱스 변환
        item_indices = []
        valid_item_ids = []
        
        for item_id in candidate_item_ids:
            if item_id in self.item_id_to_index:
                item_indices.append(self.item_id_to_index[item_id])
                valid_item_ids.append(item_id)
        
        if len(item_indices) == 0:
            return []
        
        # 유저 인덱스
        user_idx = self.user_id_to_index[target_user_id]
        
        # 텐서 생성
        user_tensor = torch.tensor([user_idx] * len(item_indices), dtype=torch.long).to(self.device)
        item_tensor = torch.tensor(item_indices, dtype=torch.long).to(self.device)
        
        # 추론
        with torch.no_grad():
            scores = self.model(user_tensor, item_tensor).cpu().numpy()
        
        # 결과 생성
        results = [
            {'item_id': item_id, 'score': float(score)}
            for item_id, score in zip(valid_item_ids, scores)
        ]
        
        # 점수 내림차순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Top-K 반환
        return results[:top_k]


if __name__ == "__main__":
    # 예시 사용
    recommender = HybridRecommender(
        night_model_path="data/models/neumf_night_model.pth",
        night_user_embedding_path="data/cache/night_user_embedding.json",
        outfit_embeddings_csv="data/cache/outfit_embeddings.csv",
        day_user_embedding_path="data/cache/day_user_embedding.json"
    )
    
    # 추천 수행
    recommendations = recommender.recommend(
        target_user_id="user_12345",
        candidate_item_ids=["outfit_1", "outfit_2", "outfit_3"],
        top_k=10
    )
    
    print("\n추천 결과:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['item_id']}: {rec['score']:.4f}")

