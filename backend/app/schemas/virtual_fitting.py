"""
가상 피팅 관련 스키마 정의.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.schemas.common import PaginationPayload


# 가상 피팅 아이템 요청 스키마
class FittingItemRequest(BaseModel):
    item_id: int = Field(alias="itemId", description="아이템 고유 ID")
    category: Literal["top", "bottom", "outer"] = Field(description="아이템 카테고리")

    class Config:
        populate_by_name = True


# 가상 피팅 시작 요청 스키마
class VirtualFittingRequest(BaseModel):
    items: List[FittingItemRequest] = Field(min_length=1, max_length=3, description="피팅할 아이템 목록")

    class Config:
        populate_by_name = True


# 가상 피팅 시작 응답 데이터 스키마 1
class VirtualFittingResponseData(BaseModel):
    job_id: int = Field(alias="jobId", description="피팅 작업 고유 ID")
    status: str = Field(description="피팅 작업 상태")
    created_at: datetime = Field(alias="createdAt", description="피팅 작업 생성 일시")

    class Config:
        populate_by_name = True


# 가상 피팅 시작 응답 데이터 스키마 2
class VirtualFittingResponse(BaseModel):
    success: bool = True
    data: VirtualFittingResponseData


# 가상 피팅 상태 조회 - Processing 상태 페이로드
class VirtualFittingJobStatusProcessingPayload(BaseModel):
    job_id: int = Field(alias="jobId", description="피팅 작업 고유 ID")
    status: str = Field(default="processing", description="피팅 작업 상태")
    current_step: str = Field(alias="currentStep", description="현재 처리 단계")

    class Config:
        populate_by_name = True


# 가상 피팅 상태 조회 - Completed 상태 페이로드
class VirtualFittingJobStatusCompletedPayload(BaseModel):
    job_id: int = Field(alias="jobId", description="피팅 작업 고유 ID")
    status: str = Field(default="completed", description="피팅 작업 상태")
    result_image_url: str = Field(alias="resultImageUrl", description="피팅 결과 이미지 URL")
    llm_message: Optional[str] = Field(alias="llmMessage", default=None, description="LLM 평가 메시지")
    completed_at: datetime = Field(alias="completedAt", description="작업 완료 일시")
    processing_time: int = Field(alias="processingTime", description="처리 시간 (초)")

    class Config:
        populate_by_name = True


# 가상 피팅 상태 조회 - Failed 상태 페이로드
class VirtualFittingJobStatusFailedPayload(BaseModel):
    job_id: int = Field(alias="jobId", description="피팅 작업 고유 ID")
    status: str = Field(default="failed", description="피팅 작업 상태")
    error: str = Field(description="에러 메시지")
    failed_step: str = Field(alias="failedStep", description="실패한 단계")
    failed_at: datetime = Field(alias="failedAt", description="작업 실패 일시")

    class Config:
        populate_by_name = True


# 가상 피팅 상태 조회 - Timeout 상태 페이로드
class VirtualFittingJobStatusTimeoutPayload(BaseModel):
    job_id: int = Field(alias="jobId", description="피팅 작업 고유 ID")
    status: str = Field(default="timeout", description="피팅 작업 상태")
    error: str = Field(description="에러 메시지")
    timeout_at: datetime = Field(alias="timeoutAt", description="타임아웃 발생 일시")

    class Config:
        populate_by_name = True


# 가상 피팅 상태 조회 - Union 타입
VirtualFittingJobStatusPayload = Union[
    VirtualFittingJobStatusProcessingPayload,
    VirtualFittingJobStatusCompletedPayload,
    VirtualFittingJobStatusFailedPayload,
    VirtualFittingJobStatusTimeoutPayload,
]


# 가상 피팅 상태 조회 응답 스키마
class VirtualFittingJobStatusResponse(BaseModel):
    success: bool = True
    data: VirtualFittingJobStatusPayload


# 가상 피팅 이력 조회 - 아이템 페이로드
class FittingHistoryItemPayload(BaseModel):
    item_id: int = Field(alias="itemId", description="아이템 고유 ID")
    category: str = Field(description="카테고리")
    name: str = Field(description="상품명")

    class Config:
        populate_by_name = True


# 가상 피팅 이력 조회 - 피팅 페이로드
class FittingHistoryPayload(BaseModel):
    job_id: int = Field(alias="jobId", description="가상 피팅 작업 고유 ID")
    status: str = Field(description="작업 상태")
    result_image_url: Optional[str] = Field(
        alias="resultImageUrl",
        default=None,
        description="결과 이미지 URL (완료된 경우만)",
    )
    items: List[FittingHistoryItemPayload] = Field(description="피팅에 사용된 아이템 목록")
    created_at: datetime = Field(alias="createdAt", description="피팅 작업 생성 일시")

    class Config:
        populate_by_name = True


# 가상 피팅 이력 조회 - 응답 데이터
class FittingHistoryResponseData(BaseModel):
    fittings: List[FittingHistoryPayload] = Field(description="가상 피팅 이력 목록")
    pagination: PaginationPayload = Field(description="페이지네이션 정보")


# 가상 피팅 이력 조회 응답 스키마
class FittingHistoryResponse(BaseModel):
    success: bool = True
    data: FittingHistoryResponseData


# 가상 피팅 이력 삭제 응답 데이터 스키마 1
class DeleteFittingHistoryResponseData(BaseModel):
    message: str
    deleted_at: datetime = Field(alias="deletedAt")

    class Config:
        populate_by_name = True


# 가상 피팅 이력 삭제 응답 데이터 스키마 2
class DeleteFittingHistoryResponse(BaseModel):
    success: bool = True
    data: DeleteFittingHistoryResponseData

