"""
가상 피팅 관련 API 라우터.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.security import extract_bearer_token
from app.db.database import get_db
from app.schemas.virtual_fitting import (
    DeleteFittingHistoryResponse,
    FittingHistoryResponse,
    VirtualFittingJobStatusResponse,
    VirtualFittingRequest,
    VirtualFittingResponse,
)
from app.services.auth_service import get_user_from_token
from app.services.virtual_fitting_service import (
    _process_virtual_fitting_async,
    delete_virtual_fitting_history,
    get_virtual_fitting_history,
    get_virtual_fitting_status,
    start_virtual_fitting,
)


def _process_virtual_fitting_with_new_session(
    fitting_id: int,
    user_id: int,
    items,
) -> None:
    """
    새로운 DB 세션을 생성하여 가상 피팅 처리를 수행합니다.
    백그라운드 작업에서 호출됩니다.
    """
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        import asyncio
        asyncio.run(
            _process_virtual_fitting_async(
                db=db,
                fitting_id=fitting_id,
                user_id=user_id,
                items=items,
            )
        )
    finally:
        db.close()

router = APIRouter(prefix="/virtual-fitting", tags=["Virtual Fitting"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=FittingHistoryResponse,
)
async def get_virtual_fitting_history_endpoint(
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    limit: int = Query(default=20, ge=1, le=50, description="페이지당 개수"),
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> FittingHistoryResponse:
    """
    유저가 시도했던 피팅 히스토리(목록)를 반환합니다.
    
    - 최신 요청 순(내림차순)으로 반환합니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)
    
    history_data = get_virtual_fitting_history(
        db=db,
        user_id=user.user_id,
        page=page,
        limit=limit,
    )
    
    return FittingHistoryResponse(
        data=history_data,
    )


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=VirtualFittingResponse,
)
async def start_virtual_fitting_endpoint(
    request: VirtualFittingRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> VirtualFittingResponse:
    """
    신규 가상 피팅 작업을 트리거합니다.
    
    - 무거운 이미지 생성 로직은 스레드 풀(Background Task)을 통해 비동기 처리합니다.
    - 클라이언트에는 지연 없이 즉시 작업(Job) ID를 반환합니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)
    
    # 가상 피팅 작업 정보 초기화 (데이터베이스 레코드 사전 발급)
    fitting_id = start_virtual_fitting(
        db=db,
        user_id=user.user_id,
        request=request,
    )
    
    # 백그라운드 작업을 등록하여 별도의 스레드에서 생성 프로세스 수행
    background_tasks.add_task(
        _process_virtual_fitting_with_new_session,
        fitting_id=fitting_id,
        user_id=user.user_id,
        items=request.items,
    )
    
    from app.models.fitting_result import FittingResult
    fitting_result = db.get(FittingResult, fitting_id)
    
    return VirtualFittingResponse(
        data={
            "jobId": fitting_id,
            "status": fitting_result.status,
            "createdAt": fitting_result.created_at,
        }
    )


@router.get(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    response_model=VirtualFittingJobStatusResponse,
)
async def get_virtual_fitting_status_endpoint(
    job_id: int,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> VirtualFittingJobStatusResponse:
    """
    비동기로 수행 중인 피팅 작업의 현재 상태(Status)를 조회합니다.
    
    상태에 따라 다음 필드를 제공합니다:
    - processing: 현재 처리 단계 정보
    - completed: 결과 이미지 URL, 추천 코멘트, 처리 소요 시간
    - failed: 에러 메시지
    
    클라이언트에서 실시간 프로그레스 바 구현 등을 위해 주기적으로(Polling) 호출할 수 있습니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)
    
    status_payload = get_virtual_fitting_status(
        db=db,
        fitting_id=job_id,
        user_id=user.user_id,
    )
    
    return VirtualFittingJobStatusResponse(
        data=status_payload,
    )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    response_model=DeleteFittingHistoryResponse,
)
async def delete_virtual_fitting_history_endpoint(
    job_id: int,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> DeleteFittingHistoryResponse:
    """
    완료 또는 실패한 가상 피팅 이력을 영구 삭제합니다.
    """
    token = extract_bearer_token(authorization)
    user = get_user_from_token(db, token)
    
    deleted_at = delete_virtual_fitting_history(
        db=db,
        fitting_id=job_id,
        user_id=user.user_id,
    )
    
    return DeleteFittingHistoryResponse(
        data={
            "message": "가상 피팅 이력이 삭제되었습니다",
            "deletedAt": deleted_at,
        }
    )

