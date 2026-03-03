"""
코디 데이터를 DB에 일괄 삽입하는 배치 스크립트.

사용법:
    python scripts/load_coordis.py data/coordis.json
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.coordi import Coordi
from app.models.coordi_image import CoordiImage
from app.models.coordi_item import CoordiItem
from app.models.item import Item
from app.models.item_image import ItemImage
from app.models.item_image import ItemImage


# 카테고리 변환: 한국어 -> 영어
CATEGORY_MAP = {
    "아우터": "outer",
    "상의": "top",
    "하의": "bottom",
}

# 시즌 변환: 한국어 -> 영어
SEASON_MAP = {
    "봄": "spring",
    "여름": "summer",
    "가을": "fall",
    "겨울": "winter",
}

# 스타일 변환: 한국어 -> 영어
STYLE_MAP = {
    "캐주얼": "casual",
    "스트릿": "street",
    "스포티": "sporty",
    "미니멀": "minimal",
}

# 성별 변환: 대문자 -> 소문자
def normalize_gender(gender: str) -> str:
    """성별을 소문자로 변환"""
    return gender.lower() if gender else "female"




def get_or_create_item(
    db: SessionLocal,
    item_id: int,
    category: str,
    brand: str,
    name: str,
    price: int | None,
    image_url: str,
    purchase_url: str,
) -> Item:
    """
    아이템이 존재하면 업데이트하고, 없으면 생성한다.
    
    Args:
        db: 데이터베이스 세션
        item_id: 아이템 ID (직접 지정)
        category: 카테고리 (한국어)
        brand: 브랜드명
        name: 아이템명
        price: 가격
        image_url: 이미지 URL
        purchase_url: 구매 URL
        
    Returns:
        Item 객체
    """
    # 기존 아이템 조회
    existing_item = db.execute(
        select(Item).where(Item.item_id == item_id)
    ).scalar_one_or_none()
    
    # 카테고리 변환
    item_type = CATEGORY_MAP.get(category, "top")  # 기본값: top
    
    if existing_item:
        # 기존 아이템이 있으면 필드 업데이트 (덮어쓰기)
        existing_item.item_name = name
        existing_item.category = item_type
        existing_item.brand_name_ko = brand
        existing_item.price = float(price) if price else None
        existing_item.purchase_url = purchase_url
        
        item = existing_item
    else:
        # 아이템 생성 (item_id 직접 지정)
        item = Item(
            item_id=item_id,  # 직접 ID 지정
            item_name=name,
            category=item_type,
            brand_name_ko=brand,
            price=float(price) if price else None,
            purchase_url=purchase_url,
        )
        db.add(item)
    
    db.flush()  # item_id를 DB에 확정
    
    # 아이템 이미지 처리 (중복 체크)
    if image_url:
        # 기존 메인 이미지 확인
        existing_image = db.execute(
            select(ItemImage).where(
                ItemImage.item_id == item.item_id,
                ItemImage.is_main == True,
            )
        ).scalar_one_or_none()
        
        if existing_image:
            # 기존 이미지가 있으면 URL 업데이트
            existing_image.image_url = image_url
        else:
            # 기존 이미지가 없으면 새로 생성
            item_image = ItemImage(
                item_id=item.item_id,
                image_url=image_url,
                is_main=True,  # 첫 번째 이미지를 메인으로
            )
            db.add(item_image)
    
    return item


def create_coordi(
    db: SessionLocal,
    outfit_id: int,
    gender: str,
    image_url: str,
    detail_url: str,
    items: list[dict],
    season: str,
    style: str,
    description: str,
) -> Coordi:
    """
    코디를 생성하거나 업데이트한다. (ID가 같으면 덮어쓰기)
    
    Args:
        db: 데이터베이스 세션
        outfit_id: 코디 ID (직접 지정)
        gender: 성별
        image_url: 코디 이미지 URL
        detail_url: 상세 URL
        items: 아이템 리스트
        season: 시즌 (한국어)
        style: 스타일 (한국어)
        description: 설명
        
    Returns:
        Coordi 객체
    """
    # 기존 코디 조회
    existing_coordi = db.execute(
        select(Coordi).where(Coordi.coordi_id == outfit_id)
    ).scalar_one_or_none()
    
    # 데이터 변환
    gender_normalized = normalize_gender(gender)
    season_english = SEASON_MAP.get(season, "spring")  # 기본값: spring
    style_english = STYLE_MAP.get(style, "casual")  # 기본값: casual
    
    description_embedding = None
    # 임베딩 생성은 별도 배치 스크립트로 처리 (untitled0.py -> update_embeddings.py)
    
    if existing_coordi:
        # 기존 코디가 있으면 필드 업데이트 (덮어쓰기)
        existing_coordi.gender = gender_normalized
        existing_coordi.season = season_english
        existing_coordi.style = style_english
        existing_coordi.description = description
        existing_coordi.description_embedding = description_embedding
        coordi = existing_coordi
    else:
        # 코디 생성 (coordi_id 직접 지정)
        coordi = Coordi(
            coordi_id=outfit_id,  # 직접 ID 지정
            gender=gender_normalized,
            season=season_english,
            style=style_english,
            description=description,
            description_embedding=description_embedding,
        )
        db.add(coordi)
    
    db.flush()  # coordi_id를 DB에 확정
    
    # 코디 이미지 처리 (중복 체크)
    if image_url:
        # 기존 메인 이미지 확인
        existing_image = db.execute(
            select(CoordiImage).where(
                CoordiImage.coordi_id == coordi.coordi_id,
                CoordiImage.is_main == True,
            )
        ).scalar_one_or_none()
        
        if existing_image:
            # 기존 이미지가 있으면 URL 업데이트
            existing_image.image_url = image_url
        else:
            # 기존 이미지가 없으면 새로 생성
            coordi_image = CoordiImage(
                coordi_id=coordi.coordi_id,
                image_url=image_url,
                is_main=True,
            )
            db.add(coordi_image)
    
    # 아이템들 처리 및 관계 생성
    for item_data in items:
        item_id = int(item_data["item_id"])
        category = item_data["category"]
        brand = item_data.get("brand", "")
        name = item_data.get("name", "")
        price = item_data.get("price")
        item_image_url = item_data.get("image_url", "")
        purchase_url = item_data.get("purchase_url", "")
        
        # 아이템 조회 또는 생성
        item = get_or_create_item(
            db=db,
            item_id=item_id,
            category=category,
            brand=brand,
            name=name,
            price=price,
            image_url=item_image_url,
            purchase_url=purchase_url,
        )
        
        # 코디-아이템 관계 생성 (이미 존재하는지 확인)
        existing_relation = db.execute(
            select(CoordiItem).where(
                CoordiItem.coordi_id == coordi.coordi_id,
                CoordiItem.item_id == item.item_id,
            )
        ).scalar_one_or_none()
        
        if not existing_relation:
            coordi_item = CoordiItem(
                coordi_id=coordi.coordi_id,
                item_id=item.item_id,
            )
            db.add(coordi_item)
    
    return coordi


def load_coordis_from_json(json_file_path: str) -> None:
    """
    JSON 파일에서 코디 데이터를 읽어 DB에 삽입한다.
    
    Args:
        json_file_path: JSON 파일 경로
    """
    db = SessionLocal()
    
    try:
        # JSON 파일 읽기
        with open(json_file_path, "r", encoding="utf-8") as f:
            coordis_data = json.load(f)
        
        # 리스트가 아니면 단일 코디로 처리
        if not isinstance(coordis_data, list):
            coordis_data = [coordis_data]
        
        # 코디 개수
        total_count = len(coordis_data)
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        # DB에서 가장 마지막에 저장된 코디 ID 조회
        last_coordi_id = db.execute(
            select(Coordi.coordi_id).order_by(Coordi.coordi_id.desc()).limit(1)
        ).scalar_one_or_none()
        
        if last_coordi_id is None:
            last_coordi_id = 0
            print("DB가 비어있습니다. ID 1부터 시작합니다.")
        else:
            print(f"마지막 저장된 코디 ID: {last_coordi_id}")
            print(f"ID {last_coordi_id + 1}부터 시작합니다.")
        
        # "제일 마지막부터 데이터를 3201로 매핑" -> 역순 처리 (제거됨)
        # print("데이터를 역순으로 처리합니다...")
        # coordis_data.reverse()
        
        print(f"총 {total_count}개의 코디를 처리합니다...\n")
        
        # 각 코디 삽입
        current_id = last_coordi_id + 1
        
        for idx, coordi_data in enumerate(coordis_data, 1):
            try:
                # JSON의 outfit_id는 무시하고 새로운 ID 부여
                original_outfit_id = coordi_data.get("outfit_id")
                outfit_id = current_id
                
                gender = coordi_data.get("gender", "FEMALE")
                image_url = coordi_data.get("image_url", "")
                detail_url = coordi_data.get("detail_url", "")
                items = coordi_data.get("items", [])
                season = coordi_data.get("season", "봄")
                style = coordi_data.get("style", "캐주얼")
                description = coordi_data.get("description", "")
                
                # 코디 생성
                coordi = create_coordi(
                    db=db,
                    outfit_id=outfit_id,
                    gender=gender,
                    image_url=image_url,
                    detail_url=detail_url,
                    items=items,
                    season=season,
                    style=style,
                    description=description,
                )
                
                # 커밋
                db.commit()
                
                success_count += 1
                print(
                    f"[{idx}/{total_count}] ✓ New ID: {coordi.coordi_id} (Original: {original_outfit_id}), "
                    f"아이템 {len(items)}개, 스타일: {coordi.style}"
                )
                
                current_id += 1
                
                
            except Exception as e:
                db.rollback()
                error_count += 1
                outfit_id = coordi_data.get("outfit_id", "알 수 없음")
                print(f"[{idx}/{total_count}] ✗ 코디 ID {outfit_id}: {str(e)}")
                print("상세 에러 로그:")
                traceback.print_exc()
                print("-" * 50)
        
        # 결과 요약
        print(f"\n{'='*50}")
        print(f"완료: {success_count}개 성공, {error_count}개 실패, {skipped_count}개 스킵됨")
        print(f"{'='*50}")
        
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다: {json_file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파싱 실패: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"오류: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def main() -> None:
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python scripts/load_coordis.py <json_file_path>")
        print("예시: python scripts/load_coordis.py data/coordis.json")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    load_coordis_from_json(json_file_path)


if __name__ == "__main__":
    main()

