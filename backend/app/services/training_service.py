import torch
import torch.nn as nn
import torch.optim as optim
from sqlalchemy.orm import Session
from sqlalchemy import select, text, tuple_
import numpy as np
import logging
import os

from app.db.database import SessionLocal
from app.models.user_coordi_interaction import UserCoordiInteraction
from app.models.user_embedding import UserEmbedding
from app.models.item_embedding import ItemEmbedding
from app.ml.neumf_model import NeMF

logger = logging.getLogger(__name__)

class NightModelTrainer:
    def __init__(self, db: Session):
        self.db = db
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
    def train(self, epochs=5, batch_size=256, embedding_dim=512):
        logger.info("[Training] Initializing Incremental Training...")
        
        # 1. 체크포인트 로드 (Model + Mappings)
        # 파일 절대 경로를 기준으로 backend 루트 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/app/services
        backend_dir = os.path.dirname(os.path.dirname(current_dir)) # .../backend
        base_dir = os.path.join(backend_dir, "data", "model_artifacts")
        
        checkpoint_path = os.path.join(base_dir, "neumf_night_model.pth")
        
        existing_checkpoint = None
        if os.path.exists(checkpoint_path):
            try:
                existing_checkpoint = torch.load(checkpoint_path, map_location=self.device)
                logger.info(f"[Training] Found existing checkpoint at {checkpoint_path}")
            except Exception as e:
                logger.warning(f"[Training] Failed to load checkpoint: {e}. Starting from scratch.")
        
        # 2. 신규 데이터 로드 (is_trained=False)
        # like, preference 만 Positive로 간주
        stmt = select(UserCoordiInteraction).where(
            UserCoordiInteraction.action_type.in_(['like', 'preference']),
            UserCoordiInteraction.is_trained == False
        )
        new_interactions = self.db.execute(stmt).scalars().all()
        
        if not new_interactions:
            logger.info("[Training] No new interactions found (is_trained=False). Skipping training.")
            return

        # 3. ID 매핑 업데이트 (Dynamic Resize 준비)
        # 기존 매핑 로드
        if existing_checkpoint:
            user_id_to_index = existing_checkpoint['user_id_to_index'] # str(uid) -> idx
            item_id_to_index = existing_checkpoint['item_id_to_index'] # str(iid) -> idx
            num_users = existing_checkpoint['num_users']
            num_items = existing_checkpoint['num_items']
        else:
            user_id_to_index = {}
            item_id_to_index = {}
            num_users = 0
            num_items = 0
            
        # 신규 ID 식별 및 매핑 추가
        train_data = [] # (u_idx, i_idx)
        interaction_ids_to_mark = []
        
        # 현재 데이터셋에서의 최대 인덱스 추적
        current_max_user_idx = num_users - 1
        current_max_item_idx = num_items - 1
        
        for interaction in new_interactions:
            uid_str = str(interaction.user_id)
            iid_str = str(interaction.coordi_id)
            
            # User Mapping
            if uid_str not in user_id_to_index:
                current_max_user_idx += 1
                user_id_to_index[uid_str] = current_max_user_idx
            
            # Item Mapping
            if iid_str not in item_id_to_index:
                current_max_item_idx += 1
                item_id_to_index[iid_str] = current_max_item_idx
                
            u_idx = user_id_to_index[uid_str]
            i_idx = item_id_to_index[iid_str]
            
            train_data.append((u_idx, i_idx))
            # 학습에 사용된 Interaction ID 수집 (복합키: user_id, coordi_id)
            interaction_ids_to_mark.append((interaction.user_id, interaction.coordi_id))
            
        # 업데이트된 차원 수
        new_num_users = current_max_user_idx + 1
        new_num_items = current_max_item_idx + 1
        
        logger.info(f"[Training] New Data Split: {len(train_data)} interactions.")
        logger.info(f"[Training] Dimensions: Users {num_users} -> {new_num_users}, Items {num_items} -> {new_num_items}")

        # 4. 모델 초기화 및 가중치 로드 (Resize 포함)
        model = NeMF(new_num_users, new_num_items, embedding_dim=embedding_dim).to(self.device)
        
        if existing_checkpoint:
            self._load_and_resize_model(model, existing_checkpoint, new_num_users, new_num_items)
        else:
            logger.info("[Training] Created new model from scratch.")
            
        model.train()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        # 5. 학습 루프 (BPR) - 신규 데이터에 대해서만 (Fine-tuning)
        # Catastrophic Forgetting 방지를 위해 Old Data를 섞으면 좋지만, 
        # 현재 요청사항은 "is_trained=False만" 학습하는 것임.
        logger.info("[Training] Start Incremental BPR Training...")
        
        for epoch in range(epochs):
            total_loss = 0
            np.random.shuffle(train_data)
            
            num_batches = len(train_data) // batch_size
            
            # 데이터가 적을 경우 최소 1번은 돌도록
            if num_batches == 0:
                num_batches = 1
            
            for i in range(num_batches):
                start = i * batch_size
                end = min((i + 1) * batch_size, len(train_data))
                if start >= end: break # Safety check
                
                batch = train_data[start:end]
                u_batch = [x[0] for x in batch]
                i_batch = [x[1] for x in batch]
                
                # Negative Sampling
                j_batch = []
                for _ in range(len(batch)):
                    # 전체 아이템 범위 내에서 랜덤 샘플링
                    neg_item = np.random.randint(0, new_num_items)
                    j_batch.append(neg_item)
                
                u_tensor = torch.tensor(u_batch, dtype=torch.long).to(self.device)
                i_tensor = torch.tensor(i_batch, dtype=torch.long).to(self.device)
                j_tensor = torch.tensor(j_batch, dtype=torch.long).to(self.device)
                
                # Forward
                pos_probs = model.forward(u_tensor, i_tensor)
                neg_probs = model.forward(u_tensor, j_tensor)
                
                # BPR Loss
                pos_probs = torch.clamp(pos_probs, min=1e-7, max=1.0-1e-7)
                neg_probs = torch.clamp(neg_probs, min=1e-7, max=1.0-1e-7)
                
                pos_scores = torch.log(pos_probs / (1 - pos_probs))
                neg_scores = torch.log(neg_probs / (1 - neg_probs))
                
                loss = -torch.mean(torch.log(torch.sigmoid(pos_scores - neg_scores) + 1e-10))
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            logger.info(f"[Training] Epoch {epoch+1}/{epochs} Loss: {total_loss:.4f}")

        # 6. is_trained = True 마킹
        self._mark_as_trained(interaction_ids_to_mark)

        # 7. 저장 (DB & File)
        # 역매핑 생성 (저장용)
        # user_map, item_map은 원래 (DB ID -> Index) 였지만, 여기선 str(DB ID) -> Index 로 관리됨
        # save_embeddings와 save_checkpoint는 이 구조에 맞춰야 함
        
        # 호환성을 위해 int 키로 변환한 맵 생성 (save_embeddings용)
        user_map_int = {int(k): v for k, v in user_id_to_index.items()}
        item_map_int = {int(k): v for k, v in item_id_to_index.items()}
        
        self.save_embeddings(model, user_map_int, item_map_int)
        self.save_checkpoint(model, user_id_to_index, item_id_to_index, embedding_dim)
        
    def _load_and_resize_model(self, model, checkpoint, new_num_users, new_num_items):
        """
        기존 모델 가중치를 로드하되, 크기가 늘어난 경우(새 유저/아이템) 
        기존 가중치는 복사하고 늘어난 부분만 초기화 상태로 유지합니다.
        """
        old_state_dict = checkpoint['model_state_dict']
        model_state_dict = model.state_dict()
        
        logger.info("[Training] Loading and resizing model weights...")
        
        # Embedding Layer Resize 로직
        for name, param in old_state_dict.items():
            if name not in model_state_dict:
                continue
                
            if 'embedding' in name:
                # 예: user_embedding.weight (num_users, dim)
                old_tensor = param
                new_tensor = model_state_dict[name]
                
                # 차원이 다르면 (늘어났으면) 복사
                if old_tensor.shape != new_tensor.shape:
                    # 앞부분(기존 ID)만 복사
                    # user, item 임베딩은 보통 (N, dim) 형태
                    n_old = old_tensor.shape[0]
                    n_new = new_tensor.shape[0]
                    dim = old_tensor.shape[1]
                    
                    # 안전장치: 기존 크기만큼만 복사
                    n_copy = min(n_old, n_new)
                    new_tensor[:n_copy, :] = old_tensor[:n_copy, :]
                    
                    # 나머지(새 ID)는 이미 초기화된 상태 (NeMF init에서 처리됨)
                    # 모델 state_dict에 반영
                    model_state_dict[name] = new_tensor
                    logger.info(f"  - Resized {name}: {old_tensor.shape} -> {new_tensor.shape}")
                else:
                    model_state_dict[name] = old_tensor
            else:
                # MLP Layer 등은 그대로 복사 (단, hidden dims가 바뀌지 않았다는 가정)
                if param.shape == model_state_dict[name].shape:
                    model_state_dict[name] = param
                else:
                    logger.warning(f"  - Skipping {name} due to shape mismatch: {param.shape} vs {model_state_dict[name].shape}")

        model.load_state_dict(model_state_dict)
        logger.info("[Training] Model weights loaded successfully.")

    def _mark_as_trained(self, interaction_ids):
        """
        학습에 사용된 인터랙션을 is_trained=True로 업데이트
        interaction_ids: List of (user_id, coordi_id) tuples
        대량 데이터 처리를 위해 Chunk 단위로 업데이트합니다.
        """
        if not interaction_ids:
            return
            
        chunk_size = 1000
        total_marked = 0
        
        try:
            for i in range(0, len(interaction_ids), chunk_size):
                chunk = interaction_ids[i : i + chunk_size]
                
                stmt = (
                    UserCoordiInteraction.__table__.update()
                    .where(
                        tuple_(UserCoordiInteraction.user_id, UserCoordiInteraction.coordi_id).in_(chunk)
                    )
                    .values(is_trained=True)
                )
                self.db.execute(stmt)
                total_marked += len(chunk)
                
            self.db.commit()
            logger.info(f"[Training] Marked {total_marked} interactions as trained.")
            
        except Exception as e:
            logger.error(f"[Training] Failed to mark interactions as trained: {e}")
            self.db.rollback()

    def save_embeddings(self, model, user_map, item_map):
        logger.info("[Training] Saving embeddings to DB...")
        model.eval()
        
        with torch.no_grad():
            u_weights = model.user_embedding.weight.cpu().numpy().tolist()
            i_weights = model.item_embedding.weight.cpu().numpy().tolist()
            
        try:
            # Upsert User Embeddings
            for uid, idx in user_map.items():
                 vector = u_weights[idx]
                 self._upsert_user(uid, 'night_v1', vector)
                 self._upsert_user(uid, 'day_v1', vector)
                 
            # Upsert Item Embeddings
            for iid, idx in item_map.items():
                vector = i_weights[idx]
                self._upsert_item(iid, 'night_v1', vector)
            
            self.db.commit()
            logger.info("[Training] All embeddings saved successfully.")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"[Training] Failed to save embeddings: {e}")

    def save_checkpoint(self, model, user_id_to_index, item_id_to_index, embedding_dim):
        """
        모델 체크포인트 저장 (덮어쓰기)
        """
        # 파일 절대 경로를 기준으로 backend 루트 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/app/services
        backend_dir = os.path.dirname(os.path.dirname(current_dir)) # .../backend
        base_dir = os.path.join(backend_dir, "data", "model_artifacts")
        
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
            
        save_path = os.path.join(base_dir, "neumf_night_model.pth")
        
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'user_id_to_index': user_id_to_index,
            'item_id_to_index': item_id_to_index,
            'num_users': len(user_id_to_index),
            'num_items': len(item_id_to_index),
            'embedding_dim': embedding_dim,
            'hidden_dims': [128]
        }
        
        try:
            torch.save(checkpoint, save_path)
            logger.info(f"[Training] Model checkpoint updated at {save_path}")
        except Exception as e:
            logger.error(f"[Training] Failed to save model checkpoint: {e}")

    def _upsert_user(self, user_id, version, vector):
        embedding = self.db.get(UserEmbedding, (user_id, version))
        if not embedding:
            embedding = UserEmbedding(
                user_id=user_id, 
                model_version=version, 
                vector=vector
            )
            self.db.add(embedding)
        else:
            embedding.vector = vector

    def _upsert_item(self, coordi_id, version, vector):
        embedding = self.db.get(ItemEmbedding, (coordi_id, version))
        if not embedding:
            embedding = ItemEmbedding(
                coordi_id=coordi_id, 
                model_version=version, 
                vector=vector
            )
            self.db.add(embedding)
        else:
            embedding.vector = vector

def run_night_training():
    """
    스케줄러에서 호출하는 엔트리 포인트
    """
    logger.info("Initializing Night Training Service...")
    db = SessionLocal()
    try:
        trainer = NightModelTrainer(db)
        # 실전: 에폭을 적당히 늘려줍니다 (증분 학습이므로 적은 에폭으로도 충분할 수 있음)
        trainer.train(epochs=5, batch_size=64)
    except Exception as e:
        logger.error(f"Night training failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
