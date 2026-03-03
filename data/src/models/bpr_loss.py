"""
BPR (Bayesian Personalized Ranking) Loss 구현
"""
import torch
import torch.nn as nn


import torch.nn.functional as F

class BPRLoss(nn.Module):
    def __init__(self):
        super(BPRLoss, self).__init__()

    def forward(self, positive_scores, negative_scores):
        # softplus(x) = log(1 + exp(x))
        # BPR Loss = -log(sigmoid(diff)) = log(1 + exp(-diff))
        # 따라서 softplus(-diff)와 동일함
        
        diff = positive_scores - negative_scores
        loss = F.softplus(-diff)
        
        return loss.mean()


def compute_bpr_loss(
    model,
    user_ids: torch.Tensor,
    positive_item_ids: torch.Tensor,
    negative_item_ids: torch.Tensor
) -> torch.Tensor:
    """
    BPR Loss를 계산하는 헬퍼 함수
    
    Args:
        model: NeMF 모델
        user_ids: (batch_size,) - 사용자 인덱스
        positive_item_ids: (batch_size,) - Positive 아이템 인덱스
        negative_item_ids: (batch_size,) - Negative 아이템 인덱스
    
    Returns:
        torch.Tensor: BPR Loss
    """
    # Positive 점수
    positive_scores = model(user_ids, positive_item_ids)
    
    # Negative 점수
    negative_scores = model(user_ids, negative_item_ids)
    
    # BPR Loss
    bpr_loss = BPRLoss()
    loss = bpr_loss(positive_scores, negative_scores)
    
    return loss




