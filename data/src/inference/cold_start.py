import json
import numpy as np
from datetime import datetime
from typing import List, Tuple, Dict
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_MODEL = "sentence-transformers/distiluse-base-multilingual-cased-v2"

_model = None

VERBOSE = False

def get_model(model_name: str = None):
    """
    Sentence Transformer 모델을 로드합니다 (싱글톤 패턴).
    
    Args:
        model_name: 사용할 모델명 (None이면 기본 모델 사용)
    
    Returns:
        SentenceTransformer 모델
    """
    global _model
    if _model is None:
        if model_name is None:
            model_name = DEFAULT_MODEL
        if VERBOSE:
            print(f"Loading Sentence Transformer model: {model_name}")
            print("(This may take a few minutes on first run...)")
        _model = SentenceTransformer(model_name)
        if VERBOSE:
            print("Model loaded successfully!")
    return _model


def get_embedding(text: str, model_name: str = None) -> np.ndarray:
    """
    Sentence Transformer를 사용하여 텍스트의 임베딩 벡터를 생성합니다.
    
    Args:
        text: 임베딩할 텍스트
        model_name: 사용할 모델명 (None이면 기본 모델 사용)
    
    Returns:
        임베딩 벡터 (numpy array)
    """
    model = get_model(model_name)
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding


def create_query_embedding(
    hashtags_text: str,
    image_embedding: np.ndarray,
    text_weight: float = 10.0,
    model_name: str = None,
) -> np.ndarray:
    """
    해시태그 텍스트 임베딩과 이미지 임베딩 합을 결합한 쿼리 벡터를 생성합니다.
    """
    if VERBOSE:
        print("Creating query embedding:")
        print(f"  Hashtags text: {hashtags_text[:100]}...")
        print(f"  Image embedding shape: {image_embedding.shape}")

    # 해시태그 텍스트 임베딩
    hashtags_embedding = get_embedding(hashtags_text, model_name)

    # 두 임베딩 합산 (가중치 곱 5 제거: 단순 합)
    query_embedding = hashtags_embedding * text_weight + image_embedding

    # 정규화 (코사인 유사도 계산 시 필요)
    norm = np.linalg.norm(query_embedding)
    if norm > 0:
        query_embedding = query_embedding / norm

    return query_embedding


def load_embeddings_from_json(json_file: str) -> Tuple[List[Dict], np.ndarray]:
    """
    JSON 파일에서 데이터와 description_embedding을 로드합니다.
    """
    if VERBOSE:
        print(f"Loading embeddings from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    embeddings = []
    valid_indices = []
    
    for idx, item in enumerate(data):
        if "description_embedding" in item and item["description_embedding"] is not None:
            embeddings.append(item["description_embedding"])
            valid_indices.append(idx)
        else:
            if VERBOSE:
                print(f"Warning: Item {idx} (outfit_id: {item.get('outfit_id', 'unknown')}) has no description_embedding")
    
    if not embeddings:
        raise ValueError("No embeddings found in the JSON file. Please run generate_embeddings.py first.")
    
    embeddings_matrix = np.array(embeddings)
    if VERBOSE:
        print(f"Loaded {len(embeddings)} embeddings with dimension {embeddings_matrix.shape[1]}")
    
    # 정규화
    norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1  # 0으로 나누기 방지
    embeddings_matrix = embeddings_matrix / norms
    
    # 유효한 인덱스에 해당하는 데이터만 반환
    valid_data = [data[i] for i in valid_indices]
    
    return valid_data, embeddings_matrix


def get_image_embedding_sum_from_outfit_ids(
    outfit_ids: List[str],
    json_file: str,
) -> np.ndarray:
    """
    선택된 outfit_id들의 description_embedding 합을 반환합니다.
    """
    if VERBOSE:
        print(f"\n선택된 outfit_id들: {outfit_ids}")
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # outfit_id → item 매핑
    id_to_item = {
        str(item.get("outfit_id")): item
        for item in data
        if "outfit_id" in item
    }

    embeddings = []
    for oid in outfit_ids:
        item = id_to_item.get(str(oid))
        if item is None:
            if VERBOSE:
                print(f"Warning: outfit_id {oid} 를 JSON에서 찾을 수 없습니다.")
            continue
        emb = item.get("description_embedding")
        if emb is None:
            if VERBOSE:
                print(f"Warning: outfit_id {oid} 에 description_embedding 이 없습니다.")
            continue
        embeddings.append(np.array(emb, dtype=float))

    if not embeddings:
        raise ValueError("선택한 outfit_id들에 대해 사용할 수 있는 description_embedding 이 없습니다.")

    image_embedding_sum = np.sum(embeddings, axis=0)
    if VERBOSE:
        print(f"선택한 이미지 임베딩 {len(embeddings)}개를 합산했습니다. shape = {image_embedding_sum.shape}")
    return image_embedding_sum


def get_season_from_month(month: int) -> str:
    """
    월(month)을 기준으로 한국어 season 레이블을 반환합니다.
    """
    if month in (12, 1, 2):
        return "겨울"
    if month in (3, 4, 5):
        return "봄"
    if month in (6, 7, 8):
        return "여름"
    return "가을"


def filter_data_by_season(
    data: List[Dict],
    embeddings_matrix: np.ndarray,
    season: str,
) -> Tuple[List[Dict], np.ndarray]:
    """
    특정 season 값에 해당하는 데이터와 임베딩만 필터링합니다.
    """
    indices = [i for i, item in enumerate(data) if item.get("season") == season]

    if not indices:
        if VERBOSE:
            print(f"Warning: season == '{season}' 인 데이터가 없습니다. 전체 데이터로 검색합니다.")
        return data, embeddings_matrix

    filtered_data = [data[i] for i in indices]
    filtered_embeddings = embeddings_matrix[indices]

    if VERBOSE:
        print(f"Season 필터 적용: '{season}' → {len(filtered_data)}개 outfit 사용")
    return filtered_data, filtered_embeddings


def find_similar_outfits(
    query_embedding: np.ndarray,
    data: List[Dict],
    embeddings_matrix: np.ndarray,
    n: int = 10
) -> List[Dict]:
    """
    쿼리 임베딩과 가장 유사한 n개의 outfit을 찾습니다.
    """
    # 쿼리 임베딩을 2D 배열로 변환
    query_embedding = query_embedding.reshape(1, -1)
    
    # 코사인 유사도 계산
    similarities = cosine_similarity(query_embedding, embeddings_matrix)[0]
    
    # 유사도가 높은 순으로 정렬
    top_indices = np.argsort(similarities)[::-1][:n]
    
    # 결과 생성
    results = []
    for idx in top_indices:
        outfit = data[idx].copy()
        outfit['similarity_score'] = float(similarities[idx])
        results.append(outfit)
    
    return results


def search_similar_outfits(
    text1: str,
    text2: np.ndarray,
    json_file: str = "data/raw/final_data_남자.json",
    n: int = 10,
    model_name: str = None
) -> List[Dict]:
    """
    해시태그와 이미지 임베딩을 기반으로 유사한 outfit을 검색합니다.
    """
    # 1. 쿼리 임베딩 생성
    if VERBOSE:
        print("\n=== Step 1: Creating query embedding ===")
    # model_name 은 키워드 인자로 넘겨서 text_weight 위치와 섞이지 않도록 함
    query_embedding = create_query_embedding(text1, text2, model_name=model_name)

    # 2. JSON 파일에서 임베딩 로드
    if VERBOSE:
        print("\n=== Step 2: Loading outfit embeddings ===")
    data, embeddings_matrix = load_embeddings_from_json(json_file)

    # 2-1. 현재 날짜 기준 season 필터 적용
    current_month = datetime.now().month
    current_season = get_season_from_month(current_month)
    if VERBOSE:
        print(f"\n현재 월: {current_month}, 현재 season 판정: {current_season}")

    # 현재 season 에 해당하는 데이터만 사용
    data, embeddings_matrix = filter_data_by_season(data, embeddings_matrix, current_season)

    # 3. 유사도 검색
    if VERBOSE:
        print(f"\n=== Step 3: Finding top {n} similar outfits ===")
    results = find_similar_outfits(query_embedding, data, embeddings_matrix, n)
    
    return results


def print_results(results: List[Dict], n: int = None):
    """
    검색 결과를 출력합니다.
    
    Args:
        results: 검색 결과 리스트
        n: 출력할 개수 (None이면 모두 출력)
    """
    if n is None:
        n = len(results)
    
    print(f"\n=== Top {n} Similar Outfits ===")
    print("=" * 80)
    
    for i, outfit in enumerate(results[:n], 1):
        print(f"\n[{i}] Outfit ID: {outfit.get('outfit_id', 'N/A')}")
        print(f"    Similarity Score: {outfit.get('similarity_score', 0):.4f}")
        print(f"    Style: {outfit.get('style', 'N/A')}")
        print(f"    Season: {outfit.get('season', 'N/A')}")
        print(f"    Description: {outfit.get('description', 'N/A')[:100]}...")
        print(f"    Detail URL: {outfit.get('detail_url', 'N/A')}")
        print(f"    Image URL: {outfit.get('image_url', 'N/A')}")
        
        if 'items' in outfit:
            print(f"    Items ({len(outfit['items'])}):")
            for item in outfit['items'][:3]:  # 처음 3개만 출력
                print(f"      - {item.get('category', 'N/A')}: {item.get('name', 'N/A')[:50]}")
            if len(outfit['items']) > 3:
                print(f"      ... and {len(outfit['items']) - 3} more items")


if __name__ == "__main__":
    # 통합 남자 데이터(JSON, description_embedding 포함)
    json_file = "data/raw/final_data_남자.json"

    # text1: 해시태그 5개를 직접 입력
    text1 = input("해시태그를 모두 입력하세요 (공백/콤마로 구분): ").strip()

    # outfit_ids 5개를 입력 받아 해당 코디의 description_embedding 을 합산
    ids_raw = input("콤마(,)로 구분된 outfit_id 5개를 입력하세요: ").strip()
    outfit_ids = [s.strip() for s in ids_raw.split(",") if s.strip()]

    image_embedding_sum = get_image_embedding_sum_from_outfit_ids(outfit_ids, json_file)

    # 검색 실행
    results = search_similar_outfits(
        text1=text1,
        text2=image_embedding_sum,
        json_file=json_file,
        n=20,
    )

    # outfit_id만 추출
    outfit_ids = [outfit['outfit_id'] for outfit in results]
    for outfit_id in outfit_ids:
        print(outfit_id)

