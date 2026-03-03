
import json
import logging
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가 (패키지 임포트 문제 해결)
# scripts/ 폴더에서 실행하기 때문에 상위 트리의 backend 폴더를 경로에 추가
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_DIR))

from sqlalchemy.orm import Session
from sqlalchemy import update
from app.db.database import SessionLocal
from app.models.coordi import Coordi

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def update_embeddings_from_json(json_file: str = "output_embeddings.json"):
    """
    JSON 파일에서 임베딩을 읽어 DB의 description_embedding 컬럼을 업데이트합니다.
    """
    logger.info(f"Starting to update embeddings from {json_file}...")
    
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        print(f"현재 경로: {os.getcwd()}")
        return

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        db: Session = SessionLocal()
        updated_count = 0
        
        # 일괄 업데이트보다는 안전하게 건별 업데이트 진행 (진행상황 파악 용이)
        total_items = len(data)
        logger.info(f"Loaded {total_items} items. Processing...")

        for idx, item in enumerate(data):
            coordi_id = item.get('coordi_id')
            embedding = item.get('description_embedding')
            
            if not coordi_id or not embedding:
                logger.warning(f"Skipping item {idx}: Missing id or embedding")
                continue
                
            # DB 업데이트
            stmt = (
                update(Coordi)
                .where(Coordi.coordi_id == coordi_id)
                .values(description_embedding=embedding)
            )
            result = db.execute(stmt)
            updated_count += result.rowcount
            
            if (idx + 1) % 50 == 0:
                db.commit()
                logger.info(f"Progress: {idx + 1}/{total_items} committed...")
                
        db.commit()
        logger.info(f"Successfully updated {updated_count} coordis.")
        
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # 실행 시 파일명 인자로 받을 수 있음
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        # 기본값: 같은 디렉토리의 output_embeddings.json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "output_embeddings.json")
        # 없으면 상위 디렉토리도 확인
        if not os.path.exists(json_path):
             json_path = "output_embeddings.json"

    update_embeddings_from_json(json_path)
