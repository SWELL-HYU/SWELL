"""
아이템 관련 API 라우터.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.security import extract_bearer_token
from app.db.database import get_db
from app.schemas.items import ItemDetailPayload, ItemDetailResponse, ItemDetailResponseData
from app.services.auth_service import get_user_from_token
from app.services.item_service import get_item_by_id

# 아이템 API 라우터 (접두사: /items)
router = APIRouter(prefix="/items", tags=["Items"])

def _build_item_payload(item) -> ItemDetailPayload:
    """
    데이터베이스 아이템 객체를 API 응답용 페이로드(ItemDetailPayload)로 변환합니다.
    """

    # 메인 이미지 추출
    # 메인 이미지가 있으면 메인 이미지 URL을 사용, 없으면 첫 번째 이미지 URL을 사용
    main_image: Optional[str] = None
    if getattr(item, "images", None):
        main_image = next(
            (image.image_url for image in item.images if getattr(image, "is_main", False)),
            item.images[0].image_url,
        )

    # 아이템 페이로드 생성
    payload = ItemDetailPayload.model_validate(
        {
            "id": str(item.item_id),
            "category": item.item_type,
            "brand": item.brand_name_ko,
            "name": item.item_name,
            "price": float(item.price) if item.price is not None else None,
            "imageUrl": main_image,
            "purchaseUrl": item.purchase_url,
            "createdAt": item.created_at,
        },
        from_attributes=False,
    )

    return payload

@router.get(
    "/{item_id}",
    status_code=status.HTTP_200_OK,
    response_model=ItemDetailResponse,
)
def read_item_detail(
    item_id: int,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> ItemDetailResponse:
    """
    특정 아이템의 상세 정보를 조회합니다.
    
    - 제공된 item_id로 구성된 구체적인 브랜드, 가격, 구매 URL 등을 반환합니다.
    - 내부적으로 인증 토큰이 유효한지 검사만 진행합니다.
    """
    token = extract_bearer_token(authorization)
    get_user_from_token(db, token)

    item = get_item_by_id(db, item_id)
    item_payload = _build_item_payload(item)

    return ItemDetailResponse(
        data=ItemDetailResponseData(
            item=item_payload,
        )
    )


