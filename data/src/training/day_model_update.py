"""
낮 모델 업데이트 스크립트
밤 모델 임베딩을 기반으로 낮 모델 임베딩을 초기화하고, 새로운 상호작용으로 미세 학습합니다.
"""
import os
import sys
import csv
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from tqdm import tqdm

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from data.src.models.neumf_model import NeMF
from data.src.models.bpr_dataset import BPRDataset
from data.src.models.bpr_loss import BPRLoss
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


class DayModelUpdater:
    """
    낮 모델 업데이트 클래스
    밤 모델 임베딩을 기반으로 낮 모델 임베딩을 관리합니다.
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
        
        # 밤 모델 로드
        self._load_night_model()
        
        # 아이템 임베딩은 CSV 파일에서 로드 (고정, 학습 안 함)
        self._load_item_embeddings_from_csv()
    
    def _load_night_model(self):
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
        
        print(f"밤 모델 로드 완료: {self.night_model_path}")
        print(f"사용자 수: {self.num_users}, 아이템 수: {self.num_items}")
    
    def _load_item_embeddings_from_csv(self):
        """CSV 파일의 outfit_embedding을 로드하고 고정합니다."""
        print(f"Item Embedding 로드 (CSV 파일): {self.outfit_embeddings_csv}")
        item_id_to_embedding = load_item_embeddings_from_csv(self.outfit_embeddings_csv)
        
        # 아이템 임베딩 설정 (CSV에서 로드한 outfit_embedding 사용)
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
        
        # 아이템 임베딩 고정 (학습 안 함)
        self.model.item_embedding.requires_grad_(False)
        
        print(f"Item Embedding 설정 완료: {item_embedding_set_count}개 (고정, 학습 안 함)")
    
    def initialize_day_embeddings(self):
        """
        낮 모델 임베딩을 초기화합니다.
        - day_user_embedding.json이 있으면 로드
        - 없으면 night_user_embedding.json을 복사하여 초기화
        """
        if os.path.exists(self.day_user_embedding_path):
            print(f"기존 낮 모델 임베딩 로드: {self.day_user_embedding_path}")
            with open(self.day_user_embedding_path, 'r', encoding='utf-8') as f:
                day_embeddings = json.load(f)
            
            # 기존 낮 모델 임베딩을 모델에 설정
            with torch.no_grad():
                for user_id_str, embedding_list in day_embeddings.items():
                    if user_id_str in self.user_id_to_index:
                        user_idx = self.user_id_to_index[user_id_str]
                        embedding = np.array(embedding_list)
                        
                        # 차원 맞춤
                        if embedding.shape[0] != self.embedding_dim:
                            if embedding.shape[0] > self.embedding_dim:
                                embedding = embedding[:self.embedding_dim]
                            else:
                                padding = np.zeros(self.embedding_dim - embedding.shape[0])
                                embedding = np.concatenate([embedding, padding])
                        
                        self.model.user_embedding.weight.data[user_idx] = torch.from_numpy(embedding).float()
            
            print(f"{len(day_embeddings)}개의 기존 낮 모델 임베딩 로드됨")
        else:
            print(f"낮 모델 임베딩 없음. 밤 모델 임베딩을 기반으로 초기화")
            if os.path.exists(self.night_user_embedding_path):
                with open(self.night_user_embedding_path, 'r', encoding='utf-8') as f:
                    night_embeddings = json.load(f)
            else:
                night_embeddings = {}
            
            # 밤 모델 임베딩을 낮 모델 임베딩으로 복사
            with torch.no_grad():
                for user_id_str, embedding_list in night_embeddings.items():
                    if user_id_str in self.user_id_to_index:
                        user_idx = self.user_id_to_index[user_id_str]
                        embedding = np.array(embedding_list)
                        
                        # 차원 맞춤
                        if embedding.shape[0] != self.embedding_dim:
                            if embedding.shape[0] > self.embedding_dim:
                                embedding = embedding[:self.embedding_dim]
                            else:
                                padding = np.zeros(self.embedding_dim - embedding.shape[0])
                                embedding = np.concatenate([embedding, padding])
                        
                        self.model.user_embedding.weight.data[user_idx] = torch.from_numpy(embedding).float()
            
            print(f"{len(night_embeddings)}개의 밤 모델 임베딩을 낮 모델로 복사")
        
        # 유저 임베딩은 학습 가능하도록 설정
        self.model.user_embedding.requires_grad_(True)
    
    def _freeze_non_user_params(self):
        """유저 임베딩을 제외한 모든 파라미터를 고정합니다."""
        for name, param in self.model.named_parameters():
            if 'user_embedding' not in name:
                param.requires_grad = False
            else:
                param.requires_grad = True
    
    def load_interactions_from_csv(
        self,
        csv_file: str,
        since_timestamp: Optional[datetime] = None
    ) -> List[Tuple[int, int]]:
        """
        CSV 파일에서 positive 상호작용을 로드합니다 (BPR Loss용).
        
        Args:
            csv_file: CSV 파일 경로
            since_timestamp: 이 시간 이후의 상호작용만 로드 (None이면 모두)
        
        Returns:
            List[Tuple[user_idx, item_idx]] - Positive 상호작용만 (like, preference)
        """
        positive_interactions = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row['user_id']
                item_id = row['outfit_id']
                interaction = row['interaction']
                
                # Positive interaction만 (like, preference)
                if interaction in ['like', 'preference']:
                    if user_id in self.user_id_to_index and item_id in self.item_id_to_index:
                        user_idx = self.user_id_to_index[user_id]
                        item_idx = self.item_id_to_index[item_id]
                        positive_interactions.append((user_idx, item_idx))
        
        return positive_interactions
    
    def fine_tune_user_embeddings(
        self,
        positive_interactions: List[Tuple[int, int]],
        epochs: int = 1,
        batch_size: int = 256,
        learning_rate: float = 0.001,
        num_negatives: int = 1
    ):
        """
        유저 임베딩만 미세 학습합니다 (BPR Loss 사용).
        
        Args:
            positive_interactions: List[Tuple[user_idx, item_idx]] - Positive 상호작용
            epochs: 에폭 수
            batch_size: 배치 크기
            learning_rate: 학습률
            num_negatives: 각 positive에 대해 샘플링할 negative 개수
        """
        if len(positive_interactions) == 0:
            print("학습할 상호작용이 없습니다.")
            return
        
        print(f"\n낮 모델 유저 임베딩 미세 학습 시작 (BPR Loss)")
        print(f"Positive 상호작용 수: {len(positive_interactions)}, 에폭: {epochs}")
        
        # BPR 데이터셋 생성
        dataset = BPRDataset(positive_interactions, self.num_items, num_negatives)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # 옵티마이저 설정 (유저 임베딩만)
        optimizer = optim.Adam(
            [self.model.user_embedding.weight],
            lr=learning_rate
        )
        bpr_loss = BPRLoss()
        
        # 학습 루프
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0.0
            num_batches = 0
            
            for batch in tqdm(dataloader, desc=f"Epoch {epoch+1}/{epochs}"):
                user_ids = batch['user_id'].to(self.device)
                positive_item_ids = batch['positive_item_id'].to(self.device)
                negative_item_ids = batch['negative_item_id'].to(self.device)
                
                # Forward pass
                positive_scores = self.model(user_ids, positive_item_ids)
                negative_scores = self.model(user_ids, negative_item_ids)
                
                # BPR Loss 계산
                loss = bpr_loss(positive_scores, negative_scores)
                
                # Backward pass (유저 임베딩만 업데이트)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                num_batches += 1
            
            avg_loss = total_loss / num_batches
            print(f"Epoch {epoch+1}/{epochs} - Average BPR Loss: {avg_loss:.6f}")
    
    def save_day_user_embeddings(self):
        """낮 모델 유저 임베딩을 저장합니다."""
        print(f"\n낮 모델 유저 임베딩 저장: {self.day_user_embedding_path}")
        
        self.model.eval()
        day_user_embeddings = {}
        
        with torch.no_grad():
            for user_id_str, user_idx in self.user_id_to_index.items():
                embedding = self.model.user_embedding.weight[user_idx].cpu().numpy()
                day_user_embeddings[user_id_str] = embedding
        
        # User Embedding 저장
        os.makedirs(os.path.dirname(self.day_user_embedding_path), exist_ok=True)
        embeddings_dict = {
            user_id: embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
            for user_id, embedding in day_user_embeddings.items()
        }
        with open(self.day_user_embedding_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_dict, f, ensure_ascii=False, indent=2)
        print(f"{len(day_user_embeddings)}개의 낮 모델 유저 임베딩 저장 완료")


if __name__ == "__main__":
    # 예시 사용
    updater = DayModelUpdater(
        night_model_path="data/models/neumf_night_model.pth",
        night_user_embedding_path="data/cache/night_user_embedding.json",
        outfit_embeddings_csv="data/cache/outfit_embeddings.csv",
        day_user_embedding_path="data/cache/day_user_embedding.json"
    )
    
    # 낮 모델 임베딩 초기화
    updater.initialize_day_embeddings()
    
    # 새로운 상호작용 로드 (positive만)
    new_positive_interactions = updater.load_interactions_from_csv(
        "data/cache/user_outfit_interaction.csv"
    )
    
    # 미세 학습 (BPR Loss)
    updater.fine_tune_user_embeddings(new_positive_interactions, epochs=1)
    
    # 저장
    updater.save_day_user_embeddings()

