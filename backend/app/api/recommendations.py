"""
코디 추천 관련 API 라우터.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.security import extract_bearer_token
from app.db.database import get_db
from app.schemas.recommendation_response import (
    RecommendationsResponse,
    RecommendationsResponseData,
)
from app.services.auth_service import get_user_from_token
from app.services.recommendations_service import get_recommended_coordis

# 코디 추천 관련 라우터(접두사: /recommendations)
router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=RecommendationsResponse,
)
async def get_recommendations(
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    limit: int = Query(default=20, ge=1, le=50, description="페이지당 개수"),
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> RecommendationsResponse:
    """
    사용자 취향 맞춤형 최적의 코디(Outfit) 리스트를 추천합니다.
    
    - 서비스 계층에서 LLM이나 별도 추천 알고리즘을 사용해 개인화된 메시지와 함께 코디를 구성합니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)
    
    outfits, pagination = await get_recommended_coordis(
        db=db,
        user_id=user.user_id,
        page=page,
        limit=limit,
    )
    
    return RecommendationsResponse(
        data=RecommendationsResponseData(
            outfits=outfits,
            pagination=pagination,
        )
    )

