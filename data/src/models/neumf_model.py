"""
Neural Matrix Factorization (NeMF) 모델 정의
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class NeMF(nn.Module):
    def __init__(self, num_users, num_items, embedding_dim=512, hidden_dims=None, dropout=0.0):
        super(NeMF, self).__init__()
        
        if hidden_dims is None:
            hidden_dims = [128]  # 기본값: 1층
            
        # 임베딩 레이어
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.item_embedding = nn.Embedding(num_items, embedding_dim)
        
        # 1. MLP 부분
        mlp_layers = []
        # 입력 차원: embedding_dim * 2 (concatenation)
        input_dim = embedding_dim * 2 
        
        for hidden_dim in hidden_dims:
            mlp_layers.append(nn.Linear(input_dim, hidden_dim))
            mlp_layers.append(nn.ReLU())
            if dropout > 0:
                mlp_layers.append(nn.Dropout(dropout))
            input_dim = hidden_dim
            
        self.mlp = nn.Sequential(*mlp_layers)
        
        # 2. 최종 예측 레이어 수정
        # 입력: MLP 결과 + GMF 결과(embedding_dim 크기)
        # GMF와 MLP를 합쳐서(Concat) 최종 점수를 냅니다.
        final_input_dim = hidden_dims[-1] + embedding_dim
        self.output_layer = nn.Linear(final_input_dim, 1)
        self.sigmoid = nn.Sigmoid()
        
        self._init_weights()
    
    def _init_weights(self):
        """가중치 초기화"""
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.item_embedding.weight, std=0.01)
        
        for layer in self.mlp:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.constant_(layer.bias, 0)
        
        nn.init.xavier_uniform_(self.output_layer.weight)
        nn.init.constant_(self.output_layer.bias, 0)
    
    def forward(self, user_ids, item_ids):
            user_emb = self.user_embedding(user_ids)
            item_emb = self.item_embedding(item_ids)
            
            # [A] GMF 파트: 요소별 곱 (Element-wise Product) -> 유사도 학습에 유리
            gmf_output = user_emb * item_emb 
            
            # [B] MLP 파트: 복잡한 비선형 관계 학습
            concat_emb = torch.cat([user_emb, item_emb], dim=1)
            mlp_output = self.mlp(concat_emb)
            
            # [C] 결합 (NeuMF 방식)
            vector_concat = torch.cat([gmf_output, mlp_output], dim=1)
            output = self.output_layer(vector_concat)
            
            return self.sigmoid(output).squeeze(1)



