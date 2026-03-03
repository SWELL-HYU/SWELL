import torch
from torch.utils.data import Dataset
import random
import numpy as np
from typing import List, Tuple, Optional

class BPRDataset(Dataset):
    def __init__(self, positive_interactions, num_items, num_negatives=1, skip_interactions: Optional[List[Tuple[int, int]]] = None):
        """
        Args:
            positive_interactions: List[Tuple[user_idx, item_idx, interaction_type]]
                interaction_type: 'like' or 'preference'
            num_items: 전체 아이템 수
            num_negatives: 각 positive에 대해 샘플링할 negative 개수
            skip_interactions: Skip 데이터 리스트 (Negative 후보군으로 활용)
        """
        self.positive_interactions = positive_interactions  # [(user, item, type), ...]
        self.num_items = num_items
        self.num_negatives = num_negatives
        self.skip_interactions = skip_interactions if skip_interactions else []
        
        # 빠른 조회를 위해 User별 Positive 아이템을 Set으로 저장
        self.user_pos_dict = {}
        for u, i, _ in positive_interactions:
            if u not in self.user_pos_dict:
                self.user_pos_dict[u] = set()
            self.user_pos_dict[u].add(i)
        
        # User별 Skip 아이템을 Set으로 저장 (Negative 후보군)
        self.user_skip_dict = {}
        for u, i in self.skip_interactions:
            if u not in self.user_skip_dict:
                self.user_skip_dict[u] = set()
            self.user_skip_dict[u].add(i)

    def __len__(self):
        return len(self.positive_interactions)

    def __getitem__(self, idx):
        user_idx, pos_item_idx, interaction_type = self.positive_interactions[idx]
        
        # Negative 샘플링: Skip 데이터를 우선 사용, 없으면 랜덤 샘플링
        neg_item_idx = self._sample_negative(user_idx)
        
        return {
            'user_id': torch.tensor(user_idx, dtype=torch.long),
            'positive_item_id': torch.tensor(pos_item_idx, dtype=torch.long),
            'negative_item_id': torch.tensor(neg_item_idx, dtype=torch.long)
        }

    def _sample_negative(self, user_idx):
        """
        Negative 샘플링: Skip 데이터를 우선 사용, 없으면 랜덤 샘플링
        """
        # 1. Skip 데이터가 있으면 우선 사용 (70% 확률)
        if user_idx in self.user_skip_dict and len(self.user_skip_dict[user_idx]) > 0:
            if random.random() < 0.7:  # 70% 확률로 Skip 데이터 사용
                skip_items = list(self.user_skip_dict[user_idx])
                return random.choice(skip_items)
        
        # 2. Skip 데이터가 없거나 30% 확률로 랜덤 샘플링
        # 무한 루프 방지를 위한 안전장치
        if len(self.user_pos_dict[user_idx]) >= self.num_items:
            return 0  # 모든 아이템을 다 본 경우 (예외처리)

        max_attempts = 100
        for _ in range(max_attempts):
            # 전체 아이템 중 하나를 랜덤하게 뽑음
            neg_candidate = random.randint(0, self.num_items - 1)
            
            # 그 아이템이 유저가 본 적 없는 것이라면 선택
            if neg_candidate not in self.user_pos_dict[user_idx]:
                return neg_candidate
        
        # 최후의 수단: 첫 번째 아이템 반환 (거의 발생하지 않음)
        return 0