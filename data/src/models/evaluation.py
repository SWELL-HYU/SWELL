"""
추천 시스템 성능 평가 지표
"""
import numpy as np
import torch
from typing import List, Dict, Set
from collections import defaultdict


def hit_rate_at_k(
    recommendations: List[str],
    ground_truth: Set[str],
    k: int = 10
) -> float:
    """
    Hit Rate@K 계산
    
    Args:
        recommendations: 추천된 아이템 ID 리스트 (점수 순으로 정렬됨)
        ground_truth: 실제 상호작용한 아이템 ID 집합
        k: Top-K
    
    Returns:
        float: Hit Rate@K (0.0 ~ 1.0)
    """
    if len(ground_truth) == 0:
        return 0.0
    
    top_k = recommendations[:k]
    hits = len(set(top_k) & ground_truth)
    
    return 1.0 if hits > 0 else 0.0


def precision_at_k(
    recommendations: List[str],
    ground_truth: Set[str],
    k: int = 10
) -> float:
    """
    Precision@K 계산
    
    Args:
        recommendations: 추천된 아이템 ID 리스트 (점수 순으로 정렬됨)
        ground_truth: 실제 상호작용한 아이템 ID 집합
        k: Top-K
    
    Returns:
        float: Precision@K (0.0 ~ 1.0)
    """
    if k == 0:
        return 0.0
    
    top_k = recommendations[:k]
    hits = len(set(top_k) & ground_truth)
    
    return hits / k


def recall_at_k(
    recommendations: List[str],
    ground_truth: Set[str],
    k: int = 10
) -> float:
    """
    Recall@K 계산
    
    Args:
        recommendations: 추천된 아이템 ID 리스트 (점수 순으로 정렬됨)
        ground_truth: 실제 상호작용한 아이템 ID 집합
        k: Top-K
    
    Returns:
        float: Recall@K (0.0 ~ 1.0)
    """
    if len(ground_truth) == 0:
        return 0.0
    
    top_k = recommendations[:k]
    hits = len(set(top_k) & ground_truth)
    
    return hits / len(ground_truth)


def ndcg_at_k(
    recommendations: List[str],
    ground_truth: Set[str],
    k: int = 10
) -> float:
    """
    NDCG@K (Normalized Discounted Cumulative Gain) 계산
    
    Args:
        recommendations: 추천된 아이템 ID 리스트 (점수 순으로 정렬됨)
        ground_truth: 실제 상호작용한 아이템 ID 집합
        k: Top-K
    
    Returns:
        float: NDCG@K (0.0 ~ 1.0)
    """
    if len(ground_truth) == 0:
        return 0.0
    
    top_k = recommendations[:k]
    
    # DCG 계산
    dcg = 0.0
    for i, item_id in enumerate(top_k):
        if item_id in ground_truth:
            # rel = 1 (관련 있음), position = i + 1
            dcg += 1.0 / np.log2(i + 2)  # log2(i+2) because i starts from 0
    
    # IDCG 계산 (이상적인 경우)
    idcg = 0.0
    num_relevant = min(len(ground_truth), k)
    for i in range(num_relevant):
        idcg += 1.0 / np.log2(i + 2)
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def evaluate_recommendations(
    all_recommendations: Dict[str, List[str]],
    all_ground_truth: Dict[str, Set[str]],
    k: int = 10
) -> Dict[str, float]:
    """
    모든 사용자에 대한 추천 성능을 평가합니다.
    
    Args:
        all_recommendations: Dict[user_id, List[item_id]] - 각 사용자의 추천 리스트
        all_ground_truth: Dict[user_id, Set[item_id]] - 각 사용자의 실제 상호작용 집합
        k: Top-K
    
    Returns:
        Dict[str, float]: 평가 지표 딕셔너리
    """
    hr_scores = []
    precision_scores = []
    recall_scores = []
    ndcg_scores = []
    
    for user_id in all_recommendations:
        if user_id not in all_ground_truth:
            continue
        
        recommendations = all_recommendations[user_id]
        ground_truth = all_ground_truth[user_id]
        
        if len(ground_truth) == 0:
            continue
        
        hr = hit_rate_at_k(recommendations, ground_truth, k)
        prec = precision_at_k(recommendations, ground_truth, k)
        rec = recall_at_k(recommendations, ground_truth, k)
        ndcg = ndcg_at_k(recommendations, ground_truth, k)
        
        hr_scores.append(hr)
        precision_scores.append(prec)
        recall_scores.append(rec)
        ndcg_scores.append(ndcg)
    
    if len(hr_scores) == 0:
        return {
            'HR@K': 0.0,
            'Precision@K': 0.0,
            'Recall@K': 0.0,
            'NDCG@K': 0.0
        }
    
    return {
        'HR@K': np.mean(hr_scores),
        'Precision@K': np.mean(precision_scores),
        'Recall@K': np.mean(recall_scores),
        'NDCG@K': np.mean(ndcg_scores)
    }


def create_ground_truth_from_interactions(
    interactions: List[tuple],
    user_id_to_index: Dict[str, int],
    item_id_to_index: Dict[str, int]
) -> Dict[str, Set[str]]:
    """
    상호작용 데이터로부터 ground truth를 생성합니다.
    
    Args:
        interactions: List[Tuple[user_id, item_id, interaction]]
        user_id_to_index: 사용자 ID -> 인덱스 매핑
        item_id_to_index: 아이템 ID -> 인덱스 매핑
    
    Returns:
        Dict[str, Set[str]]: user_id -> 실제 상호작용한 item_id 집합
    """
    ground_truth = defaultdict(set)
    
    for user_id, item_id, interaction in interactions:
        # Positive interaction만 포함 (like, preference)
        if interaction in ['like', 'preference']:
            if user_id in user_id_to_index and item_id in item_id_to_index:
                ground_truth[user_id].add(item_id)
    
    return dict(ground_truth)




