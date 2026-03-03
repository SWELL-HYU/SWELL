import json
import numpy as np
import sys
import os
import csv
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
from sklearn.metrics.pairwise import cosine_similarity

# 같은 디렉토리에서 실행할 때를 위한 경로 조정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from Data.cold_start import (
        load_embeddings_from_json,
        get_image_embedding_sum_from_outfit_ids,
        VERBOSE,
        search_similar_outfits,
        get_embedding
    )
except ImportError:
    # 같은 디렉토리에서 실행할 때
    from data.src.inference.cold_start import (
        load_embeddings_from_json,
        get_image_embedding_sum_from_outfit_ids,
        VERBOSE,
        search_similar_outfits,
        get_embedding
    )


class InteractiveRecommendationSystem:
    """
    상호작용 기반 추천 시스템
    
    알고리즘:
    1. user_id를 읽고 interaction == None이면 콜드 스타트 기반으로 이미지 임베딩 5개를 합함(평균)
    2. 가장 가까운 30개 코디 추출
    3. 사용자가 상호작용함
    4. 상호작용을 기록하고 상호작용으로 계산해서 사용자 벡터를 이동시킴
    5. 상호작용이 기록된 벡터는 제외하고 다른 30개 코디 추출
    6. 반복
    """
    
    def __init__(
        self,
        json_file: str = "data/raw/final_data_남자_겨울_temp.json",
        weight_like: float = 1.0,
        weight_preference: float = 2.0,
        weight_skip: float = -0.5,
        n_recommendations: int = 30,
        cold_start_outfit_ids: Optional[List[str]] = None
    ):
        """
        Args:
            json_file: 코디 데이터가 있는 JSON 파일 경로
            weight_like: like 상호작용의 가중치
            weight_preference: preference 상호작용의 가중치
            weight_skip: skip 상호작용의 가중치 (보통 음수)
            n_recommendations: 추천할 코디 개수 (기본값: 30)
            cold_start_outfit_ids: 콜드 스타트용 outfit_id 리스트 (5개)
        """
        self.json_file = json_file
        self.weight_like = weight_like
        self.weight_preference = weight_preference
        self.weight_skip = weight_skip
        self.n_recommendations = n_recommendations
        
        # 데이터 로드
        self.data, self.embeddings_matrix = load_embeddings_from_json(json_file)
        self.outfit_id_to_index = {
            str(item['outfit_id']): idx 
            for idx, item in enumerate(self.data)
        }
        
        # 사용자별 상태 저장
        self.user_vectors: Dict[str, np.ndarray] = {}  # user_id -> user_vector
        self.user_interactions: Dict[str, Set[str]] = {}  # user_id -> set of interacted outfit_ids
        self.user_shown_outfits: Dict[str, List[str]] = {}  # user_id -> list of shown outfit_ids (상호작용하지 않은 것 포함)
        self.cold_start_outfit_ids = cold_start_outfit_ids
        
        # CSV 파일 경로 설정
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_file = os.path.join(script_dir, "warm_start", "user_outfit_interaction.csv")
        self.view_time_csv_file = os.path.join(script_dir, "warm_start", "user_outfit_view_time.csv")
        
        # 낮 모델 임베딩 저장 경로
        self.day_user_embedding_path = os.path.join(script_dir, "warm_start", "day_user_embedding.json")
        
        # 밤 모델 임베딩 경로 (초기값으로 사용)
        self.night_user_embedding_path = os.path.join(script_dir, "warm_start", "night_user_embedding.json")
        
        # CSV 파일이 없으면 생성
        if not os.path.exists(self.csv_file):
            os.makedirs(os.path.dirname(self.csv_file), exist_ok=True)
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['user_id', 'outfit_id', 'interaction', 'trained'])
        
        if not os.path.exists(self.view_time_csv_file):
            os.makedirs(os.path.dirname(self.view_time_csv_file), exist_ok=True)
            with open(self.view_time_csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['user_id', 'outfit_id', 'view_time_seconds'])
        
        # 사용자별 코디 보여준 시간 추적 (user_id -> {outfit_id: start_time})
        self.outfit_view_start_times: Dict[str, Dict[str, float]] = {}
        
        # user_embedding_utils 함수들을 인라인화 (더 이상 import 불필요)
        
        if VERBOSE:
            print(f"Loaded {len(self.data)} outfits")
            print(f"Weights - Like: {weight_like}, Preference: {weight_preference}, Skip: {weight_skip}")
    
    def initialize_user_vector(self, user_id: str, cold_start_outfit_ids: Optional[List[str]] = None) -> np.ndarray:
        """
        사용자 벡터를 초기화합니다 (콜드 스타트).
        
        Args:
            user_id: 사용자 ID
            cold_start_outfit_ids: 콜드 스타트용 outfit_id 리스트 (5개). None이면 self.cold_start_outfit_ids 사용
        
        Returns:
            초기화된 사용자 벡터
        """
        if cold_start_outfit_ids is None:
            cold_start_outfit_ids = self.cold_start_outfit_ids
        
        if cold_start_outfit_ids is None or len(cold_start_outfit_ids) == 0:
            raise ValueError("콜드 스타트를 위해 최소 5개의 outfit_id가 필요합니다.")
        
        if len(cold_start_outfit_ids) != 5:
            if VERBOSE:
                print(f"Warning: 콜드 스타트 outfit_id가 5개가 아닙니다 ({len(cold_start_outfit_ids)}개). 평균을 계산합니다.")
        
        # 5개 코디의 description_embedding 합산
        image_embedding_sum = get_image_embedding_sum_from_outfit_ids(
            cold_start_outfit_ids, 
            self.json_file
        )
        
        # 평균 계산 (5로 나눔)
        user_vector = image_embedding_sum / len(cold_start_outfit_ids)
        
        # 정규화
        norm = np.linalg.norm(user_vector)
        if norm > 0:
            user_vector = user_vector / norm
        
        self.user_vectors[user_id] = user_vector
        self.user_interactions[user_id] = set()
        
        if VERBOSE:
            print(f"User {user_id} initialized with cold start (5 outfits)")
        
        return user_vector
    
    def get_user_vector(self, user_id: str, cold_start_outfit_ids: Optional[List[str]] = None) -> np.ndarray:
        """
        사용자 벡터를 가져옵니다. 없으면 밤 임베딩에서 로드하거나 초기화합니다.
        
        Args:
            user_id: 사용자 ID
            cold_start_outfit_ids: 콜드 스타트용 outfit_id 리스트 (없을 경우)
        
        Returns:
            사용자 벡터
        """
        if user_id not in self.user_vectors:
            # 먼저 낮 임베딩에서 로드 시도
            if os.path.exists(self.day_user_embedding_path):
                with open(self.day_user_embedding_path, 'r', encoding='utf-8') as f:
                    day_embeddings = json.load(f)
                if user_id in day_embeddings:
                    self.user_vectors[user_id] = np.array(day_embeddings[user_id])
                    if VERBOSE:
                        print(f"User {user_id} loaded from day embedding")
                    return self.user_vectors[user_id]
            
            # 낮 임베딩이 없으면 밤 임베딩에서 로드 시도
            if os.path.exists(self.night_user_embedding_path):
                with open(self.night_user_embedding_path, 'r', encoding='utf-8') as f:
                    night_embeddings = json.load(f)
                if user_id in night_embeddings:
                    self.user_vectors[user_id] = np.array(night_embeddings[user_id])
                    if VERBOSE:
                        print(f"User {user_id} loaded from night embedding (initialized day embedding)")
                    return self.user_vectors[user_id]
            
            # 밤 임베딩도 없으면 콜드 스타트로 초기화
            self.initialize_user_vector(user_id, cold_start_outfit_ids)
        return self.user_vectors[user_id]
    
    def recommend_outfits(
        self, 
        user_id: str, 
        exclude_interacted: bool = True,
        exclude_shown: bool = False,  # 상호작용하지 않은 보여준 코디도 제외할지 여부
        cold_start_outfit_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        사용자에게 코디를 추천합니다.
        
        Args:
            user_id: 사용자 ID
            exclude_interacted: 상호작용한 코디를 제외할지 여부
            exclude_shown: 상호작용하지 않은 보여준 코디도 제외할지 여부 (False면 다음 검색에 포함)
            cold_start_outfit_ids: 콜드 스타트용 outfit_id 리스트 (없을 경우)
        
        Returns:
            추천된 코디 리스트 (similarity_score 포함)
        """
        # 사용자 벡터 가져오기
        user_vector = self.get_user_vector(user_id, cold_start_outfit_ids)
        user_vector = user_vector.reshape(1, -1)
        
        # 코사인 유사도 계산
        similarities = cosine_similarity(user_vector, self.embeddings_matrix)[0]
        
        # 제외할 인덱스 집합
        exclude_indices = set()
        
        # 상호작용한 코디 제외
        if exclude_interacted and user_id in self.user_interactions:
            interacted_indices = {
                self.outfit_id_to_index.get(str(oid))
                for oid in self.user_interactions[user_id]
                if str(oid) in self.outfit_id_to_index
            }
            exclude_indices.update(interacted_indices)
        
        # 상호작용하지 않은 보여준 코디 제외 (옵션)
        if exclude_shown and user_id in self.user_shown_outfits:
            shown_indices = {
                self.outfit_id_to_index.get(str(oid))
                for oid in self.user_shown_outfits[user_id]
                if str(oid) in self.outfit_id_to_index
            }
            exclude_indices.update(shown_indices)
        
        # 제외할 인덱스의 유사도를 매우 낮게 설정
        for idx in exclude_indices:
            if idx is not None:
                similarities[idx] = -1.0
        
        # 유사도가 높은 순으로 정렬
        top_indices = np.argsort(similarities)[::-1][:self.n_recommendations]
        
        # 결과 생성
        results = []
        for idx in top_indices:
            outfit = self.data[idx].copy()
            outfit['similarity_score'] = float(similarities[idx])
            results.append(outfit)
        
        return results
    
    def record_interaction(
        self,
        user_id: str,
        outfit_id: str,
        interaction_type: str,
        cold_start_outfit_ids: Optional[List[str]] = None,
        save_to_csv: bool = True,
        view_time_seconds: Optional[float] = None
    ):
        """
        사용자의 상호작용을 기록하고 사용자 벡터를 업데이트합니다.
        [수정됨] 학습률(Learning Rate)을 적용하여 벡터가 급격하게 튀는 것을 방지합니다.
        view_time_seconds가 제공되면 이를 기반으로 가중치를 조정합니다.
        
        Args:
            user_id: 사용자 ID
            outfit_id: 상호작용한 코디 ID
            interaction_type: 상호작용 타입 ('like', 'preference', 'skip')
            cold_start_outfit_ids: 콜드 스타트용 outfit_id 리스트 (없을 경우)
            save_to_csv: CSV 파일에 저장할지 여부
            view_time_seconds: 시청 시간 (초). None이면 자동 계산
        """
        # view_time 계산 (제공되지 않았으면 시작 시간에서 계산)
        if view_time_seconds is None:
            if (user_id in self.outfit_view_start_times and 
                str(outfit_id) in self.outfit_view_start_times[user_id]):
                start_time = self.outfit_view_start_times[user_id][str(outfit_id)]
                view_time_seconds = datetime.now().timestamp() - start_time
            else:
                # 시작 시간이 없으면 기본값 사용 (interaction_type에 따라)
                if interaction_type == 'like':
                    view_time_seconds = 15.0  # 평균 like 시간
                elif interaction_type == 'skip':
                    view_time_seconds = 3.0   # 평균 skip 시간
                else:
                    view_time_seconds = 0.0   # preference는 시간 없음
        
        # 사용자 벡터 가져오기
        user_vector = self.get_user_vector(user_id, cold_start_outfit_ids)
        
        # outfit_id로 인덱스 찾기
        outfit_idx = self.outfit_id_to_index.get(str(outfit_id))
        if outfit_idx is None:
            raise ValueError(f"Outfit ID {outfit_id}를 찾을 수 없습니다.")
        
        # 코디의 임베딩 가져오기
        outfit_embedding = self.embeddings_matrix[outfit_idx].copy()
        
        # 가중치 결정 (view_time을 고려하여 조정)
        if interaction_type == 'like':
            base_weight = self.weight_like
            # view_time이 길수록 가중치 증가 (5-30초 범위)
            # 5초 미만이면 가중치 감소, 30초 이상이면 최대 가중치
            if view_time_seconds < 5:
                time_multiplier = 0.5 + (view_time_seconds / 5) * 0.5  # 0.5 ~ 1.0
            elif view_time_seconds > 30:
                time_multiplier = 1.5  # 최대 1.5배
            else:
                time_multiplier = 1.0 + ((view_time_seconds - 5) / 25) * 0.5  # 1.0 ~ 1.5
            weight = base_weight * time_multiplier
        elif interaction_type == 'preference':
            weight = self.weight_preference
            # preference는 시간과 무관하게 고정 가중치
        elif interaction_type == 'skip':
            base_weight = self.weight_skip
            # view_time이 짧을수록 가중치 증가 (1-5초 범위)
            # 1초 미만이면 최대 음수 가중치, 5초 이상이면 가중치 감소
            if view_time_seconds < 1:
                time_multiplier = 1.5  # 최대 음수 효과
            elif view_time_seconds > 5:
                time_multiplier = 0.5  # 가중치 감소
            else:
                time_multiplier = 1.5 - ((view_time_seconds - 1) / 4) * 1.0  # 1.5 ~ 0.5
            weight = base_weight * time_multiplier
        else:
            raise ValueError(f"Unknown interaction type: {interaction_type}")
        
        # -------------------------------------------------------------------------
        # [CRITICAL FIX] 벡터 연산 로직 수정
        # 기존: user_vector + weight * outfit_embedding (너무 급격한 변화)
        # 수정: Learning Rate(학습률) 적용 + 정규화 유지
        # -------------------------------------------------------------------------
        
        # 학습률 설정 (0.1 ~ 0.2 권장): 한 번의 행동이 전체 취향의 15% 정도를 수정하도록 설정
        # 이 값이 클수록 최근 행동에 민감하고, 작을수록 과거 취향을 오래 유지함
        LEARNING_RATE = 0.15 
        
        # 업데이트 벡터 계산 (방향 * 가중치 * 학습률)
        # 예: Like(1.0) -> 아이템 방향으로 0.15만큼 이동
        # 예: Skip(-0.5) -> 아이템 반대 방향으로 0.075만큼 이동
        update_delta = LEARNING_RATE * weight * outfit_embedding
        
        # 사용자 벡터 업데이트
        new_user_vector = user_vector + update_delta
        
        # 정규화 (Normalization) - 벡터의 크기를 1로 유지하여 방향성만 남김
        norm = np.linalg.norm(new_user_vector)
        if norm > 0:
            user_vector = new_user_vector / norm
        else:
            # 만약 상쇄되어 0이 되면 기존 벡터 유지 (희박한 케이스)
            pass
            
        # -------------------------------------------------------------------------

        # 업데이트
        self.user_vectors[user_id] = user_vector
        
        # 상호작용 기록
        if user_id not in self.user_interactions:
            self.user_interactions[user_id] = set()
        self.user_interactions[user_id].add(str(outfit_id))
        
        # CSV 파일에 저장
        if save_to_csv:
            # interaction CSV 저장 (trained=False로 저장, 아직 학습되지 않음)
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([user_id, outfit_id, interaction_type, 'False'])
            
            # view_time CSV 저장 (preference는 제외)
            if interaction_type != 'preference':
                with open(self.view_time_csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([user_id, outfit_id, int(view_time_seconds)])
        
        # 낮 모델 임베딩 저장 (실시간 업데이트)
        # 밤 모델 임베딩은 건들지 않음
        self._save_day_user_embedding(user_id, user_vector)
        
        # 보여준 코디 목록에서 제거
        if user_id in self.user_shown_outfits:
            if str(outfit_id) in self.user_shown_outfits[user_id]:
                self.user_shown_outfits[user_id].remove(str(outfit_id))
        
        # 시작 시간 기록 제거
        if user_id in self.outfit_view_start_times:
            if str(outfit_id) in self.outfit_view_start_times[user_id]:
                del self.outfit_view_start_times[user_id][str(outfit_id)]
        
        if VERBOSE:
            print(f"User {user_id} interacted with {outfit_id}: {interaction_type} "
                  f"(view_time: {view_time_seconds:.1f}s, adjusted weight: {weight * LEARNING_RATE:.3f})")
    
    def _save_day_user_embedding(self, user_id: str, user_vector: np.ndarray):
        """
        낮 모델 유저 임베딩을 저장합니다.
        실시간으로 업데이트되며, 밤 모델 임베딩은 건들지 않습니다.
        
        Args:
            user_id: 사용자 ID
            user_vector: 업데이트된 사용자 벡터
        """
        # 기존 낮 모델 임베딩 로드
        if os.path.exists(self.day_user_embedding_path):
            with open(self.day_user_embedding_path, 'r', encoding='utf-8') as f:
                day_embeddings = json.load(f)
        else:
            day_embeddings = {}
        
        # 현재 유저 임베딩 업데이트
        day_embeddings[user_id] = user_vector.tolist() if isinstance(user_vector, np.ndarray) else user_vector
        
        # 저장
        os.makedirs(os.path.dirname(self.day_user_embedding_path), exist_ok=True)
        with open(self.day_user_embedding_path, 'w', encoding='utf-8') as f:
            json.dump(day_embeddings, f, ensure_ascii=False, indent=2)
    def show_outfit(self, user_id: str, outfit_id: str):
        """
        코디를 사용자에게 보여준 것을 기록합니다 (상호작용하지 않은 경우).
        보여준 시간을 기록하여 나중에 view_time 계산에 사용합니다.
        
        Args:
            user_id: 사용자 ID
            outfit_id: 보여준 코디 ID
        """
        if user_id not in self.user_shown_outfits:
            self.user_shown_outfits[user_id] = []
        
        # 이미 상호작용한 코디가 아니고, 이미 보여준 목록에 없으면 추가
        if user_id not in self.user_interactions or str(outfit_id) not in self.user_interactions[user_id]:
            if str(outfit_id) not in self.user_shown_outfits[user_id]:
                self.user_shown_outfits[user_id].append(str(outfit_id))
        
        # 보여준 시간 기록 (view_time 계산용)
        if user_id not in self.outfit_view_start_times:
            self.outfit_view_start_times[user_id] = {}
        self.outfit_view_start_times[user_id][str(outfit_id)] = datetime.now().timestamp()
    
    def update_weights(
        self,
        weight_like: Optional[float] = None,
        weight_preference: Optional[float] = None,
        weight_skip: Optional[float] = None
    ):
        """
        상호작용 가중치를 업데이트합니다.
        
        Args:
            weight_like: like 가중치 (None이면 변경 안 함)
            weight_preference: preference 가중치 (None이면 변경 안 함)
            weight_skip: skip 가중치 (None이면 변경 안 함)
        """
        if weight_like is not None:
            self.weight_like = weight_like
        if weight_preference is not None:
            self.weight_preference = weight_preference
        if weight_skip is not None:
            self.weight_skip = weight_skip
        
        if VERBOSE:
            print(f"Updated weights - Like: {self.weight_like}, Preference: {self.weight_preference}, Skip: {self.weight_skip}")
    
    def get_user_interaction_count(self, user_id: str) -> int:
        """사용자의 상호작용 개수를 반환합니다."""
        return len(self.user_interactions.get(user_id, set()))
    
    def reset_user(self, user_id: str):
        """사용자의 상태를 초기화합니다."""
        if user_id in self.user_vectors:
            del self.user_vectors[user_id]
        if user_id in self.user_interactions:
            del self.user_interactions[user_id]
        if VERBOSE:
            print(f"User {user_id} reset")


def simulate_interactive_recommendation(
    user_id: str,
    json_file: str = "data/raw/final_data_남자.json",
    cold_start_outfit_ids: Optional[List[str]] = None,
    weight_like: float = 1.0,
    weight_preference: float = 2.0,
    weight_skip: float = -0.5,
    n_iterations: int = 5,
    n_recommendations: int = 30
):
    """
    상호작용 기반 추천 시스템을 시뮬레이션합니다.
    
    Args:
        user_id: 사용자 ID
        json_file: 코디 데이터 JSON 파일 경로
        cold_start_outfit_ids: 콜드 스타트용 outfit_id 리스트 (5개)
        weight_like: like 가중치
        weight_preference: preference 가중치
        weight_skip: skip 가중치
        n_iterations: 반복 횟수
        n_recommendations: 추천 개수
    """
    # 시스템 초기화
    system = InteractiveRecommendationSystem(
        json_file=json_file,
        weight_like=weight_like,
        weight_preference=weight_preference,
        weight_skip=weight_skip,
        n_recommendations=n_recommendations,
        cold_start_outfit_ids=cold_start_outfit_ids
    )
    
    print(f"\n=== Interactive Recommendation System ===")
    print(f"User ID: {user_id}")
    print(f"Weights - Like: {weight_like}, Preference: {weight_preference}, Skip: {weight_skip}")
    print(f"Recommendations per iteration: {n_recommendations}")
    print(f"Total iterations: {n_iterations}\n")
    
    for iteration in range(n_iterations):
        print(f"\n--- Iteration {iteration + 1} ---")
        
        # 추천 받기
        recommendations = system.recommend_outfits(user_id, exclude_interacted=True)
        
        print(f"Recommended {len(recommendations)} outfits")
        print(f"Top 5 outfit IDs:")
        for i, outfit in enumerate(recommendations[:5], 1):
            print(f"  {i}. {outfit['outfit_id']} (similarity: {outfit['similarity_score']:.4f})")
        
        # 시뮬레이션: 첫 번째 추천에 대해 랜덤 상호작용
        if len(recommendations) > 0:
            import random
            first_outfit_id = recommendations[0]['outfit_id']
            
            # 랜덤 상호작용 (10% like, 90% skip)
            if random.random() < 0.1:
                interaction_type = 'like'
            else:
                interaction_type = 'skip'
            
            print(f"\nSimulated interaction: {interaction_type} on outfit {first_outfit_id}")
            system.record_interaction(user_id, first_outfit_id, interaction_type)
            print(f"Total interactions: {system.get_user_interaction_count(user_id)}")
    
    print(f"\n=== Simulation Complete ===")
    print(f"Total interactions recorded: {system.get_user_interaction_count(user_id)}")
    
    return system


if __name__ == "__main__":
    # 예시 사용법
    import sys
    import random
    
    # 사용자 ID 입력
    user_id = input("User ID를 입력하세요: ").strip()
    if not user_id:
        user_id = "test_user_1"
        print(f"Using default user ID: {user_id}")
    
    # 콜드 스타트: 해시태그와 이미지 임베딩 입력
    print("\n=== 콜드 스타트: 초기 코디 선택 ===")
    print("방법 1: 해시태그와 이미지 임베딩으로 검색 (추천)")
    print("방법 2: 직접 outfit_id 5개 입력")
    print("방법 3: 랜덤 선택")
    
    method = input("\n방법을 선택하세요 (1/2/3, 기본값: 1): ").strip()
    if not method:
        method = "1"
    
    cold_start_outfit_ids = None
    
    # JSON 파일 경로 결정 (현재 스크립트 위치 기준)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(script_dir, "male", "final_data_남자_겨울_temp.json")
    if not os.path.exists(json_file_path):
        json_file_path = os.path.join(script_dir, "male", "final_data_남자.json")
        if not os.path.exists(json_file_path):
            # 프로젝트 루트 기준으로 시도
            parent_dir = os.path.dirname(script_dir)
            json_file_path = os.path.join(parent_dir, "Data", "male", "final_data_남자_겨울_temp.json")
            if not os.path.exists(json_file_path):
                json_file_path = os.path.join(parent_dir, "Data", "male", "final_data_남자.json")
    
    if method == "1":
        # 방법 1: 콜드 스타트 검색 사용
        print("\n--- 콜드 스타트 검색 ---")
        json_file = json_file_path
        
        # 해시태그 입력
        text1 = input("해시태그를 모두 입력하세요 (공백/콤마로 구분): ").strip()
        if not text1:
            print("해시태그가 입력되지 않았습니다. 랜덤 선택으로 전환합니다.")
            method = "3"
        else:
            # outfit_ids 5개를 입력 받아 해당 코디의 description_embedding 을 합산
            ids_raw = input("콤마(,)로 구분된 outfit_id 5개를 입력하세요 (이미지 임베딩용): ").strip()
            if not ids_raw:
                print("outfit_id가 입력되지 않았습니다. 랜덤 선택으로 전환합니다.")
                method = "3"
            else:
                outfit_ids_for_embedding = [s.strip() for s in ids_raw.split(",") if s.strip()]
                
                if len(outfit_ids_for_embedding) < 5:
                    print(f"Warning: outfit_id가 5개보다 적습니다 ({len(outfit_ids_for_embedding)}개). 사용 가능한 것만 사용합니다.")
                
                try:
                    # 이미지 임베딩 합산
                    image_embedding_sum = get_image_embedding_sum_from_outfit_ids(
                        outfit_ids_for_embedding, 
                        json_file
                    )
                    
                    # 검색 실행 (상위 5개 추출)
                    print("\n검색 중...")
                    results = search_similar_outfits(
                        text1=text1,
                        text2=image_embedding_sum,
                        json_file=json_file,
                        n=5,
                    )
                    
                    # outfit_id만 추출
                    cold_start_outfit_ids = [str(outfit['outfit_id']) for outfit in results]
                    print(f"\n콜드 스타트로 선택된 outfit_id 5개:")
                    for i, outfit_id in enumerate(cold_start_outfit_ids, 1):
                        print(f"  {i}. {outfit_id}")
                    
                except Exception as e:
                    print(f"오류 발생: {e}")
                    print("랜덤 선택으로 전환합니다.")
                    method = "3"
    
    if method == "2" or cold_start_outfit_ids is None:
        # 방법 2: 직접 입력
        if method == "2":
            ids_input = input("\n콜드 스타트용 outfit_id 5개를 입력하세요 (콤마로 구분): ").strip()
            if ids_input:
                cold_start_outfit_ids = [s.strip() for s in ids_input.split(",") if s.strip()]
            else:
                print("입력이 없어 랜덤 선택으로 전환합니다.")
                method = "3"
    
    if method == "3" or cold_start_outfit_ids is None:
        # 방법 3: 랜덤 선택
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cold_start_outfit_ids = [str(item['outfit_id']) for item in random.sample(data, min(5, len(data)))]
        print(f"\n랜덤으로 선택된 outfit IDs: {cold_start_outfit_ids}")
    
    # 가중치 기본값 사용
    weight_like = 1.0
    weight_preference = 2.0
    weight_skip = -0.5
    print(f"\n가중치 설정 (기본값): Like={weight_like}, Preference={weight_preference}, Skip={weight_skip}")
    print(f"사용할 JSON 파일: {json_file_path}")
    
    # 시스템 초기화
    system = InteractiveRecommendationSystem(
        json_file=json_file_path,
        weight_like=weight_like,
        weight_preference=weight_preference,
        weight_skip=weight_skip,
        n_recommendations=30,
        cold_start_outfit_ids=cold_start_outfit_ids
    )
    
    # 사용자 초기화
    system.initialize_user_vector(user_id, cold_start_outfit_ids)
    
    # 인터랙티브 루프
    print("\n=== Interactive Recommendation System ===")
    print("Commands:")
    print("  'start' or 's' - Start showing outfits one by one")
    print("  'next' or 'n' - Show next outfit (if available)")
    print("  'like' or 'l' - Like current outfit")
    print("  'preference' or 'pref' or 'p' - Mark current outfit as preference")
    print("  'skip' or 'sk' - Skip current outfit")
    print("  'pass' or 'pass' - Pass current outfit (no interaction, will be shown again later)")
    print("  'weights' - Show current weights")
    print("  'update_weights <like> <preference> <skip>' - Update weights")
    print("  'interactions' - Show interaction count")
    print("  'quit' or 'q' - Exit\n")
    
    current_outfit = None
    current_outfit_queue = []
    
    while True:
        command = input("Command: ").strip().lower()
        
        if command in ['quit', 'q', 'exit']:
            break
        elif command in ['start', 's']:
            # 새로운 추천 받기 (상호작용하지 않은 보여준 코디는 포함)
            print("\n새로운 추천을 받는 중...")
            recommendations = system.recommend_outfits(user_id, exclude_interacted=True, exclude_shown=False)
            current_outfit_queue = recommendations
            print(f"추천된 코디 {len(recommendations)}개를 준비했습니다.")
            if len(current_outfit_queue) > 0:
                current_outfit = current_outfit_queue.pop(0)
                system.show_outfit(user_id, current_outfit['outfit_id'])
                print(f"\n=== 현재 코디 ===")
                print(f"Outfit ID: {current_outfit['outfit_id']}")
                print(f"Similarity: {current_outfit['similarity_score']:.4f}")
                print(f"Style: {current_outfit.get('style', 'N/A')}")
                print(f"Description: {current_outfit.get('description', 'N/A')[:100]}...")
            else:
                print("추천할 코디가 없습니다.")
                current_outfit = None
        elif command in ['next', 'n']:
            if len(current_outfit_queue) > 0:
                current_outfit = current_outfit_queue.pop(0)
                system.show_outfit(user_id, current_outfit['outfit_id'])
                print(f"\n=== 현재 코디 ===")
                print(f"Outfit ID: {current_outfit['outfit_id']}")
                print(f"Similarity: {current_outfit['similarity_score']:.4f}")
                print(f"Style: {current_outfit.get('style', 'N/A')}")
                print(f"Description: {current_outfit.get('description', 'N/A')[:100]}...")
            elif current_outfit is None:
                print("현재 보여줄 코디가 없습니다. 'start' 명령으로 새로운 추천을 받으세요.")
            else:
                print("큐에 더 이상 코디가 없습니다. 'start' 명령으로 새로운 추천을 받으세요.")
        elif command in ['like', 'l']:
            if current_outfit is None:
                print("현재 보여줄 코디가 없습니다.")
            else:
                outfit_id = current_outfit['outfit_id']
                try:
                    system.record_interaction(user_id, outfit_id, 'like')
                    print(f"✓ Like 상호작용이 기록되었습니다: {outfit_id}")
                    current_outfit = None
                    # 다음 코디 자동으로 보여주기
                    if len(current_outfit_queue) > 0:
                        current_outfit = current_outfit_queue.pop(0)
                        system.show_outfit(user_id, current_outfit['outfit_id'])
                        print(f"\n=== 다음 코디 ===")
                        print(f"Outfit ID: {current_outfit['outfit_id']}")
                        print(f"Similarity: {current_outfit['similarity_score']:.4f}")
                    else:
                        print("더 이상 보여줄 코디가 없습니다. 'start' 명령으로 새로운 추천을 받으세요.")
                except Exception as e:
                    print(f"Error: {e}")
        elif command in ['preference', 'pref', 'p']:
            if current_outfit is None:
                print("현재 보여줄 코디가 없습니다.")
            else:
                outfit_id = current_outfit['outfit_id']
                try:
                    system.record_interaction(user_id, outfit_id, 'preference')
                    print(f"✓ Preference 상호작용이 기록되었습니다: {outfit_id}")
                    current_outfit = None
                    # 다음 코디 자동으로 보여주기
                    if len(current_outfit_queue) > 0:
                        current_outfit = current_outfit_queue.pop(0)
                        system.show_outfit(user_id, current_outfit['outfit_id'])
                        print(f"\n=== 다음 코디 ===")
                        print(f"Outfit ID: {current_outfit['outfit_id']}")
                        print(f"Similarity: {current_outfit['similarity_score']:.4f}")
                    else:
                        print("더 이상 보여줄 코디가 없습니다. 'start' 명령으로 새로운 추천을 받으세요.")
                except Exception as e:
                    print(f"Error: {e}")
        elif command in ['skip', 'sk']:
            if current_outfit is None:
                print("현재 보여줄 코디가 없습니다.")
            else:
                outfit_id = current_outfit['outfit_id']
                try:
                    system.record_interaction(user_id, outfit_id, 'skip')
                    print(f"✓ Skip 상호작용이 기록되었습니다: {outfit_id}")
                    current_outfit = None
                    # 다음 코디 자동으로 보여주기
                    if len(current_outfit_queue) > 0:
                        current_outfit = current_outfit_queue.pop(0)
                        system.show_outfit(user_id, current_outfit['outfit_id'])
                        print(f"\n=== 다음 코디 ===")
                        print(f"Outfit ID: {current_outfit['outfit_id']}")
                        print(f"Similarity: {current_outfit['similarity_score']:.4f}")
                    else:
                        print("더 이상 보여줄 코디가 없습니다. 'start' 명령으로 새로운 추천을 받으세요.")
                except Exception as e:
                    print(f"Error: {e}")
        elif command in ['pass', 'pass']:
            if current_outfit is None:
                print("현재 보여줄 코디가 없습니다.")
            else:
                outfit_id = current_outfit['outfit_id']
                # 상호작용 없이 넘어감 (다음 검색에 포함됨)
                print(f"✓ 코디를 넘어갑니다 (상호작용 없음): {outfit_id}")
                print("이 코디는 다음 검색에도 포함됩니다.")
                current_outfit = None
                # 다음 코디 자동으로 보여주기
                if len(current_outfit_queue) > 0:
                    current_outfit = current_outfit_queue.pop(0)
                    system.show_outfit(user_id, current_outfit['outfit_id'])
                    print(f"\n=== 다음 코디 ===")
                    print(f"Outfit ID: {current_outfit['outfit_id']}")
                    print(f"Similarity: {current_outfit['similarity_score']:.4f}")
                else:
                    print("더 이상 보여줄 코디가 없습니다. 'start' 명령으로 새로운 추천을 받으세요.")
        elif command == 'weights':
            print(f"\nCurrent weights:")
            print(f"  Like: {system.weight_like}")
            print(f"  Preference: {system.weight_preference}")
            print(f"  Skip: {system.weight_skip}")
        elif command.startswith('update_weights '):
            parts = command.split()
            if len(parts) == 4:
                try:
                    like_w = float(parts[1])
                    pref_w = float(parts[2])
                    skip_w = float(parts[3])
                    system.update_weights(like_w, pref_w, skip_w)
                    print("Weights updated successfully")
                except ValueError:
                    print("Error: Invalid weight values")
            else:
                print("Usage: update_weights <like> <preference> <skip>")
        elif command == 'interactions':
            count = system.get_user_interaction_count(user_id)
            shown_count = len(system.user_shown_outfits.get(user_id, []))
            print(f"Total interactions: {count}")
            print(f"Shown but not interacted: {shown_count}")
        else:
            print("Unknown command. Type 'quit' to exit.")

