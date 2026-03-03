"""
코디 추천 관련 비즈니스 로직.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app.models.coordi import Coordi
from app.models.coordi_item import CoordiItem
from app.models.item import Item
from app.models.tag import Tag
from app.models.user import User
from app.models.user_closet_item import UserClosetItem
from app.models.user_coordi_interaction import UserCoordiInteraction
from app.models.user_coordi_view_log import UserCoordiViewLog
from app.models.user_preferred_tag import UserPreferredTag
from app.schemas.recommendation_response import (
    OutfitItemPayload,
    OutfitPayload,
    PaginationPayload,
)
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import generate_llm_message


def _get_season_from_month(month: int) -> str:
    """
    월(month)을 기준으로 영어 season 레이블을 반환합니다.
    
    Parameters
    ----------
    month:
        월 (1-12)
        
    Returns
    -------
    str:
        계절 ("spring", "summer", "fall", "winter")
    """
    # TODO: 계절 기준 수정 가능
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"


async def _get_recommended_coordi_ids_temporary(
    db: Session,
    user_id: int,
    page: int,
    limit: int,
) -> tuple[list[int], int]:
    """
    임시 추천 함수: 사용자 성별에 맞는 코디를 최신순으로 반환합니다.
    
    TODO: 추천 모델로 교체 예정, 진짜 엄청 개편필요함 ㅠㅠ
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    page:
        페이지 번호 (1부터 시작)
    limit:
        페이지당 개수(반환할 코디의 개수)
        
    Returns
    -------
    tuple[list[int], int]:
        (코디 ID 리스트, 전체 코디 개수)
    """
    # 사용자 정보 조회
    user = db.get(User, user_id)
    if user is None or user.gender is None: # 사용자 정보 조회 실패 시 빈 리스트 반환
        return [], 0
    
    # 사용자가 이미 본 코디 또는 상호작용한 코디 ID 조회 (제외할 코디)
    viewed_coordi_ids = db.execute(
        select(UserCoordiViewLog.coordi_id)
        .where(UserCoordiViewLog.user_id == user_id)
    ).scalars().all()
    
    interacted_coordi_ids = db.execute(
        select(UserCoordiInteraction.coordi_id)
        .where(UserCoordiInteraction.user_id == user_id)
    ).scalars().all()
    
    # 두 집합 합치기 (중복 제거)
    # TODO: 이렇게 사후적 조치를 하는 것보단, 애초에 dataset에서 제외되도록 추천 모델 개발 필요
    excluded_coordi_ids = set(viewed_coordi_ids) | set(interacted_coordi_ids)
    
    # 사용자 성별에 맞는 코디 조회 (최신순, 이미 본 코디 제외)
    # TODO: 추천 모델로 교체 예정
    offset = (page - 1) * limit
    
    # 기본 쿼리: 성별 필터링
    base_query = select(Coordi).where(Coordi.gender == user.gender)
    
    # 이미 본 코디가 있으면 제외
    if excluded_coordi_ids:
        base_query = base_query.where(Coordi.coordi_id.notin_(excluded_coordi_ids))
    
    # 페이지네이션용 전체 개수 조회 (최적화: count() 사용)
    count_query = select(func.count(Coordi.coordi_id)).where(Coordi.gender == user.gender)
    if excluded_coordi_ids:
        count_query = count_query.where(Coordi.coordi_id.notin_(excluded_coordi_ids))
    total_items = db.execute(count_query).scalar_one()
    
    # 페이지네이션 적용
    # TODO: 여기에 추천 모델 적용
    coordis = db.execute(
        base_query
        .order_by(Coordi.created_at.desc())
        .offset(offset)
        .limit(limit) 
    ).scalars().all()
    
    # 코디 ID 리스트 반환
    coordi_ids = [coordi.coordi_id for coordi in coordis]
    return coordi_ids, total_items


async def _get_cold_recommended_coordi_ids(
    db: Session,
    user_id: int,
    page: int,
    limit: int,
) -> tuple[list[int], int]:
    """
    Cold recommendation 함수: 사용자의 선호 태그와 선택한 샘플 코디를 기반으로 임베딩 기반 추천을 수행합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    page:
        페이지 번호 (1부터 시작)
    limit:
        페이지당 개수(반환할 코디의 개수)
        
    Returns
    -------
    tuple[list[int], int]:
        (코디 ID 리스트, 전체 코디 개수)
    """
    # 사용자 정보 조회
    user = db.get(User, user_id)
    if user is None or user.gender is None:
        return [], 0
    
    # 1. 사용자의 선호 태그 조회
    preferred_tags = db.execute(
        select(Tag)
        .join(UserPreferredTag, Tag.tag_id == UserPreferredTag.tag_id)
        .where(UserPreferredTag.user_id == user_id)
    ).scalars().all()
    
    # 태그 텍스트 합치기 (예: "#캐주얼 #스트릿 #미니멀")
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
        # 필요한 컬럼만 조회: select(Coordi) -> select(Coordi.description_embedding)
        sample_embeddings = db.execute(
            select(Coordi.description_embedding)
            .where(Coordi.coordi_id.in_(sample_coordi_ids))
            .where(Coordi.description_embedding.isnot(None))
        ).scalars().all()
        
        # description_embedding 합산
        embeddings = []
        for embedding in sample_embeddings:
            if embedding is not None:
                # Vector 타입을 리스트로 변환
                embedding_list = list(embedding)
                embeddings.append(np.array(embedding_list, dtype=float))
        
        if embeddings:
            image_embedding_sum = np.sum(embeddings, axis=0)
        else:
            # 임베딩이 없으면 0 벡터
            image_embedding_sum = np.zeros(512)
    else:
        # 선택한 코디가 없으면 0 벡터
        image_embedding_sum = np.zeros(512)
    
    # 4. 태그 임베딩 생성
    embedding_service = EmbeddingService()
    if hashtags_text:
        hashtags_embedding = np.array(embedding_service.generate_embedding(hashtags_text), dtype=float)
    else:
        hashtags_embedding = np.zeros(512)
    
    # 5. 쿼리 임베딩 생성 (cold_start.py 로직 참고: text_weight=10.0)
    text_weight = 10.0
    query_embedding = hashtags_embedding + image_embedding_sum * text_weight
    
    # 정규화 (코사인 유사도 계산 시 필요)
    norm = np.linalg.norm(query_embedding)
    if norm > 0:
        query_embedding = query_embedding / norm
    else:
        # 정규화 불가능하면 (데이터 부족) 빈 결과 반환 (Phase 1 제거)
        return [], 0
    
    # 6. 사용자가 이미 본 코디 또는 상호작용한 코디 ID 조회 (제외할 코디)
    viewed_coordi_ids = db.execute(
        select(UserCoordiViewLog.coordi_id)
        .where(UserCoordiViewLog.user_id == user_id)
    ).scalars().all()
    
    interacted_coordi_ids = db.execute(
        select(UserCoordiInteraction.coordi_id)
        .where(UserCoordiInteraction.user_id == user_id)
    ).scalars().all()
    
    excluded_coordi_ids = set(viewed_coordi_ids) | set(interacted_coordi_ids)
    
    # 7. 현재 날짜 기준 계절 필터 적용
    current_month = datetime.now().month
    current_season = _get_season_from_month(current_month)
    
    # 8. pgvector를 사용하여 코사인 유사도로 유사한 코디 찾기
    # <=> 연산자는 코사인 거리 (1 - 코사인 유사도)를 반환하므로, 작을수록 유사함
    offset = (page - 1) * limit
    
    # 기본 쿼리: 성별 필터링, 계절 필터링, description_embedding이 있는 코디만
    base_query = (
        select(Coordi)
        .where(Coordi.gender == user.gender)
        .where(Coordi.season == current_season)
        .where(Coordi.description_embedding.isnot(None))
    )
    
    # 이미 본 코디가 있으면 제외
    if excluded_coordi_ids:
        base_query = base_query.where(Coordi.coordi_id.notin_(excluded_coordi_ids))
    
    # 전체 개수 조회
    count_query = (
        select(func.count(Coordi.coordi_id))
        .where(Coordi.gender == user.gender)
        .where(Coordi.season == current_season)
        .where(Coordi.description_embedding.isnot(None))
    )
    if excluded_coordi_ids:
        count_query = count_query.where(Coordi.coordi_id.notin_(excluded_coordi_ids))
    total_items = db.execute(count_query).scalar_one()
    
    # 쿼리 임베딩을 리스트로 변환
    query_embedding_list = query_embedding.tolist()
    
    # pgvector의 코사인 거리 연산자 (<=>) 사용
    # <=> 연산자는 코사인 거리 (1 - 코사인 유사도)를 반환하므로, 작을수록 유사함
    # 벡터를 PostgreSQL 벡터 형식 문자열로 변환: '[1,2,3]'
    query_vector_str = "[" + ",".join(map(str, query_embedding_list)) + "]"

    # [Warm Start Initialization]
    # Cold Start 쿼리 임베딩을 'day_v1' 유저 임베딩으로 저장하여 Warm Start 전환 준비
    try:
        from app.models.user_embedding import UserEmbedding
        # 기존 day_v1 임베딩 확인
        existing_embedding = db.get(UserEmbedding, (user_id, 'day_v1'))
        if not existing_embedding:
            new_embedding = UserEmbedding(
                user_id=user_id,
                model_version='day_v1',
                vector=query_embedding_list
            )
            db.add(new_embedding)
            db.commit()
            print(f"[Cold Start] Initialized day_v1 embedding for user {user_id}")
    except Exception as e:
        print(f"[Cold Start] Failed to initialize user embedding: {e}")
        db.rollback()
    
    # text()를 사용하여 raw SQL 작성
    # db.execute()에 params로 파라미터 전달
    coordis = db.execute(
        base_query
        .order_by(
            text(f"description_embedding <=> '{query_vector_str}'::vector")
        )
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    # 코디 ID 리스트 반환
    coordi_ids = [coordi.coordi_id for coordi in coordis]
    return coordi_ids, total_items


def _build_item_payload(
    item: Item,
    user_id: int,
    user_closet_item_ids: set[int],
) -> OutfitItemPayload:
    """
    아이템 페이로드를 생성합니다.
    
    Parameters
    ----------
    item:
        아이템 모델
    user_id:
        사용자 ID
    user_closet_item_ids:
        사용자가 저장한 아이템 ID 집합
        
    Returns
    -------
    OutfitItemPayload:
        아이템 페이로드
    """
    # 메인 이미지 추출 (is_main=True 우선, 없으면 첫 번째 이미지)
    main_image = next(
        (img for img in item.images if img.is_main),
        item.images[0] if item.images else None
    )
    image_url = main_image.image_url if main_image else None
    
    # isSaved 체크
    is_saved = item.item_id in user_closet_item_ids
    
    # price 변환 (Numeric → int, 원 단위)
    price = int(float(item.price)) if item.price is not None else None
    
    return OutfitItemPayload(
        id=item.item_id,
        category=item.category,
        brand=item.brand_name_ko,
        name=item.item_name,
        price=price,
        imageUrl=image_url,
        purchaseUrl=item.purchase_url,
        isSaved=is_saved,
    )


def _build_outfit_payload(
    coordi: Coordi,
    user_id: int,
    user_favorited_coordi_ids: set[int],
    user_closet_item_ids: set[int],
    llm_message: Optional[str],
) -> OutfitPayload:
    """
    코디 페이로드를 생성합니다.
    
    Parameters
    ----------
    coordi:
        코디 모델
    user_id:
        사용자 ID
    user_favorited_coordi_ids:
        사용자가 좋아요한 코디 ID 집합
    user_closet_item_ids:
        사용자가 저장한 아이템 ID 집합
    llm_message:
        LLM 메시지
        
    Returns
    -------
    OutfitPayload:
        코디 페이로드
    """
    # 메인 이미지 추출 (is_main=True 우선, 없으면 첫 번째 이미지)
    main_image = next(
        (img for img in coordi.images if img.is_main),
        coordi.images[0] if coordi.images else None
    )
    if main_image is None:
        raise ValueError(f"Coordi {coordi.coordi_id} has no images")
    
    # isFavorited 체크
    is_favorited = coordi.coordi_id in user_favorited_coordi_ids
    
    # 아이템 페이로드 생성
    items = [
        _build_item_payload(coordi_item.item, user_id, user_closet_item_ids)
        for coordi_item in coordi.coordi_items
    ]
    
    return OutfitPayload(
        id=coordi.coordi_id,
        imageUrl=main_image.image_url,
        gender=coordi.gender,
        season=coordi.season,
        style=coordi.style,
        description=coordi.description or "",
        isFavorited=is_favorited,
        llmMessage=llm_message,
        items=items,
        createdAt=coordi.created_at,
    )


async def get_recommended_coordis(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[OutfitPayload], PaginationPayload]:
    """
    사용자 맞춤 코디 목록을 조회합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    page:
        페이지 번호 (1부터 시작)
    limit:
        페이지당 개수
        
    Returns
    -------
    tuple[list[OutfitPayload], PaginationPayload]:
        (코디 페이로드 리스트, 페이지네이션 정보)
    """
    # 1. 사용자 정보 조회
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User with id {user_id} not found")
    
    # 2. 온보딩 상태에 따라 추천 방식 결정
    coordi_ids = []
    total_items = 0

    if user.has_completed_onboarding:
        # [Case 1] 온보딩 완료 -> Warm Start 시도 (DB/Model 기반)
        try:
            from app.services.warm_recommendation_service import get_warm_recommendation_service
            warm_service = get_warm_recommendation_service()
            
            # Warm Service 호출 (유저 임베딩 없으면 [] 반환)
            w_ids, w_total = warm_service.recommend(db, user_id, page, limit)
            
            if w_ids:
                coordi_ids = w_ids
                total_items = w_total
                print(f"[Warm Start] User {user_id}: Found {len(coordi_ids)} recommendations.")
        except Exception as e:
            print(f"[Warm Start Error] Failed to get warm recommendations: {e}")
            # 실패 시 아래 Cold Start로 폴백

    # [Case 2] 결과가 없으면 (Warm Start 실패 or 온보딩 미완료) -> Cold Start (임베딩 기반)
    if not coordi_ids:
        # 온보딩 완료 여부와 관계없이 Cold Start 시도
        # (온보딩 미완료라도 태그/취향 데이터가 조금이라도 있다면 추천 가능, 없으면 빈 리스트)
        coordi_ids, total_items = await _get_cold_recommended_coordi_ids(
            db, user_id, page, limit
        )
    
    # 코디 ID 리스트가 비어있으면 빈 결과 반환
    if not coordi_ids:
        return [], PaginationPayload(
            currentPage=page,
            totalPages=0,  # 총 페이지 수
            totalItems=0,  # 총 코디 개수
            hasNext=False,  # 다음 페이지 존재 여부
            hasPrev=False,  # 이전 페이지 존재 여부
        )
    
    # 3. 각 코디 상세 정보 조회 (selectinload로 N+1 문제 방지)
    coordis = db.execute(
        select(Coordi)
        .where(Coordi.coordi_id.in_(coordi_ids))
        .options(
            selectinload(Coordi.images),
            selectinload(Coordi.coordi_items).selectinload(CoordiItem.item).selectinload(Item.images),
        )
    ).scalars().all()
    
    # 코디 ID 순서 유지 (coordi_ids 순서대로 정렬)
    # 추천 순위를 그대로 유지하기 위해.
    coordi_dict = {coordi.coordi_id: coordi for coordi in coordis}
    coordis = [coordi_dict[cid] for cid in coordi_ids if cid in coordi_dict]
    
    # 4. 사용자별 isFavorited 체크
    # 사용자가 해당 코디를 좋아요 했는지
    favorited_interactions = db.execute(
        select(UserCoordiInteraction)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.coordi_id.in_(coordi_ids),
            UserCoordiInteraction.action_type == "like",
        )
    ).scalars().all()
    user_favorited_coordi_ids = {interaction.coordi_id for interaction in favorited_interactions}
    
    # 5. 사용자별 isSaved 체크 (UserClosetItem 존재 여부)
    # 사용자가 각 아이템들을 좋아요 했는지
    all_item_ids = set()
    for coordi in coordis:
        for coordi_item in coordi.coordi_items:
            all_item_ids.add(coordi_item.item_id)
    
    closet_items = db.execute(
        select(UserClosetItem)
        .where(
            UserClosetItem.user_id == user_id,
            UserClosetItem.item_id.in_(all_item_ids),
        )
    ).scalars().all()
    user_closet_item_ids = {item.item_id for item in closet_items}
    
    # 6. 코디별 LLM 메시지 생성 (병렬, Semaphore로 동시 요청 제한)
    # TODO: 임시로 패스 - LLM 메시지 생성 비활성화
    # semaphore = asyncio.Semaphore(10)  # 최대 10개 동시 요청
    # 
    # async def generate_with_limit(coordi: Coordi) -> tuple[int, Optional[str]]:
    #     async with semaphore:
    #         # LLM 메시지 생성
    #         message = await generate_llm_message(coordi, user) 
    #         return coordi.coordi_id, message
    # 
    # tasks = [generate_with_limit(coordi) for coordi in coordis]
    # llm_results = await asyncio.gather(*tasks, return_exceptions=True)
    # 
    # # 코디 ID별 LLM 메시지 매핑 (예외 발생 시 None 처리)
    # llm_messages = {}
    # for result in llm_results:
    #     if isinstance(result, Exception):
    #         continue
    #     coordi_id, message = result
    #     llm_messages[coordi_id] = message
    
    # 임시: 빈 딕셔너리 반환 (LLM 메시지 없음)
    llm_messages = {}
    
    # 7. 페이로드 생성
    outfits = [
        _build_outfit_payload(
            coordi,
            user_id,
            user_favorited_coordi_ids,
            user_closet_item_ids,
            llm_messages.get(coordi.coordi_id),
        )
        for coordi in coordis
    ]
    
    # 8. 페이지네이션 정보 계산
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1
    
    pagination = PaginationPayload(
        currentPage=page,
        totalPages=total_pages,
        totalItems=total_items,
        hasNext=has_next,
        hasPrev=has_prev,
    )
    
    return outfits, pagination

