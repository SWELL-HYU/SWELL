"""
옷장 관련 비즈니스 로직.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AlreadySavedError, ItemNotFoundError, ItemNotInClosetError
from app.models.item import Item
from app.models.user_closet_item import UserClosetItem
from app.schemas.closet import CategoryCountsPayload, ClosetItemPayload
from app.schemas.common import PaginationPayload


def save_closet_item(
    db: Session,
    user_id: int,
    item_id: int,
) -> datetime:
    """
    아이템을 옷장에 저장합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    item_id:
        아이템 ID
        
    Returns
    -------
    datetime:
        저장 일시 (added_at)
        
    Raises
    ------
    ItemNotFoundError:
        아이템이 존재하지 않는 경우
    AlreadySavedError:
        이미 옷장에 저장된 아이템인 경우
    """
    # 1. 아이템 존재 여부 확인
    item = db.get(Item, item_id)
    if item is None:
        raise ItemNotFoundError()
    
    # 2. 이미 저장된 아이템인지 확인
    existing_closet_item = db.execute(
        select(UserClosetItem)
        .where(
            UserClosetItem.user_id == user_id,
            UserClosetItem.item_id == item_id,
        )
    ).scalar_one_or_none()
    
    if existing_closet_item is not None:
        raise AlreadySavedError()
    
    # 3. 옷장에 아이템 저장
    closet_item = UserClosetItem(
        user_id=user_id,
        item_id=item_id,
    )
    db.add(closet_item)
    db.commit()
    db.refresh(closet_item)
    
    return closet_item.added_at


def delete_closet_item(
    db: Session,
    user_id: int,
    item_id: int,
) -> datetime:
    """
    옷장에서 아이템을 삭제합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    item_id:
        아이템 ID
        
    Returns
    -------
    datetime:
        삭제 일시 (현재 시간 UTC)
        
    Raises
    ------
    ItemNotFoundError:
        아이템이 존재하지 않는 경우
    ItemNotInClosetError:
        옷장에 저장되지 않은 아이템인 경우
    """
    # 1. 아이템 존재 여부 확인
    item = db.get(Item, item_id)
    if item is None:
        raise ItemNotFoundError()
    
    # 2. 옷장에 저장된 아이템인지 확인
    closet_item = db.execute(
        select(UserClosetItem)
        .where(
            UserClosetItem.user_id == user_id,
            UserClosetItem.item_id == item_id,
        )
    ).scalar_one_or_none()
    
    if closet_item is None:
        raise ItemNotInClosetError()
    
    # 3. 옷장에서 아이템 삭제
    db.delete(closet_item)
    db.commit()
    
    # 4. 삭제 일시 반환 (현재 시간 UTC)
    return datetime.now(timezone.utc)


# 카테고리 필터 타입 정의
CategoryFilter = Literal["all", "top", "bottom", "outer"]


def _build_closet_item_payload(
    item: Item,
    closet_item: UserClosetItem,
) -> ClosetItemPayload:
    """
    옷장 아이템 페이로드를 생성합니다.
    
    Parameters
    ----------
    item:
        아이템 모델
    closet_item:
        옷장 아이템 모델
        
    Returns
    -------
    ClosetItemPayload:
        옷장 아이템 페이로드
    """
    # 메인 이미지 추출 (is_main=True 우선, 없으면 첫 번째 이미지)
    main_image = next(
        (img for img in item.images if img.is_main),
        item.images[0] if item.images else None
    )
    image_url = main_image.image_url if main_image else None
    
    # price 변환 (Numeric → int, 원 단위)
    price = int(float(item.price)) if item.price is not None else None
    
    return ClosetItemPayload(
        id=item.item_id,
        category=item.category,
        brand=item.brand_name_ko,
        name=item.item_name,
        price=price,
        imageUrl=image_url,
        purchaseUrl=item.purchase_url,
        savedAt=closet_item.added_at,
    )


async def get_closet_items(
    db: Session,
    user_id: int,
    category: CategoryFilter = "all",
    page: int = 1,
    limit: int = 20,
) -> tuple[list[ClosetItemPayload], PaginationPayload, CategoryCountsPayload]:
    """
    옷장에 저장된 아이템 목록을 조회합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    category:
        카테고리 필터 ("all"이면 필터링 안 함)
    page:
        페이지 번호 (1부터 시작)
    limit:
        페이지당 개수
        
    Returns
    -------
    tuple[list[ClosetItemPayload], PaginationPayload, CategoryCountsPayload]:
        (아이템 페이로드 리스트, 페이지네이션 정보, 카테고리별 개수)
    """
    # 1. categoryCounts 계산 (필터 적용 전 전체 카테고리별 개수)
    category_counts_query = (
        select(Item.category, func.count(UserClosetItem.item_id))
        .join(UserClosetItem, Item.item_id == UserClosetItem.item_id)
        .where(UserClosetItem.user_id == user_id)
        .group_by(Item.category)
    )
    category_counts_result = db.execute(category_counts_query).all()
    
    # 카테고리별 개수 딕셔너리 생성
    category_counts_dict = {cat: 0 for cat in ["top", "bottom", "outer"]}
    for cat, count in category_counts_result:
        if cat in category_counts_dict:
            category_counts_dict[cat] = count
    
    category_counts = CategoryCountsPayload(
        top=category_counts_dict["top"],
        bottom=category_counts_dict["bottom"],
        outer=category_counts_dict["outer"],
    )
    
    # 2. category 필터 적용하여 쿼리 구성
    query = (
        select(UserClosetItem)
        .join(Item, UserClosetItem.item_id == Item.item_id)
        .where(UserClosetItem.user_id == user_id)
    )
    
    if category != "all":
        query = query.where(Item.category == category)
    
    # 3. 전체 개수 조회 (페이지네이션용)
    count_query = (
        select(func.count(UserClosetItem.item_id))
        .join(Item, UserClosetItem.item_id == Item.item_id)
        .where(UserClosetItem.user_id == user_id)
    )
    
    if category != "all":
        count_query = count_query.where(Item.category == category)
    
    total_items = db.execute(count_query).scalar_one()
    
    # 결과가 없으면 빈 결과 반환
    if total_items == 0:
        return [], PaginationPayload(
            currentPage=page,
            totalPages=0,
            totalItems=0,
            hasNext=False,
            hasPrev=False,
        ), category_counts
    
    # 4. 페이지네이션 적용 및 정렬 (added_at 기준 최신순)
    offset = (page - 1) * limit
    closet_items = db.execute(
        query
        .order_by(UserClosetItem.added_at.desc())
        .offset(offset)
        .limit(limit)
        .options(
            selectinload(UserClosetItem.item).selectinload(Item.images),
        )
    ).scalars().all()
    
    # 5. 페이로드 생성
    items = [
        _build_closet_item_payload(closet_item.item, closet_item)
        for closet_item in closet_items
    ]
    
    # 6. 페이지네이션 정보 계산
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
    
    return items, pagination, category_counts

