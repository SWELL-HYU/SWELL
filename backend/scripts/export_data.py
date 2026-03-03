
"""
데이터 내보내기 스크립트 (export_data.py)

이 스크립트는 데이터베이스에 저장된 사용자 상호작용(UserCoordiInteraction)과
시청 로그(UserCoordiViewLog) 데이터를 CSV 파일로 내보냅니다.

생성되는 파일:
1. user_outfit_interaction.csv: 
   - user_id, outfit_id, interaction
2. user_embeddings.csv:
   - user_id, user_embedding
3. outfit_embeddings.csv:
   - outfit_id, outfit_embedding
4. user_outfit_view_time.csv: 사용자-코디 시청 시간 데이터 (view_time_seconds: 초 단위)
"""
import sys
import os
import csv
import numpy as np
import traceback

# Add backend directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.database import SessionLocal
from app.models.user_coordi_interaction import UserCoordiInteraction
from app.models.user_coordi_view_log import UserCoordiViewLog
from app.models.coordi import Coordi
from app.models.user_preferred_tag import UserPreferredTag
from app.models.tag import Tag
from app.services.embedding_service import EmbeddingService

def calculate_user_embedding(db, user_id, embedding_service):
    """
    recommendations_service.py의 _get_cold_recommended_coordi_ids 로직을 참고하여
    query_embedding(user_embedding)을 계산합니다.
    """
    # 1. 사용자의 선호 태그 조회
    preferred_tags = db.execute(
        select(Tag)
        .join(UserPreferredTag, Tag.tag_id == UserPreferredTag.tag_id)
        .where(UserPreferredTag.user_id == user_id)
    ).scalars().all()
    
    # 태그 텍스트 합치기
    hashtags_text = " ".join([tag.name for tag in preferred_tags])
    
    # 2. 사용자가 선택한 샘플 코디 조회 (action_type='preference')
    preference_interactions = db.execute(
        select(UserCoordiInteraction)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.action_type == "preference",
        )
    ).scalars().all()
    
    sample_coordi_ids = [interaction.coordi_id for interaction in preference_interactions]
    
    # 3. 선택한 코디들의 description_embedding 합산
    if sample_coordi_ids:
        sample_embeddings = db.execute(
            select(Coordi.description_embedding)
            .where(Coordi.coordi_id.in_(sample_coordi_ids))
            .where(Coordi.description_embedding.isnot(None))
        ).scalars().all()
        
        embeddings = []
        for embedding in sample_embeddings:
            if embedding is not None:
                # Vector 타입을 리스트로 변환
                embedding_list = list(embedding)
                embeddings.append(np.array(embedding_list, dtype=float))
        
        if embeddings:
            image_embedding_sum = np.sum(embeddings, axis=0)
        else:
            image_embedding_sum = np.zeros(512)
    else:
        image_embedding_sum = np.zeros(512)
    
    # 4. 태그 임베딩 생성
    if hashtags_text:
        # EmbeddingService의 generate_embedding 메소드 사용
        # recommendations_service.py: np.array(embedding_service.generate_embedding(hashtags_text), dtype=float)
        hashtags_embedding = np.array(embedding_service.generate_embedding(hashtags_text), dtype=float)
    else:
        hashtags_embedding = np.zeros(512)
    
    # 5. 쿼리 임베딩 생성 (text_weight=10.0)
    text_weight = 10.0
    query_embedding = hashtags_embedding + image_embedding_sum * text_weight
    
    # 정규화
    norm = np.linalg.norm(query_embedding)
    if norm > 0:
        query_embedding = query_embedding / norm
        
    return query_embedding.tolist()

def format_embedding(embedding_list):
    """임베딩 리스트를 문자열로 변환"""
    if not embedding_list:
        return "[]"
    return str(list(embedding_list))

def export_data():
    db = SessionLocal()
    embedding_service = None
    
    try:
        print("Initializing EmbeddingService (this may take a while)...")
        embedding_service = EmbeddingService()
        
        print("Exporting data to CSV...")

        # 1. Export user_outfit_interaction.csv
        # 임베딩 값은 별도의 CSV 파일(table)로 분리
        
        # Caches
        user_embedding_cache = {}
        outfit_embedding_cache = {}

        # Coordi 테이블과 조인하여 바로 outfit_embedding 가져오기
        stmt = (
            select(UserCoordiInteraction, Coordi.description_embedding)
            .join(Coordi, UserCoordiInteraction.coordi_id == Coordi.coordi_id)
        )
        results = db.execute(stmt).all()
        
        total_count = len(results)
        print(f"Found {total_count} interactions. Processing...")

        with open('user_outfit_interaction.csv', 'w', newline='') as csvfile:
            # 임베딩 컬럼 제거
            fieldnames = ['user_id', 'outfit_id', 'interaction']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for idx, (interaction, outfit_emb_vec) in enumerate(results):
                user_id = interaction.user_id
                outfit_id = interaction.coordi_id
                
                # Retrieve or calculate User Embedding
                if user_id not in user_embedding_cache:
                    if len(user_embedding_cache) % 10 == 0:
                        print(f"Calculating embedding for User {user_id}...")
                    user_embedding_cache[user_id] = calculate_user_embedding(db, user_id, embedding_service)
                
                # Cache Outfit Embedding
                if outfit_id not in outfit_embedding_cache:
                    outfit_emb_list = list(outfit_emb_vec) if outfit_emb_vec is not None else [0.0]*512
                    outfit_embedding_cache[outfit_id] = outfit_emb_list
                
                writer.writerow({
                    'user_id': user_id,
                    'outfit_id': outfit_id,
                    'interaction': interaction.action_type
                })
                
                if (idx + 1) % 1000 == 0:
                    print(f"Processed {idx + 1}/{total_count} interactions")
                    
        print(f"Exported {total_count} rows to user_outfit_interaction.csv")

        # 2. Export user_embeddings.csv
        print(f"Exporting {len(user_embedding_cache)} user embeddings...")
        with open('user_embeddings.csv', 'w', newline='') as csvfile:
            fieldnames = ['user_id', 'user_embedding']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for uid, emb in user_embedding_cache.items():
                writer.writerow({
                    'user_id': uid,
                    'user_embedding': format_embedding(emb)
                })
        print("Exported user_embeddings.csv")

        # 3. Export outfit_embeddings.csv
        print(f"Exporting {len(outfit_embedding_cache)} outfit embeddings...")
        with open('outfit_embeddings.csv', 'w', newline='') as csvfile:
            fieldnames = ['outfit_id', 'outfit_embedding']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for oid, emb in outfit_embedding_cache.items():
                writer.writerow({
                    'outfit_id': oid,
                    'outfit_embedding': format_embedding(emb)
                })
        print("Exported outfit_embeddings.csv")

        # 2. Export user_outfit_view_time.csv (기존 동일)
        view_logs = db.execute(select(UserCoordiViewLog)).scalars().all()
        
        with open('user_outfit_view_time.csv', 'w', newline='') as csvfile:
            fieldnames = ['user_id', 'outfit_id', 'view_time_seconds']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in view_logs:
                writer.writerow({
                    'user_id': log.user_id,
                    'outfit_id': log.coordi_id,
                    'view_time_seconds': log.duration_seconds
                })
        print(f"Exported {len(view_logs)} rows to user_outfit_view_time.csv")

        # 3. Export coordis for embedding generation (JSON)
        # We need this to generate embeddings in Colab if we can't connect to DB directly
        from app.models.coordi import Coordi
        import json

        coordis = db.execute(select(Coordi)).scalars().all()
        coordis_data = []
        for coordi in coordis:
            # Get first image url if exists
            image_url = None
            if coordi.images:
                # Assuming CoordiImage has 'image_url' field. 
                # If it's different (e.g. 'url'), this might need adjustment.
                # Based on common patterns and previous context.
                image_url = coordi.images[0].image_url

            coordis_data.append({
                "coordi_id": coordi.coordi_id,
                "image_url": image_url,
                "description": coordi.description,
                "style": coordi.style,
                "created_at": str(coordi.created_at) if coordi.created_at else None
            })
        
        with open('coordis_export.json', 'w', encoding='utf-8') as jsonfile:
            json.dump(coordis_data, jsonfile, ensure_ascii=False, indent=4)
            
        print(f"Exported {len(coordis)} coordis to coordis_export.json")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    export_data()