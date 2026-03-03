"""
코디 목록 조회 관련 비즈니스 로직.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AlreadyFavoritedError, FavoriteNotFoundError, OutfitNotFoundError
from app.models.coordi import Coordi
from app.models.coordi_item import CoordiItem
from app.models.item import Item
from app.models.user_closet_item import UserClosetItem
from app.models.user_coordi_interaction import UserCoordiInteraction
from app.models.user_coordi_view_log import UserCoordiViewLog
from app.schemas.common import PaginationPayload
from app.schemas.recommendation_response import OutfitItemPayload, OutfitPayload

# 필터 타입 정의
SeasonFilter = Literal["all", "spring", "summer", "fall", "winter"]
StyleFilter = Literal["all", "casual", "street", "sporty", "minimal"]
GenderFilter = Literal["all", "male", "female"]


def _build_item_payload_list(
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


def _build_outfit_payload_list(
    coordi: Coordi,
    user_id: int,
    user_favorited_coordi_ids: set[int],
    user_closet_item_ids: set[int],
) -> OutfitPayload:
    """
    코디 페이로드를 생성합니다 (LLM 메시지 없음).
    
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
        
    Returns
    -------
    OutfitPayload:
        코디 페이로드 (llmMessage는 None)
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
        _build_item_payload_list(coordi_item.item, user_id, user_closet_item_ids)
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
        llmMessage=None,  # 목록 조회에서는 LLM 메시지 없음
        items=items,
        createdAt=coordi.created_at,
    )


async def get_outfits_list(
    db: Session,
    user_id: int,
    season: SeasonFilter = "all",
    style: StyleFilter = "all",
    gender: GenderFilter = "all",
    page: int = 1,
    limit: int = 10,
) -> tuple[list[OutfitPayload], PaginationPayload]:
    """
    필터링된 코디 목록을 조회합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    season:
        계절 필터 ("all"이면 필터링 안 함)
    style:
        스타일 필터 ("all"이면 필터링 안 함)
    gender:
        성별 필터 ("all"이면 필터링 안 함)
    page:
        페이지 번호 (1부터 시작)
    limit:
        페이지당 개수
        
    Returns
    -------
    tuple[list[OutfitPayload], PaginationPayload]:
        (코디 페이로드 리스트, 페이지네이션 정보)
    """
    # 1. 사용자가 이미 본 코디 또는 상호작용한 코디 ID 조회 (제외할 코디)
    viewed_coordi_ids = db.execute(
        select(UserCoordiViewLog.coordi_id)
        .where(UserCoordiViewLog.user_id == user_id)
    ).scalars().all()
    
    interacted_coordi_ids = db.execute(
        select(UserCoordiInteraction.coordi_id)
        .where(UserCoordiInteraction.user_id == user_id)
    ).scalars().all()
    
    # 두 집합 합치기 (중복 제거)
    excluded_coordi_ids = set(viewed_coordi_ids) | set(interacted_coordi_ids)
    
    # 2. 필터링 쿼리 구성
    query = select(Coordi)
    
    if season != "all":
        query = query.where(Coordi.season == season)
    if style != "all":
        query = query.where(Coordi.style == style)
    if gender != "all":
        query = query.where(Coordi.gender == gender)
    
    # 이미 본 코디 또는 상호작용한 코디 제외
    if excluded_coordi_ids:
        query = query.where(Coordi.coordi_id.notin_(excluded_coordi_ids))
    
    # 3. 전체 개수 조회 (페이지네이션용)
    count_query = select(func.count(Coordi.coordi_id))
    if season != "all":
        count_query = count_query.where(Coordi.season == season)
    if style != "all":
        count_query = count_query.where(Coordi.style == style)
    if gender != "all":
        count_query = count_query.where(Coordi.gender == gender)
    
    # 이미 본 코디 또는 상호작용한 코디 제외
    if excluded_coordi_ids:
        count_query = count_query.where(Coordi.coordi_id.notin_(excluded_coordi_ids))
    
    total_items = db.execute(count_query).scalar_one()
    
    # 결과가 없으면 빈 결과 반환
    if total_items == 0:
        return [], PaginationPayload(
            currentPage=page,
            totalPages=0,
            totalItems=0,
            hasNext=False,
            hasPrev=False,
        )
    
    # 4. 페이지네이션 적용 및 정렬
    offset = (page - 1) * limit
    coordis = db.execute(
        query
        .order_by(Coordi.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(
            selectinload(Coordi.images),
            selectinload(Coordi.coordi_items).selectinload(CoordiItem.item).selectinload(Item.images),
        )
    ).scalars().all()
    
    # 5. 사용자별 isFavorited 체크
    coordi_ids = [coordi.coordi_id for coordi in coordis]
    favorited_interactions = db.execute(
        select(UserCoordiInteraction)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.coordi_id.in_(coordi_ids),
            UserCoordiInteraction.action_type == "like",
        )
    ).scalars().all()
    user_favorited_coordi_ids = {interaction.coordi_id for interaction in favorited_interactions}
    
    # 6. 사용자별 isSaved 체크 (UserClosetItem 존재 여부)
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
    
    # 7. 페이로드 생성
    outfits = [
        _build_outfit_payload_list(
            coordi,
            user_id,
            user_favorited_coordi_ids,
            user_closet_item_ids,
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


def add_favorite(
    db: Session,
    user_id: int,
    coordi_id: int,
) -> UserCoordiInteraction:
    """
    코디에 좋아요를 추가합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    coordi_id:
        코디 ID
        
    Returns
    -------
    UserCoordiInteraction:
        생성된 좋아요 상호작용 레코드
        
    Raises
    ------
    OutfitNotFoundError:
        코디가 존재하지 않는 경우
    AlreadyFavoritedError:
        이미 좋아요한 코디인 경우
    """
    # 1. 코디 존재 여부 확인
    coordi = db.get(Coordi, coordi_id)
    if coordi is None:
        raise OutfitNotFoundError()
    
    # 2. 이미 좋아요가 있는지 확인
    existing_like = db.execute(
        select(UserCoordiInteraction)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.coordi_id == coordi_id,
            UserCoordiInteraction.action_type == "like",
        )
    ).scalar_one_or_none()
    
    if existing_like is not None:
        raise AlreadyFavoritedError()
    
    # 3. 기존 상호작용 확인 (skip 등 다른 action_type이 있는 경우)
    existing_interaction = db.execute(
        select(UserCoordiInteraction)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.coordi_id == coordi_id,
        )
    ).scalar_one_or_none()
    
    if existing_interaction is not None:
        # 기존 상호작용이 있으면 좋아요로 업데이트 (좋아요 우선)
        existing_interaction.action_type = "like"
        db.commit()
        db.refresh(existing_interaction)
        return existing_interaction
    
    # 4. 새로운 좋아요 기록 생성
    interaction = UserCoordiInteraction(
        user_id=user_id,
        coordi_id=coordi_id,
        action_type="like",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    
    return interaction


def skip_outfit(
    db: Session,
    user_id: int,
    coordi_id: int,
) -> UserCoordiInteraction:
    """
    코디를 스킵으로 기록합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    coordi_id:
        코디 ID
        
    Returns
    -------
    UserCoordiInteraction:
        스킵 상호작용 레코드 (기존 또는 새로 생성된 레코드)
        
    Raises
    ------
    OutfitNotFoundError:
        코디가 존재하지 않는 경우
    """
    # 1. 코디 존재 여부 확인
    coordi = db.get(Coordi, coordi_id)
    if coordi is None:
        raise OutfitNotFoundError()
    
    # 2. 이미 좋아요한 코디인지 확인
    existing_like = db.execute(
        select(UserCoordiInteraction)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.coordi_id == coordi_id,
            UserCoordiInteraction.action_type == "like",
        )
    ).scalar_one_or_none()
    
    if existing_like is not None:
        # 좋아요가 있는 경우: 기존 레코드 반환 (예외 없이 pass, 200 OK)
        return existing_like
    
    # 3. 이미 스킵된 코디인지 확인
    existing_skip = db.execute(
        select(UserCoordiInteraction)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.coordi_id == coordi_id,
            UserCoordiInteraction.action_type == "skip",
        )
    ).scalar_one_or_none()
    
    if existing_skip is not None:
        # 스킵된 경우: 기존 레코드 반환 (idempotent, interacted_at 업데이트 안 함)
        return existing_skip
    
    # 4. 새로운 스킵 기록 생성
    interaction = UserCoordiInteraction(
        user_id=user_id,
        coordi_id=coordi_id,
        action_type="skip",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    
    return interaction


def record_view_log(
    db: Session,
    user_id: int,
    coordi_id: int,
    duration_seconds: int,
) -> datetime:
    """
    코디 조회 로그를 기록합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    coordi_id:
        코디 ID
    duration_seconds:
        조회 시간 (초)
        
    Returns
    -------
    datetime:
        기록 일시 (UTC)
        
    Raises
    ------
    OutfitNotFoundError:
        코디가 존재하지 않는 경우
    """
    # 1. 코디 존재 여부 확인
    coordi = db.get(Coordi, coordi_id)
    if coordi is None:
        raise OutfitNotFoundError()
    
    # 2. 조회 로그 레코드 생성
    view_log = UserCoordiViewLog(
        user_id=user_id,
        coordi_id=coordi_id,
        duration_seconds=duration_seconds,
    )
    db.add(view_log)
    db.commit()
    db.refresh(view_log)
    
    # 3. 기록 일시 반환 (view_started_at 사용)
    return view_log.view_started_at


def remove_favorite(
    db: Session,
    user_id: int,
    coordi_id: int,
) -> tuple[int, datetime]:
    """
    코디 좋아요를 취소합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    coordi_id:
        코디 ID
        
    Returns
    -------
    tuple[int, datetime]:
        (coordi_id, unfavorited_at)
        
    Raises
    ------
    OutfitNotFoundError:
        코디가 존재하지 않는 경우
    FavoriteNotFoundError:
        좋아요하지 않은 코디인 경우
    """
    # 1. 코디 존재 여부 확인
    coordi = db.get(Coordi, coordi_id)
    if coordi is None:
        raise OutfitNotFoundError()
    
    # 2. 좋아요 기록 확인
    existing_like = db.execute(
        select(UserCoordiInteraction)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.coordi_id == coordi_id,
            UserCoordiInteraction.action_type == "like",
        )
    ).scalar_one_or_none()
    
    if existing_like is None:
        raise FavoriteNotFoundError()
    
    # 3. 좋아요 기록 삭제
    unfavorited_at = datetime.now(timezone.utc)
    db.delete(existing_like)
    db.commit()
    
    return coordi_id, unfavorited_at


async def get_favorite_outfits(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[OutfitPayload], PaginationPayload]:
    """
    사용자가 좋아요한 코디 목록을 조회합니다.
    
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
    # 1. 전체 개수 조회
    total_items = db.execute(
        select(func.count(UserCoordiInteraction.coordi_id))
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.action_type == "like",
        )
    ).scalar_one()
    
    # 결과가 없으면 빈 결과 반환
    if total_items == 0:
        return [], PaginationPayload(
            currentPage=page,
            totalPages=0,
            totalItems=0,
            hasNext=False,
            hasPrev=False,
        )
    
    # 2. 페이지네이션 적용하여 좋아요한 코디 ID 조회 (interacted_at 기준 최신순)
    offset = (page - 1) * limit
    favorite_interactions = db.execute(
        select(UserCoordiInteraction.coordi_id)
        .where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.action_type == "like",
        )
        .order_by(UserCoordiInteraction.interacted_at.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    
    coordi_ids = list(favorite_interactions)
    
    # 3. 코디 상세 정보 조회 (selectinload로 N+1 방지)
    coordis = db.execute(
        select(Coordi)
        .where(Coordi.coordi_id.in_(coordi_ids))
        .options(
            selectinload(Coordi.images),
            selectinload(Coordi.coordi_items).selectinload(CoordiItem.item).selectinload(Item.images),
        )
    ).scalars().all()
    
    # 4. interacted_at 기준으로 정렬 (좋아요 추가 일시 기준 최신순)
    # coordi_ids 순서대로 정렬하여 페이징된 순서 유지
    coordi_dict = {coordi.coordi_id: coordi for coordi in coordis}
    coordis = [coordi_dict[coordi_id] for coordi_id in coordi_ids if coordi_id in coordi_dict]
    
    # 5. 사용자별 isFavorited 체크 (모두 좋아요한 코디이므로 True)
    user_favorited_coordi_ids = set(coordi_ids)
    
    # 6. 사용자별 isSaved 체크 (UserClosetItem 존재 여부)
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
    
    # 7. 페이로드 생성
    outfits = [
        _build_outfit_payload_list(
            coordi,
            user_id,
            user_favorited_coordi_ids,
            user_closet_item_ids,
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

