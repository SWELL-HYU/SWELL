"""
가상 피팅 관련 비즈니스 로직.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List, Union

import aiofiles
import httpx
from google.genai import Client, types
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import (
    DuplicateCategoryError,
    ForbiddenError,
    FittingJobNotFoundError,
    InsufficientItemsError,
    InvalidCategoryError,
    InvalidItemIdError,
    ItemNotFoundError,
    PhotoRequiredError,
    TooManyItemsError,
)
from app.models.fitting_result import FittingResult
from app.models.fitting_result_image import FittingResultImage
from app.models.fitting_result_item import FittingResultItem
from app.models.item import Item
from app.models.user_image import UserImage
from app.schemas.common import PaginationPayload
from app.schemas.virtual_fitting import (
    FittingHistoryItemPayload,
    FittingHistoryPayload,
    FittingHistoryResponseData,
    FittingItemRequest,
    VirtualFittingJobStatusCompletedPayload,
    VirtualFittingJobStatusFailedPayload,
    VirtualFittingJobStatusPayload,
    VirtualFittingJobStatusProcessingPayload,
    VirtualFittingJobStatusTimeoutPayload,
    VirtualFittingRequest,
)

logger = logging.getLogger(__name__)

# Gemini API 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL_ID")
FITTING_TIMEOUT_SECONDS = 300.0  # 5분 타임아웃


def start_virtual_fitting(
    db: Session,
    user_id: int,
    request: VirtualFittingRequest,
) -> int:
    """
    가상 피팅 작업을 시작합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    request:
        가상 피팅 요청 데이터
        
    Returns
    -------
    int:
        피팅 작업 ID (fitting_id)
        
    Raises
    ------
    PhotoRequiredError:
        사용자 사진이 업로드되지 않은 경우
    InsufficientItemsError:
        아이템이 1개 미만인 경우
    TooManyItemsError:
        아이템이 3개 초과인 경우
    DuplicateCategoryError:
        동일한 카테고리의 아이템이 중복된 경우
    InvalidCategoryError:
        유효하지 않은 카테고리인 경우
    InvalidItemIdError:
        유효하지 않은 아이템 ID가 포함된 경우
    """
    # 1. 사용자 사진 존재 확인 (UserImage 테이블에서 조회)
    user_image = db.execute(
        select(UserImage)
        .where(UserImage.user_id == user_id)
        .order_by(UserImage.created_at.desc())
    ).scalar_one_or_none()
    
    if user_image is None:
        raise PhotoRequiredError()
    
    # 2. 아이템 개수 검증
    items = request.items
    if len(items) < 1:
        raise InsufficientItemsError()
    if len(items) > 3:
        raise TooManyItemsError(message="최대 3개의 아이템만 선택할 수 있습니다")
    
    # 3. 카테고리 중복 확인 및 유효성 검증
    categories_seen = set()
    item_ids = []
    
    for item in items:
        # 카테고리 유효성 확인
        if item.category not in ("top", "bottom", "outer"):
            raise InvalidCategoryError()
        
        # 카테고리 중복 확인
        if item.category in categories_seen:
            raise DuplicateCategoryError()
        categories_seen.add(item.category)
        
        item_ids.append(item.item_id)
    
    # 4. 아이템 ID 유효성 확인 및 이미지 로드
    existing_items = db.execute(
        select(Item)
        .where(Item.item_id.in_(item_ids))
        .options(selectinload(Item.images))
    ).scalars().all()
    
    if len(existing_items) != len(item_ids):
        raise InvalidItemIdError()
    
    # 5. 아이템 이미지 존재 확인
    for item in existing_items:
        if not item.images:
            raise InvalidItemIdError(message=f"아이템 {item.item_id}에 이미지가 없습니다")
    
    # 6. FittingResult 레코드 생성
    fitting_result = FittingResult(
        user_id=user_id,
        status="processing",
    )
    db.add(fitting_result)
    db.flush()  # fitting_id를 얻기 위해 flush
    
    # 7. FittingResultItem 레코드 생성
    for item in items:
        fitting_result_item = FittingResultItem(
            fitting_id=fitting_result.fitting_id,
            item_id=item.item_id,
        )
        db.add(fitting_result_item)
    
    db.commit()
    db.refresh(fitting_result)
    
    return fitting_result.fitting_id


async def _download_image(url: str, timeout: float = 10.0) -> tuple[bytes, str] | None:
    """
    URL 또는 파일 경로에서 이미지를 다운로드합니다.
    
    Parameters
    ----------
    url:
        이미지 URL 또는 파일 경로
    timeout:
        타임아웃 (초, HTTP 요청에만 적용)
        
    Returns
    -------
    tuple[bytes, str] | None:
        (이미지 bytes, MIME 타입) 또는 None (실패 시)
    """
    try:
        logger.info(f"이미지 다운로드 시작: url={url[:100]}...")  # URL 일부만 로그

        # S3 Object Key 처리: http/https로 시작하지 않고, 로컬 경로(/)로 시작하지 않는 경우 Presigned URL로 변환
        if not url.startswith(("http://", "https://", "/")):
            from app.core.storage import get_storage_service
            storage_service = get_storage_service()
            # 다운로드 용도이므로 expiration을 짧게(60초) 설정
            url = await storage_service.get_presigned_url(url, expiration=60)
            logger.info(f"Object Key URL을 다운로드용 Presigned URL로 변환했습니다: {url[:100]}...")
        
        # 상대 경로인 경우 파일 시스템에서 읽기
        # TODO: 배포시 저장 경로 수정
        if url.startswith("/") and not url.startswith(("http://", "https://")):
            # 상대 경로를 절대 경로로 변환 (uploads 디렉토리 기준)
            file_path = Path(url.lstrip("/"))
            if not file_path.is_absolute():
                # 상대 경로인 경우 현재 작업 디렉토리 기준
                file_path = Path.cwd() / file_path
            
            if not file_path.exists():
                logger.error(f"파일을 찾을 수 없습니다: {file_path}")
                return None
            
            # 파일 읽기
            image_bytes = await asyncio.to_thread(file_path.read_bytes)
            logger.info(f"파일에서 이미지 로드 성공: path={file_path}, size={len(image_bytes)} bytes")
            
            # MIME 타입 추정 (파일 확장자 기반)
            mime_type = "image/jpeg"  # 기본값
            url_lower = url.lower()
            if url_lower.endswith((".png",)):
                mime_type = "image/png"
            elif url_lower.endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            
            logger.info(f"이미지 다운로드 완료: size={len(image_bytes)} bytes, mime_type={mime_type}")
            return image_bytes, mime_type
        
        # HTTP/HTTPS URL인 경우 기존 방식 사용
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"HTTP 요청 시작: url={url[:100]}...")
            response = await client.get(url)
            response.raise_for_status()
            image_bytes = response.content
            logger.info(f"HTTP 응답 수신: status={response.status_code}, size={len(image_bytes)} bytes, content_type={response.headers.get('content-type', 'unknown')}")
            
            # MIME 타입 추정 (URL 확장자 기반)
            mime_type = "image/jpeg"  # 기본값
            url_lower = url.lower()
            if url_lower.endswith((".png",)):
                mime_type = "image/png"
            elif url_lower.endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            
            logger.info(f"이미지 다운로드 완료: size={len(image_bytes)} bytes, mime_type={mime_type}")
            return image_bytes, mime_type
    except httpx.TimeoutException as e:
        logger.error(f"이미지 다운로드 타임아웃: url={url[:100]}..., timeout={timeout}초, 에러: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"이미지 다운로드 HTTP 에러: url={url[:100]}..., status={e.response.status_code}, 에러: {e}")
        return None
    except Exception as e:
        logger.error(f"이미지 다운로드 실패: url={url[:100]}..., 에러: {type(e).__name__}: {e}", exc_info=True)
        return None


def _generate_fitting_image_single_step_sync(
    person_or_result_image_bytes: bytes,
    person_or_result_mime_type: str,
    garment_image_bytes: bytes,
    garment_mime_type: str,
    garment_category: str,
) -> bytes | None:
    """
    동기 방식으로 Gemini API를 호출하여 단일 단계 가상 피팅 이미지를 생성합니다.
    
    Parameters
    ----------
    person_or_result_image_bytes:
        사람 이미지 또는 이전 단계 결과 이미지 bytes
    person_or_result_mime_type:
        사람 이미지 또는 결과 이미지 MIME 타입
    garment_image_bytes:
        의류 이미지 bytes (단일)
    garment_mime_type:
        의류 이미지 MIME 타입
    canvas_image_bytes:
        캔버스 이미지 bytes
    canvas_mime_type:
        캔버스 이미지 MIME 타입
        
    Returns
    -------
    bytes | None:
        생성된 이미지 bytes 또는 None (실패 시)
    """
    try:
        if not GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY가 설정되지 않았습니다")
            return None
        
        # 이미지 크기 로깅
        logger.info(f"Gemini API 호출 준비: person_size={len(person_or_result_image_bytes)} bytes, "
                   f"garment_size={len(garment_image_bytes)} bytes")
        
        # 이미지 크기 확인 (PIL로)
        try:
            person_img = Image.open(BytesIO(person_or_result_image_bytes))
            garment_img = Image.open(BytesIO(garment_image_bytes))
            logger.info(f"이미지 크기: person={person_img.size}, garment={garment_img.size}")
        except Exception as e:
            logger.warning(f"이미지 크기 확인 실패: {e}")
        
        client = Client(api_key=GOOGLE_API_KEY)
        
        # 카테고리별 프롬프트 분기 처리
        if garment_category == "outer":
            dressing_instruction = (
                "ACTION [OUTERWEAR]: LAYER this garment ON TOP of the subject's existing outfit. "
                "Do NOT remove the inner clothing (shirt/pants). "
                "CRITICAL: Generate the outer garment in an OPEN/UNZIPPED state to visibly reveal the inner layers underneath. "
                "Do not fully close zippers or buttons."
            )
        else:
            # top or bottom
            dressing_instruction = (
                f"ACTION [{garment_category.upper()}]: COMPLETELY REPLACE the subject's existing {garment_category} with the target garment. "
                f"Remove the original {garment_category} entirely and fit the new one naturally onto the body skin/shape."
            )

        enhanced_prompt = (
        "Role: You are an expert AI specialized in high-fidelity photorealistic virtual try-on.\n"
            "Input structure:\n"
            " - Image[1]: Reference Person (Subject to be dressed)\n"
            " - Image[2]: Garment Image (Target apparel)\n\n"

            "Objective: Synthesize a photorealistic composite where the person in Image[1] wears the garment from Image[2]. "
            "The result must be indistinguishable from a real photograph.\n\n"

            f"{dressing_instruction}\n\n"

            "Constraints: The final output must strictly match the dimensions and aspect ratio of Image[1]. "
            "Do NOT crop, resize, pad, shift, or transform the person. Preserve the background exactly if possible.\n\n"

            "Garment dressing process: Map the garment onto the body topology using physics-based draping. "
            "Simulate gravity, material stiffness, and tension folds based on the pose. "
            "Transfer environmental lighting to generate accurate 'contact shadows' (ambient occlusion) and match the film grain/noise of the reference.\n\n"

            "Preserve: FREEZE the subject's identity, facial features, hair strands, skin texture, hands, and accessories. "
            "Handle occlusions intelligently: if hair falls over shoulders, render the garment layer *under* the hair strands.\n\n"

            "Restrictions: No hallucinations of extra limbs, no distortion of face or hands, no blurring of garment textures. "
            "Do not change the body shape.\n\n"

            "Output: A single high-resolution PNG integrating the dressed subject seamlessly with professional retouching quality."
        )

        
        # 이미지 파트 생성
        logger.info("이미지 파트 생성 중...")
        person_or_result_part = types.Part.from_bytes(
            data=person_or_result_image_bytes,
            mime_type=person_or_result_mime_type
        )
        garment_part = types.Part.from_bytes(
            data=garment_image_bytes,
            mime_type=garment_mime_type
        )
        contents = [enhanced_prompt, person_or_result_part, garment_part]
        
        # Gemini API 호출
        logger.info(f"Gemini API 호출 시작: model={GEMINI_MODEL}")
        import time
        start_time = time.time()
        
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Gemini API 호출 완료: elapsed_time={elapsed_time:.2f}초")
        except Exception as api_error:
            elapsed_time = time.time() - start_time
            logger.error(f"Gemini API 호출 실패: elapsed_time={elapsed_time:.2f}초, "
                        f"error_type={type(api_error).__name__}, error={api_error}", exc_info=True)
            return None
        
        # 응답 분석
        logger.info(f"Gemini API 응답 분석: candidates_count={len(response.candidates) if hasattr(response, 'candidates') else 0}")
        
        if not hasattr(response, 'candidates') or not response.candidates:
            logger.error("Gemini API 응답에 candidates가 없습니다")
            return None
        
        # 응답에서 이미지 추출
        image_found = False
        for i, part in enumerate(response.candidates[0].content.parts):
            logger.debug(f"응답 파트 {i}: type={type(part).__name__}, has_inline_data={part.inline_data is not None}")
            if part.inline_data is not None:
                result_size = len(part.inline_data.data)
                logger.info(f"피팅 결과 이미지 추출 성공: size={result_size} bytes")
                return part.inline_data.data
        
        logger.error("응답에서 편집된 이미지를 찾지 못했습니다. 응답 구조:")
        logger.error(f"  - candidates: {len(response.candidates)}")
        if response.candidates:
            logger.error(f"  - first candidate content parts: {len(response.candidates[0].content.parts)}")
            for i, part in enumerate(response.candidates[0].content.parts):
                logger.error(f"    part[{i}]: type={type(part).__name__}, "
                           f"inline_data={part.inline_data is not None if hasattr(part, 'inline_data') else 'N/A'}")
        return None
        
    except Exception as e:
        logger.error(f"Gemini API 호출 실패: error_type={type(e).__name__}, error={e}", exc_info=True)
        return None


def _generate_llm_message_sync(
    image_bytes: bytes,
    mime_type: str,
) -> str | None:
    """
    동기 방식으로 Gemini API를 호출하여 가상 피팅 결과 이미지에 대한 추천 메시지를 생성합니다.
    
    Parameters
    ----------
    image_bytes:
        가상 피팅 결과 이미지 bytes
    mime_type:
        이미지 MIME 타입
        
    Returns
    -------
    str | None:
        생성된 LLM 메시지. 실패 시 None 반환.
    """
    try:
        if not GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY가 설정되지 않았습니다")
            return None
        
        client = Client(api_key=GOOGLE_API_KEY)
        
        # 프롬프트 구성
        # TODO: 프롬프트 수정
        prompt = (
            "이 가상 피팅 결과 이미지를 보고 사용자에게 친근하고 매력적인 추천 메시지를 작성해주세요. "
            "한 문장으로, 이모지를 포함하여 작성해주세요. (최대 50자)"
        )
        
        # 이미지 파트 생성
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )
        
        # 콘텐츠 구성
        contents = [prompt, image_part]
        
        # Gemini API 호출
        response = client.models.generate_content(
            model="gemini-2.5-flash", # TODO: 모델 변경 가능
            contents=contents,
        )
        
        # 응답 텍스트 추출
        if hasattr(response, "text") and response.text:
            return response.text.strip()
        
        return None
    except Exception as e:
        logger.error(f"LLM 메시지 생성 실패: {e}")
        return None


async def _process_virtual_fitting_async(
    db: Session,
    fitting_id: int,
    user_id: int,
    items: List[FittingItemRequest],
) -> None:
    """
    가상 피팅 처리를 비동기로 수행합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    fitting_id:
        피팅 작업 ID
    user_id:
        사용자 ID
    items:
        피팅할 아이템 목록
    """
    try:
        logger.info(f"가상 피팅 처리 시작: fitting_id={fitting_id}, user_id={user_id}, items_count={len(items)}")
        
        # 아이템 처리 순서 강제: 상의 -> 하의 -> 아우터
        # (상의를 먼저 입고 하의를 입는 것이 일반적, 아우터는 마지막에 위에 걸침)
        priority = {"top": 1, "bottom": 2, "outer": 3}
        items.sort(key=lambda x: priority.get(x.category, 99))
        
        logger.info(f"아이템 목록(정렬됨): {[{'item_id': item.item_id, 'category': item.category} for item in items]}")
        
        # 사용자 사진 조회
        user_image = db.execute(
            select(UserImage)
            .where(UserImage.user_id == user_id)
            .order_by(UserImage.created_at.desc())
        ).scalar_one_or_none()
        
        if user_image is None:
            logger.error(f"사용자 사진 없음: user_id={user_id}")
            raise PhotoRequiredError()
        
        logger.info(f"사용자 사진 조회 성공: image_url={user_image.image_url}")
        
        # 사람 이미지 다운로드
        logger.info("사용자 이미지 다운로드 시작...")
        person_result = await _download_image(user_image.image_url)
        if person_result is None:
            logger.error("사용자 사진 다운로드 실패")
            raise Exception("사용자 사진 다운로드 실패")
        person_image_bytes, person_mime_type = person_result
        logger.info(f"사용자 이미지 다운로드 완료: size={len(person_image_bytes)} bytes, mime_type={person_mime_type}")
        
        # 아이템 조회
        item_ids = [item.item_id for item in items]
        logger.info(f"아이템 조회 시작: item_ids={item_ids}")
        db_items = db.execute(
            select(Item)
            .where(Item.item_id.in_(item_ids))
            .options(selectinload(Item.images))
        ).scalars().all()
        
        logger.info(f"아이템 조회 완료: found_count={len(db_items)}, requested_count={len(item_ids)}")
        
        # 아이템 ID로 매핑
        item_dict = {item.item_id: item for item in db_items}
        
        # 의류 이미지 다운로드
        garment_results = []
        for item_request in items:
            logger.info(f"아이템 이미지 처리 시작: item_id={item_request.item_id}, category={item_request.category}")
            db_item = item_dict.get(item_request.item_id)
            if db_item is None:
                logger.error(f"아이템을 찾을 수 없습니다: item_id={item_request.item_id}")
                raise Exception(f"아이템을 찾을 수 없습니다: item_id={item_request.item_id}")
            
            logger.info(f"아이템 정보: item_id={db_item.item_id}, name={db_item.item_name}, images_count={len(db_item.images)}")
            
            # 메인 이미지 추출
            main_image = next(
                (img for img in db_item.images if img.is_main),
                db_item.images[0] if db_item.images else None
            )
            
            if main_image is None:
                logger.error(f"아이템 이미지를 찾을 수 없습니다: item_id={item_request.item_id}, images_count={len(db_item.images)}")
                raise Exception(f"아이템 이미지를 찾을 수 없습니다: item_id={item_request.item_id}")
            
            logger.info(f"아이템 이미지 선택: image_url={main_image.image_url}, is_main={main_image.is_main}")
            
            result = await _download_image(main_image.image_url)
            if result is None:
                logger.error(f"아이템 이미지 다운로드 실패: item_id={item_request.item_id}, image_url={main_image.image_url}")
                raise Exception(f"아이템 이미지 다운로드 실패: item_id={item_request.item_id}")
            
            garment_bytes, garment_mime = result
            logger.info(f"아이템 이미지 다운로드 완료: item_id={item_request.item_id}, size={len(garment_bytes)} bytes, mime_type={garment_mime}")
            garment_results.append(result)
        

        
        # 2. FittingResult 조회
        fitting_result = db.get(FittingResult, fitting_id)
        if fitting_result is None:
            logger.error(f"FittingResult를 찾을 수 없습니다: fitting_id={fitting_id}")
            return
        
        # 3. 순차적 피팅 처리
        current_image_bytes = person_image_bytes
        current_mime_type = person_mime_type
        
        # 전체 작업에 대한 타임아웃 적용
        async def sequential_fitting():
            nonlocal current_image_bytes, current_mime_type
            
            for i, (item, garment_result) in enumerate(zip(items, garment_results)):
                garment_bytes, garment_mime = garment_result
                
                logger.info(f"피팅 단계 {i+1}/{len(items)} 시작: category={item.category}, item_id={item.item_id}")
                # current_step 업데이트
                fitting_result.current_step = item.category
                db.commit()
                logger.info(f"피팅 단계 진행: fitting_id={fitting_id}, step={item.category}")
                
                # 단일 단계 피팅 호출
                result_image = await asyncio.to_thread(
                    _generate_fitting_image_single_step_sync,
                    current_image_bytes,
                    current_mime_type,
                    garment_bytes,
                    garment_mime,
                    item.category,
                )
                
                if result_image is None:
                    # 실패 처리
                    fitting_result.failed_step = item.category
                    db.commit()
                    raise Exception(f"피팅 실패: {item.category}")
                
                # 다음 단계를 위해 현재 이미지 업데이트
                current_image_bytes = result_image
                current_mime_type = "image/png"  # Gemini 응답은 PNG
            
            return current_image_bytes
        
        # 순차적 피팅 실행 (전체 타임아웃 적용)
        final_image_bytes = await asyncio.wait_for(
            sequential_fitting(),
            timeout=FITTING_TIMEOUT_SECONDS,
        )
        
        # 4. LLM 메시지 생성 (최종 이미지로)
        logger.info(f"LLM 메시지 생성 시작: fitting_id={fitting_id}")
        llm_message = await asyncio.wait_for(
            asyncio.to_thread(
                _generate_llm_message_sync,
                final_image_bytes,
                "image/png",
            ),
            timeout=15.0,  # LLM 타임아웃
        )
        
        # 5. 결과 이미지 저장
        # 스토리지 서비스 가져오기
        from app.core.storage import get_storage_service
        storage_service = get_storage_service()
        
        filename = f"fitting_{fitting_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
        destination = f"fitting/{filename}"
        
        # 파일 업로드 (StorageService 사용)
        image_url = await storage_service.upload(final_image_bytes, destination, "image/png")
        
        # 6. FittingResult 상태 업데이트 및 이미지 저장
        fitting_result.status = "completed"
        fitting_result.finished_at = datetime.now(timezone.utc)
        fitting_result.current_step = None  # 완료 시 current_step 초기화
        if llm_message:
            fitting_result.llm_message = llm_message
        
        fitting_result_image = FittingResultImage(
            fitting_id=fitting_id,
            image_url=image_url,
        )
        db.add(fitting_result_image)
        
        db.commit()
        
        logger.info(f"가상 피팅 처리 완료: fitting_id={fitting_id}")
        
    except asyncio.TimeoutError:
        logger.error(f"가상 피팅 처리 타임아웃: fitting_id={fitting_id}")
        fitting_result = db.get(FittingResult, fitting_id)
        if fitting_result:
            fitting_result.status = "timeout"
            fitting_result.finished_at = datetime.now(timezone.utc)
            fitting_result.current_step = None
            db.commit()
    except Exception as e:
        logger.error(f"가상 피팅 처리 실패: fitting_id={fitting_id}, 에러: {e}")
        fitting_result = db.get(FittingResult, fitting_id)
        if fitting_result:
            fitting_result.status = "failed"
            fitting_result.finished_at = datetime.now(timezone.utc)
            # failed_step은 이미 sequential_fitting()에서 설정됨
            fitting_result.current_step = None
            db.commit()


# 카테고리명 한글 매핑
CATEGORY_NAME_MAP = {
    "top": "상의",
    "bottom": "하의",
    "outer": "아우터",
}


async def get_virtual_fitting_status(
    db: Session,
    fitting_id: int,
    user_id: int,
) -> VirtualFittingJobStatusPayload:
    """
    가상 피팅 작업의 상태를 조회합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    fitting_id:
        피팅 작업 ID
    user_id:
        사용자 ID
        
    Returns
    -------
    VirtualFittingJobStatusPayload:
        상태별 페이로드 (Processing, Completed, Failed, Timeout)
        
    Raises
    ------
    FittingJobNotFoundError:
        피팅 작업을 찾을 수 없는 경우
    ForbiddenError:
        다른 사용자의 작업에 접근하려는 경우
    """
    # 1. FittingResult 조회
    fitting_result = db.get(FittingResult, fitting_id)
    if fitting_result is None:
        raise FittingJobNotFoundError()
    
    # 2. 권한 확인
    if fitting_result.user_id != user_id:
        raise ForbiddenError()
    
    # 3. 상태별 페이로드 생성
    status = fitting_result.status
    
    if status == "processing":
        # Processing 상태
        if fitting_result.current_step is None:
            # current_step이 None인 경우는 없어야 하지만, 안전을 위해 처리
            current_step = "top"
        else:
            current_step = fitting_result.current_step
        
        return VirtualFittingJobStatusProcessingPayload(
            jobId=fitting_id,
            status="processing",
            currentStep=current_step,
        )
    
    elif status == "completed":
        # Completed 상태
        # 이미지 URL 조회 (하나의 이미지만 존재)
        if not fitting_result.images:
            # 이미지가 없는 경우는 없어야 하지만, 안전을 위해 처리
            raise FittingJobNotFoundError()
        
        from app.core.storage import get_storage_service
        storage_service = get_storage_service()
        result_image_url = await storage_service.get_presigned_url(
            fitting_result.images[0].image_url, 
            expiration=3600
        )
        
        # LLM 메시지 처리
        llm_message = fitting_result.llm_message
        if llm_message is None:
            llm_message = "메시지 생성 중 오류가 발생했습니다"
        
        # processingTime 계산
        if fitting_result.finished_at and fitting_result.created_at:
            processing_time = int(
                (fitting_result.finished_at - fitting_result.created_at).total_seconds()
            )
        else:
            processing_time = 0
        
        return VirtualFittingJobStatusCompletedPayload(
            jobId=fitting_id,
            status="completed",
            resultImageUrl=result_image_url,
            llmMessage=llm_message,
            completedAt=fitting_result.finished_at,
            processingTime=processing_time,
        )
    
    elif status == "failed":
        # Failed 상태
        # 에러 메시지 동적 생성
        if fitting_result.failed_step:
            category_name = CATEGORY_NAME_MAP.get(
                fitting_result.failed_step,
                fitting_result.failed_step,
            )
            error_message = f"{category_name} 피팅 중 오류가 발생했습니다"
        else:
            error_message = "피팅 중 오류가 발생했습니다"
        
        return VirtualFittingJobStatusFailedPayload(
            jobId=fitting_id,
            status="failed",
            error=error_message,
            failedStep=fitting_result.failed_step or "unknown",
            failedAt=fitting_result.finished_at,
        )
    
    elif status == "timeout":
        # Timeout 상태
        # 에러 메시지 동적 생성
        error_message = f"처리 시간을 초과했습니다 ({int(FITTING_TIMEOUT_SECONDS)}초)"
        
        return VirtualFittingJobStatusTimeoutPayload(
            jobId=fitting_id,
            status="timeout",
            error=error_message,
            timeoutAt=fitting_result.finished_at,
        )
    
    else:
        # 알 수 없는 상태
        raise FittingJobNotFoundError()


async def get_virtual_fitting_history(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 20,
) -> FittingHistoryResponseData:
    """
    가상 피팅 이력을 조회합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    user_id:
        사용자 ID
    page:
        페이지 번호 (기본값: 1)
    limit:
        페이지당 개수 (기본값: 20)
        
    Returns
    -------
    FittingHistoryResponseData:
        가상 피팅 이력 및 페이지네이션 정보
    """
    # 1. 전체 개수 조회
    count_query = select(func.count(FittingResult.fitting_id)).where(
        FittingResult.user_id == user_id
    )
    total_items = db.execute(count_query).scalar_one()
    
    # 결과가 없으면 빈 결과 반환
    if total_items == 0:
        return FittingHistoryResponseData(
            fittings=[],
            pagination=PaginationPayload(
                currentPage=page,
                totalPages=0,
                totalItems=0,
                hasNext=False,
                hasPrev=False,
            ),
        )
    
    # 2. 페이지네이션 적용 및 정렬 (created_at 기준 최신순)
    offset = (page - 1) * limit
    fitting_results = db.execute(
        select(FittingResult)
        .where(FittingResult.user_id == user_id)
        .order_by(FittingResult.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(
            selectinload(FittingResult.fitting_result_items).selectinload(
                FittingResultItem.item
            ),
            selectinload(FittingResult.images),
        )
    ).scalars().all()
    
    # 3. 페이로드 생성
    fittings = []
    from app.core.storage import get_storage_service
    storage_service = get_storage_service()
    
    for fitting_result in fitting_results:
        # resultImageUrl 처리
        result_image_url = None
        if fitting_result.status == "completed" and fitting_result.images:
            result_image_url = await storage_service.get_presigned_url(
                fitting_result.images[0].image_url, 
                expiration=3600
            )
        
        # 아이템 정보 수집
        items = [
            FittingHistoryItemPayload(
                itemId=fitting_item.item.item_id,
                category=fitting_item.item.category,
                name=fitting_item.item.item_name,
            )
            for fitting_item in fitting_result.fitting_result_items
        ]
        
        fittings.append(
            FittingHistoryPayload(
                jobId=fitting_result.fitting_id,
                status=fitting_result.status,
                resultImageUrl=result_image_url,
                items=items,
                createdAt=fitting_result.created_at,
            )
        )
    
    # 4. 페이지네이션 정보 계산
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1
    
    return FittingHistoryResponseData(
        fittings=fittings,
        pagination=PaginationPayload(
            currentPage=page,
            totalPages=total_pages,
            totalItems=total_items,
            hasNext=has_next,
            hasPrev=has_prev,
        ),
    )


def delete_virtual_fitting_history(
    db: Session,
    fitting_id: int,
    user_id: int,
) -> datetime:
    """
    가상 피팅 이력을 삭제합니다.
    
    Parameters
    ----------
    db:
        데이터베이스 세션
    fitting_id:
        피팅 작업 ID
    user_id:
        사용자 ID
        
    Returns
    -------
    datetime:
        삭제 일시 (UTC)
        
    Raises
    ------
    FittingJobNotFoundError:
        피팅 작업을 찾을 수 없는 경우
    ForbiddenError:
        다른 사용자의 작업을 삭제하려는 경우
    """
    # 1. FittingResult 조회
    fitting_result = db.get(FittingResult, fitting_id)
    if fitting_result is None:
        raise FittingJobNotFoundError()
    
    # 2. 권한 확인
    if fitting_result.user_id != user_id:
        raise ForbiddenError()
    
    # 3. 파일 삭제 (FittingResultImage의 image_url에서)
    try:
        for image in fitting_result.images:
            # 파일 경로 추출 및 삭제
            try:
                file_path = Path(image.image_url.lstrip("/"))
                if not file_path.is_absolute():
                    # 상대 경로인 경우 현재 작업 디렉토리 기준
                    file_path = Path.cwd() / file_path
                
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"가상 피팅 결과 이미지 파일 삭제: {file_path}")
            except Exception as e:
                # 파일 삭제 실패는 로깅하지만 DB 삭제는 계속 진행
                # (파일이 이미 없거나 경로가 잘못된 경우 등)
                logger.warning(
                    f"Failed to delete fitting result image file: {image.image_url}. Error: {e}",
                    exc_info=True,
                )
    except Exception as e:
        # 파일 삭제 중 예외 발생 시에도 로깅만 하고 계속 진행
        logger.warning(
            f"Error while deleting fitting result image files: {e}",
            exc_info=True,
        )
    
    # 4. FittingResult 삭제 (CASCADE로 관련 데이터 자동 삭제)
    db.delete(fitting_result)
    db.commit()
    
    # 5. 삭제 일시 반환
    return datetime.now(timezone.utc)

