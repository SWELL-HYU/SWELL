"""
밤 모델 학습 스크립트
하루가 끝나고 모든 상호작용 데이터로 밤 모델 임베딩을 학습합니다.
"""
import os
import sys
import json
import csv
import ast
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from typing import Dict, List, Tuple, Set
from tqdm import tqdm

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from Data.src.neumf_model import NeMF
from Data.src.bpr_dataset import BPRDataset
from Data.src.bpr_loss import BPRLoss
from Data.src.evaluation import (
    evaluate_recommendations,
    create_ground_truth_from_interactions
)
# user_embedding_utils 함수들을 인라인화

# CSV 파일에서 임베딩 로드 함수
def load_item_embeddings_from_csv(csv_file: str) -> Dict[str, np.ndarray]:
    """
    CSV 파일에서 outfit_id별 임베딩을 로드합니다.
    
    Args:
        csv_file: CSV 파일 경로 (outfit_id, outfit_embedding 컬럼)
    
    Returns:
        Dict[str, np.ndarray]: outfit_id -> embedding 매핑
    """
    item_id_to_embedding = {}
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        # 첫 번째 줄 읽기 (헤더 확인용)
        first_line = f.readline().strip()
        
        # Git merge conflict 마커나 잘못된 헤더 처리
        if first_line.startswith('<<<<<<<') or first_line.startswith('=======') or first_line.startswith('>>>>>>>'):
            # 다음 줄을 헤더로 사용
            f.seek(0)  # 파일 처음으로
            next(f)  # 첫 줄 건너뛰기
        
        reader = csv.DictReader(f)
        for row in reader:
            # None 체크 후 안전하게 접근
            outfit_id = row.get('outfit_id')
            embedding_str = row.get('outfit_embedding')
            
            # None이나 빈 값 필터링
            if not outfit_id or not embedding_str:
                continue
            
            outfit_id = str(outfit_id).strip()
            embedding_str = str(embedding_str).strip()
            
            if not outfit_id or not embedding_str:
                continue
            
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


def load_interactions_from_csv(csv_file: str, only_untrained: bool = True) -> List[Tuple[str, str, str]]:
    """
    CSV 파일에서 상호작용 데이터를 로드합니다.
    
    Args:
        csv_file: CSV 파일 경로
        only_untrained: True면 trained=False인 상호작용만 로드, False면 모두 로드
    
    Returns:
        List[Tuple[user_id, outfit_id, interaction]]
    """
    interactions = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # None 체크 후 strip
            user_id = row.get('user_id') or ''
            outfit_id = row.get('outfit_id') or ''
            interaction = row.get('interaction') or ''
            
            # 문자열로 변환 후 strip
            user_id = str(user_id).strip() if user_id is not None else ''
            outfit_id = str(outfit_id).strip() if outfit_id is not None else ''
            interaction = str(interaction).strip() if interaction is not None else ''
            
            # None이나 빈 값 필터링
            if not user_id or not outfit_id or not interaction:
                continue
            
            # trained 컬럼이 없으면 False로 간주 (기존 데이터 호환성)
            trained = row.get('trained', 'False').lower() == 'true'
            
            if only_untrained and trained:
                continue  # 이미 학습된 상호작용은 건너뛰기
            
            interactions.append((user_id, outfit_id, interaction))
    return interactions


def _update_trained_interactions(csv_file: str, trained_interactions: List[Tuple[str, str, str]]):
    """
    학습된 상호작용을 trained=True로 업데이트합니다.
    
    Args:
        csv_file: CSV 파일 경로
        trained_interactions: 학습에 사용된 상호작용 리스트 (user_id, outfit_id, interaction)
    """
    # 학습된 상호작용을 Set으로 변환 (빠른 조회)
    trained_set = {(user_id, outfit_id, interaction) for user_id, outfit_id, interaction in trained_interactions}
    
    # CSV 파일 읽기
    rows = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        # trained 컬럼이 없으면 추가
        if 'trained' not in fieldnames:
            fieldnames = list(fieldnames) + ['trained']
        
        for row in reader:
            user_id = row['user_id']
            outfit_id = row['outfit_id']
            interaction = row['interaction']
            
            # 학습된 상호작용이면 trained=True로 업데이트
            if (user_id, outfit_id, interaction) in trained_set:
                row['trained'] = 'True'
            elif 'trained' not in row:
                row['trained'] = 'False'  # 기존 데이터는 False로 설정
            
            rows.append(row)
    
    # CSV 파일 쓰기
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    trained_count = sum(1 for row in rows if row.get('trained', 'False').lower() == 'true')
    print(f"학습된 상호작용 {trained_count}개를 trained=True로 업데이트 완료")


def interaction_to_rating(interaction: str) -> float:
    """
    상호작용 타입을 rating으로 변환합니다.
    
    Args:
        interaction: 'like', 'preference', 'skip'
    
    Returns:
        float: rating (0.0 ~ 1.0)
    """
    if interaction == 'preference':
        return 1.0
    elif interaction == 'like':
        return 1.0
    elif interaction == 'skip':
        return 0.0
    else:
        return 0.5  # 기본값


def train_night_model(
    interaction_csv: str = "data/cache/user_outfit_interaction.csv",
    outfit_embeddings_csv: str = "data/cache/outfit_embeddings.csv",
    day_user_embedding_path: str = "data/cache/day_user_embedding.json",
    night_model_save_path: str = "data/models/neumf_night_model.pth",
    night_user_embedding_path: str = "data/cache/night_user_embedding.json",
    embedding_dim: int = 512,
    hidden_dims: List[int] = None,
    learning_rate: float = 0.05,
    batch_size: int = 128,
    num_epochs: int = 15,
    num_negatives: int = 1,
    test_ratio: float = 0.2,
    eval_k: int = 10,
    dropout: float = 0.2,
    weight_decay: float = 0.0,
    device: str = None
):
    """
    밤 모델을 학습합니다 (BPR Loss 사용).
    
    중요:
    - Item embedding은 CSV 파일(outfit_embeddings.csv)에서 로드 (학습 안 함, 고정)
    - User embedding만 학습하고 저장
    
    Args:
        interaction_csv: 상호작용 CSV 파일 경로
        outfit_embeddings_csv: Item Embedding CSV 파일 경로 (outfit_id, outfit_embedding)
        day_user_embedding_path: 낮 모델 유저 임베딩 경로 (초기값으로 사용, 선택적)
        night_model_save_path: 밤 모델 저장 경로
        night_user_embedding_path: 밤 모델 유저 임베딩 저장 경로
        embedding_dim: 임베딩 차원 (고정: 512)
        hidden_dims: MLP 히든 레이어 차원 리스트 (기본값: [128] - 1층)
        learning_rate: 학습률 (기본값: 0.005)
        batch_size: 배치 크기 (기본값: 128)
        num_epochs: 에폭 수 (기본값: 50)
        num_negatives: 각 positive에 대해 샘플링할 negative 개수 (기본값: 1)
        test_ratio: 테스트 데이터 비율 (0.0 ~ 1.0)
        eval_k: 평가할 Top-K 값
        dropout: Dropout 비율 (기본값: 0.0)
        weight_decay: Weight decay (L2 정규화, 기본값: 0.0 - 과적합 방지를 위해 제거)
        device: 사용할 디바이스 ('cuda' or 'cpu')
    """
    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    if hidden_dims is None:
        hidden_dims = [512, 64]  # 정보를 단계적으로 압축하는 깔때기 구조
    
    print("=" * 80)
    print("밤 모델 학습 시작")
    print("=" * 80)
    
    # 1. 상호작용 데이터 로드 (학습되지 않은 상호작용만)
    print(f"\n[1] 상호작용 데이터 로드: {interaction_csv}")
    interactions = load_interactions_from_csv(interaction_csv, only_untrained=True)
    print(f"총 {len(interactions)}개의 학습되지 않은 상호작용 로드됨")
    
    if len(interactions) == 0:
        print("학습할 상호작용이 없습니다. 종료합니다.")
        return
    
    # 2. 고유한 user_id와 item_id 추출
    unique_users = sorted(set([user_id for user_id, _, _ in interactions]))
    unique_items = sorted(set([item_id for _, item_id, _ in interactions]))
    
    num_users = len(unique_users)
    num_items = len(unique_items)
    
    print(f"사용자 수: {num_users}, 아이템 수: {num_items}")
    
    # 3. ID 매핑 생성
    user_id_to_index = {user_id: idx for idx, user_id in enumerate(unique_users)}
    item_id_to_index = {item_id: idx for idx, item_id in enumerate(unique_items)}
    index_to_user_id = {idx: user_id for user_id, idx in user_id_to_index.items()}
    index_to_item_id = {idx: item_id for item_id, idx in item_id_to_index.items()}
    
    # 4. Positive 상호작용 추출 및 Skip 데이터 수집 (Like Oversampling 적용)
    positive_interactions = []
    skip_interactions = []  # Skip 데이터를 negative로 활용
    all_interactions_indexed = []
    
    like_count = 0
    preference_count = 0
    skip_count = 0
    
    for user_id, item_id, interaction in interactions:
        user_idx = user_id_to_index[user_id]
        item_idx = item_id_to_index[item_id]
        
        # 모든 상호작용 저장 (평가용)
        all_interactions_indexed.append((user_id, item_id, interaction))
        
        if interaction == 'like':
            # Like 데이터를 5배 oversampling (더 많이 띄우기)
            for _ in range(9):
                positive_interactions.append((user_idx, item_idx, 'like'))
            like_count += 1
        elif interaction == 'preference':
            # Preference는 1번만 추가
            positive_interactions.append((user_idx, item_idx, 'preference'))
            preference_count += 1
        elif interaction == 'skip':
            # Skip 데이터를 negative 후보군으로 저장
            skip_interactions.append((user_idx, item_idx))
            skip_count += 1
    
    print(f"Positive 상호작용: {len(positive_interactions)}개 (Like: {like_count}개 → {like_count * 5}개 oversampling, Preference: {preference_count}개)")
    print(f"Skip 상호작용: {skip_count}개 (Negative 후보군으로 활용)")
    
    # 5. Train/Test Split
    if test_ratio > 0:
        np.random.seed(42)
        np.random.shuffle(positive_interactions)
        split_idx = int(len(positive_interactions) * (1 - test_ratio))
        train_interactions = positive_interactions[:split_idx]
        test_interactions = positive_interactions[split_idx:]
        print(f"Train: {len(train_interactions)}개, Test: {len(test_interactions)}개")
    else:
        train_interactions = positive_interactions
        test_interactions = []
        print(f"Train: {len(train_interactions)}개 (Test split 없음)")
    
    # Skip 데이터도 Train/Test Split (Negative 후보군)
    train_skip_interactions = skip_interactions  # Skip은 모두 학습에 사용
    
    # 6. BPR 데이터셋 생성 (Skip 데이터를 Negative로 활용)
    print(f"\n[2] BPR 데이터셋 생성 (negative sampling: {num_negatives}개, Skip 데이터를 Negative로 활용)")
    train_dataset = BPRDataset(
        train_interactions, 
        num_items, 
        num_negatives,
        skip_interactions=train_skip_interactions  # Skip 데이터 전달
    )
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Test ground truth 생성 (interaction type 제거)
    test_ground_truth = {}
    if test_interactions:
        for user_idx, item_idx, _ in test_interactions:
            user_id = index_to_user_id[user_idx]
            item_id = index_to_item_id[item_idx]
            if user_id not in test_ground_truth:
                test_ground_truth[user_id] = set()
            test_ground_truth[user_id].add(item_id)
    
    # 6. Item Embedding 로드 (CSV 파일에서 로드)
    print(f"\n[3] Item Embedding 로드 (고정, 학습 안 함): {outfit_embeddings_csv}")
    item_id_to_embedding = load_item_embeddings_from_csv(outfit_embeddings_csv)
    print(f"로드된 Item Embedding: {len(item_id_to_embedding)}개")
    
    # 7. 모델 초기화
    print(f"\n[4] 모델 초기화")
    print(f"  - hidden_dims: {hidden_dims}")
    print(f"  - dropout: {dropout}")
    model = NeMF(
        num_users=num_users,
        num_items=num_items,
        embedding_dim=embedding_dim,
        hidden_dims=hidden_dims,
        dropout=dropout
    ).to(device)
    
    # Item Embedding 설정 (CSV에서 로드한 outfit_embedding 사용)
    print(f"[5] Item Embedding 설정 (고정)")
    item_embedding_set_count = 0
    with torch.no_grad():
        for item_id_str, item_idx in item_id_to_index.items():
            if item_id_str in item_id_to_embedding:
                embedding = item_id_to_embedding[item_id_str]
                
                # 차원 맞춤
                if embedding.shape[0] != embedding_dim:
                    if embedding.shape[0] > embedding_dim:
                        embedding = embedding[:embedding_dim]
                    else:
                        padding = np.zeros(embedding_dim - embedding.shape[0])
                        embedding = np.concatenate([embedding, padding])
                
                model.item_embedding.weight.data[item_idx] = torch.from_numpy(embedding).float()
                item_embedding_set_count += 1
            else:
                # CSV에 임베딩이 없는 경우 랜덤 초기화 유지
                pass
    
    print(f"Item Embedding 설정 완료: {item_embedding_set_count}개")
    
    # Item Embedding 고정 (학습 안 함)
    model.item_embedding.requires_grad_(False)
    print("Item Embedding 고정 완료 (학습 안 함)")
    
    # 8. 밤 모델 임베딩을 초기값으로 사용 (선택적)
    night_user_embedding_path_for_init = night_user_embedding_path
    initialized_count = 0
    
    if os.path.exists(night_user_embedding_path_for_init):
        # 파일 크기 확인 (비어있는지 체크)
        file_size = os.path.getsize(night_user_embedding_path_for_init)
        
        if file_size > 0:
            try:
                print(f"\n[6] 밤 모델 임베딩을 초기값으로 사용: {night_user_embedding_path_for_init}")
                with open(night_user_embedding_path_for_init, 'r', encoding='utf-8') as f:
                    night_embeddings = json.load(f)
                
                # 딕셔너리가 비어있지 않은지 확인
                if night_embeddings and isinstance(night_embeddings, dict):
                    for user_id_str, embedding_list in night_embeddings.items():
                        if user_id_str in user_id_to_index:
                            user_idx = user_id_to_index[user_id_str]
                            embedding = np.array(embedding_list)
                            
                            # 512차원으로 맞춤
                            if embedding.shape[0] != embedding_dim:
                                if embedding.shape[0] > embedding_dim:
                                    embedding = embedding[:embedding_dim]
                                else:
                                    padding = np.zeros(embedding_dim - embedding.shape[0])
                                    embedding = np.concatenate([embedding, padding])
                            
                            model.user_embedding.weight.data[user_idx] = torch.from_numpy(embedding).float()
                            initialized_count += 1
                    
                    if initialized_count > 0:
                        print(f"{initialized_count}개의 유저 임베딩 초기화됨 (밤 모델 임베딩 사용)")
                    else:
                        print(f"밤 모델 임베딩 파일이 있지만 유효한 데이터가 없음. 랜덤 초기화 사용")
                else:
                    print(f"밤 모델 임베딩 파일이 비어있음. 랜덤 초기화 사용")
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"밤 모델 임베딩 파일 파싱 오류: {e}. 랜덤 초기화 사용")
        else:
            print(f"밤 모델 임베딩 파일이 비어있음. 랜덤 초기화 사용")
    else:
        print(f"\n[6] 밤 모델 임베딩 파일 없음. 랜덤 초기화 사용")
    
    if initialized_count == 0:
        print(f"모든 유저 임베딩을 랜덤 초기화로 사용")
    
    # 9. 학습 설정 (User Embedding만 학습)
    # Item Embedding은 이미 고정되어 있으므로 User Embedding만 옵티마이저에 포함
    optimizer = optim.AdamW([model.user_embedding.weight], lr=learning_rate, weight_decay=weight_decay)
    
    # Learning Rate Scheduler: NDCG 기반으로 동작
    # NDCG가 연속 2번 상승하지 않으면 learning rate 감소
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.7, patience=2, verbose=True)
    
    bpr_loss = BPRLoss()
    
    print(f"\n[7] 학습 설정")
    print(f"  - User Embedding만 학습 (Item Embedding은 고정)")
    print(f"  - BPR Loss 사용")
    print(f"  - Initial Learning Rate: {learning_rate}")
    print(f"  - Learning Rate Scheduler: ReduceLROnPlateau (NDCG 기반)")
    print(f"    → NDCG가 연속 2번 상승하지 않으면 learning rate 감소 (factor=0.7)")
    print(f"  - Weight Decay: {weight_decay}")
    print(f"  - Dropout: {dropout}")
    
    # 10. 학습 루프
    print(f"\n[8] 학습 시작 (에폭: {num_epochs}, 배치 크기: {batch_size})")
    model.train()
    
    best_metrics = None
    best_epoch = 0
    ndcg_history = []  # NDCG 히스토리 추적 (5 에폭마다 평가)
    
    for epoch in range(num_epochs):
        total_loss = 0.0
        num_batches = 0
        
        for batch in tqdm(train_dataloader, desc=f"Epoch {epoch+1}/{num_epochs}"):
            user_ids = batch['user_id'].to(device)
            positive_item_ids = batch['positive_item_id'].to(device)
            negative_item_ids = batch['negative_item_id'].to(device)
            
            # Forward pass
            positive_scores = model(user_ids, positive_item_ids)
            negative_scores = model(user_ids, negative_item_ids)
            
            # BPR Loss 계산
            loss = bpr_loss(positive_scores, negative_scores)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        avg_loss = total_loss / num_batches
        current_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch {epoch+1}/{num_epochs} - Average BPR Loss: {avg_loss:.6f} - LR: {current_lr:.6f}")
        
        # 평가 (테스트 데이터가 있는 경우, 5 에폭마다)
        if test_interactions and (epoch + 1) % 5 == 0:
            print(f"\n[평가] Epoch {epoch+1}")
            metrics = evaluate_model(
                model, test_ground_truth, user_id_to_index, item_id_to_index,
                index_to_user_id, index_to_item_id, num_items, eval_k, device
            )
            
            current_ndcg = metrics['NDCG@K']
            ndcg_history.append(current_ndcg)
            
            print(f"  HR@{eval_k}: {metrics['HR@K']:.4f}")
            print(f"  Precision@{eval_k}: {metrics['Precision@K']:.4f}")
            print(f"  Recall@{eval_k}: {metrics['Recall@K']:.4f}")
            print(f"  NDCG@{eval_k}: {current_ndcg:.4f}")
            
            # Best 모델 저장
            if best_metrics is None or current_ndcg > best_metrics['NDCG@K']:
                best_metrics = metrics
                best_epoch = epoch + 1
                print(f"  → Best 모델 업데이트 (NDCG@{eval_k}: {current_ndcg:.4f})")
            
            # Learning Rate Scheduler 업데이트 (NDCG 기반)
            # NDCG가 연속 2번 상승하지 않으면 learning rate 감소
            # ReduceLROnPlateau는 mode='max'이므로 NDCG를 직접 전달
            scheduler.step(current_ndcg)
            
            # NDCG 히스토리 출력 (디버깅용)
            if len(ndcg_history) >= 2:
                prev_ndcg = ndcg_history[-2]
                if current_ndcg > prev_ndcg:
                    print(f"  → NDCG 상승: {prev_ndcg:.4f} → {current_ndcg:.4f}")
                else:
                    print(f"  → NDCG 하락 또는 동일: {prev_ndcg:.4f} → {current_ndcg:.4f}")
    
    # 최종 평가 결과 출력
    if test_interactions:
        print(f"\n[최종 평가 결과]")
        print(f"Best Epoch: {best_epoch}")
        if best_metrics:
            print(f"  HR@{eval_k}: {best_metrics['HR@K']:.4f}")
            print(f"  Precision@{eval_k}: {best_metrics['Precision@K']:.4f}")
            print(f"  Recall@{eval_k}: {best_metrics['Recall@K']:.4f}")
            print(f"  NDCG@{eval_k}: {best_metrics['NDCG@K']:.4f}")
    
    # 11. 모델 저장
    print(f"\n[9] 모델 저장: {night_model_save_path}")
    os.makedirs(os.path.dirname(night_model_save_path), exist_ok=True)
    
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'user_id_to_index': user_id_to_index,
        'item_id_to_index': item_id_to_index,
        'num_users': num_users,
        'num_items': num_items,
        'embedding_dim': embedding_dim,
        'hidden_dims': hidden_dims,
        'epoch': num_epochs,
        'loss': avg_loss,
        'best_metrics': best_metrics,
        'best_epoch': best_epoch,
        'outfit_embeddings_csv': outfit_embeddings_csv  # Item embedding 출처 기록
    }
    torch.save(checkpoint, night_model_save_path)
    print("모델 저장 완료")
    
    # 12. 밤 모델 User Embedding 저장 (Item Embedding은 저장 안 함, JSON에서 로드)
    print(f"\n[10] 밤 모델 User Embedding 저장")
    model.eval()
    
    # User Embedding 저장
    night_user_embeddings = {}
    with torch.no_grad():
        for user_id_str, user_idx in user_id_to_index.items():
            embedding = model.user_embedding.weight[user_idx].cpu().numpy()
            night_user_embeddings[user_id_str] = embedding
    
    # User Embedding 저장
    os.makedirs(os.path.dirname(night_user_embedding_path), exist_ok=True)
    embeddings_dict = {
        user_id: embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
        for user_id, embedding in night_user_embeddings.items()
    }
    with open(night_user_embedding_path, 'w', encoding='utf-8') as f:
        json.dump(embeddings_dict, f, ensure_ascii=False, indent=2)
    print(f"밤 모델 유저 임베딩 저장: {night_user_embedding_path}")
    print(f"Item Embedding은 저장하지 않음 (CSV 파일에서 로드: {outfit_embeddings_csv})")
    
    # 13. 학습된 상호작용을 trained=True로 업데이트
    print(f"\n[11] 학습된 상호작용을 trained=True로 업데이트")
    _update_trained_interactions(interaction_csv, interactions)
    
    # 14. 낮 임베딩도 밤 임베딩으로 최신화
    print(f"\n[12] 낮 임베딩을 밤 임베딩으로 최신화")
    if os.path.exists(day_user_embedding_path):
        # 기존 낮 임베딩 로드
        with open(day_user_embedding_path, 'r', encoding='utf-8') as f:
            day_embeddings = json.load(f)
        
        # 밤 임베딩으로 업데이트 (밤 임베딩에 있는 사용자만)
        updated_count = 0
        for user_id_str, embedding_list in night_user_embeddings.items():
            day_embeddings[user_id_str] = embedding_list
            updated_count += 1
        
        # 저장
        with open(day_user_embedding_path, 'w', encoding='utf-8') as f:
            json.dump(day_embeddings, f, ensure_ascii=False, indent=2)
        print(f"{updated_count}개의 낮 임베딩이 밤 임베딩으로 업데이트됨")
    else:
        # 낮 임베딩 파일이 없으면 밤 임베딩을 복사
        os.makedirs(os.path.dirname(day_user_embedding_path), exist_ok=True)
        with open(day_user_embedding_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_dict, f, ensure_ascii=False, indent=2)
        print(f"낮 임베딩 파일이 없어 밤 임베딩을 복사하여 생성: {day_user_embedding_path}")
    
    print("\n" + "=" * 80)
    print("밤 모델 학습 완료!")
    print("=" * 80)


def evaluate_model(
    model,
    test_ground_truth: Dict[str, Set[str]],
    user_id_to_index: Dict[str, int],
    item_id_to_index: Dict[str, int],
    index_to_user_id: Dict[int, str],
    index_to_item_id: Dict[int, str],
    num_items: int,
    k: int,
    device: str
) -> Dict[str, float]:
    """
    모델을 평가합니다.
    
    Args:
        model: 학습된 NeMF 모델
        test_ground_truth: 테스트 ground truth (user_id -> Set[item_id])
        user_id_to_index: 사용자 ID -> 인덱스 매핑
        item_id_to_index: 아이템 ID -> 인덱스 매핑
        index_to_user_id: 인덱스 -> 사용자 ID 매핑
        index_to_item_id: 인덱스 -> 아이템 ID 매핑
        num_items: 전체 아이템 수
        k: Top-K
        device: 디바이스
    
    Returns:
        Dict[str, float]: 평가 지표
    """
    model.eval()
    
    all_recommendations = {}
    
    # 각 사용자에 대해 추천 생성
    with torch.no_grad():
        for user_id, ground_truth_items in test_ground_truth.items():
            if user_id not in user_id_to_index:
                continue
            
            user_idx = user_id_to_index[user_id]
            
            # 모든 아이템에 대한 점수 계산
            user_tensor = torch.tensor([user_idx] * num_items, dtype=torch.long).to(device)
            item_tensor = torch.tensor(list(range(num_items)), dtype=torch.long).to(device)
            
            scores = model(user_tensor, item_tensor).cpu().numpy()
            
            # 점수 순으로 정렬
            item_indices = np.argsort(scores)[::-1]  # 내림차순
            
            # 아이템 ID로 변환
            recommendations = [index_to_item_id[idx] for idx in item_indices]
            all_recommendations[user_id] = recommendations
    
    # 평가
    metrics = evaluate_recommendations(all_recommendations, test_ground_truth, k)
    
    model.train()
    return metrics


if __name__ == "__main__":
    train_night_model()

