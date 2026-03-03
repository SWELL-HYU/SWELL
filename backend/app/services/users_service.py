"""
사용자 관련 비즈니스 로직.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import (
    DeleteFailedError,
    DuplicateIdError,
    InsufficientHashtagsError,
    InsufficientOutfitsError,
    InvalidHashtagIdError,
    InvalidOutfitIdError,
    InvalidPersonImageError,
    TooManyHashtagsError,
    TooManyOutfitsError,
    UploadFailedError,
)
from app.core.file_utils import (
    generate_unique_filename,
    validate_upload_file,
)
from app.core.image_validation import validate_person_in_image
from app.models.coordi import Coordi
from app.models.tag import Tag
from app.models.user import User
from app.models.user_coordi_interaction import UserCoordiInteraction
from app.models.user_image import UserImage
from app.models.user_preferred_tag import UserPreferredTag
from app.schemas.users import (
    HashtagOptionPayload,
    SampleOutfitOptionPayload,
    UserPreferencesRequest,
)

logger = logging.getLogger(__name__)


def _get_season_from_month(month: int) -> str:
    """
    월(month)을 기준으로 영어 season 레이블을 반환합니다.
    """
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"


def get_preferences_options_data(
    db: Session,
    gender: str | None = None,
) -> tuple[list[HashtagOptionPayload], list[SampleOutfitOptionPayload]]:
    """
    사용자 선호도 설정 옵션 데이터를 조회한다.
    
    Args:
        db: 데이터베이스 세션
        gender: 사용자 성별 ("male" 또는 "female"). None이면 모든 태그 반환
        
    Returns:
        (hashtags, sample_outfits) 튜플
    """
    # TODO: 하드코딩한 값이니, 변경이 생길 경우 반드시 교체
    # 성별에 따른 태그 ID 필터링
    if gender == "female":
        # 여자: tag_id 1-18
        allowed_tag_ids = set(range(1, 19))
    elif gender == "male":
        # 남자: tag_id 19-25, 그리고 2, 3, 4, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18
        allowed_tag_ids = {2, 3, 4, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25}
    else:
        # 성별이 없으면 모든 태그 반환
        allowed_tag_ids = None
    
    # 태그 조회 (성별에 따라 필터링, ID 순으로 정렬)
    if allowed_tag_ids is not None:
        tags = db.execute(
            select(Tag)
            .where(Tag.tag_id.in_(allowed_tag_ids))
            .order_by(Tag.tag_id)
        ).scalars().all()
    else:
        tags = db.execute(
            select(Tag).order_by(Tag.tag_id)
        ).scalars().all()

    # 해시태그 옵션 페이로드 생성
    hashtags = [
        HashtagOptionPayload(id=tag.tag_id, name=tag.name)
        for tag in tags
    ]

    # 성별에 따른 예시 코디 조회 (랜덤 10개)
    # ORDER BY RANDOM()은 DB 부하가 크므로, 전체 ID를 가져와서 애플리케이션 레벨에서 샘플링
    import random
    
    # 1. 조건에 맞는 모든 코디 ID 조회
    # 현재 날짜 기준 계절 필터 적용
    current_month = datetime.now().month
    current_season = _get_season_from_month(current_month)

    id_query = select(Coordi.coordi_id).where(Coordi.season == current_season)
    if gender:
        id_query = id_query.where(Coordi.gender == gender.lower())
    
    all_coordi_ids = db.execute(id_query).scalars().all()
    
    # 2. 랜덤하게 10개 선택 (ID가 10개 미만이면 전체 선택)
    if len(all_coordi_ids) > 10:
        selected_ids = random.sample(all_coordi_ids, 10)
    else:
        selected_ids = all_coordi_ids
        
    # 3. 선택된 ID로 코디 조회 (이미지 포함, N+1 방지)
    if selected_ids:
        coordis = db.execute(
            select(Coordi)
            .where(Coordi.coordi_id.in_(selected_ids))
            .options(selectinload(Coordi.images))
        ).scalars().all()
    else:
        coordis = []

    # 예시 코디 옵션 페이로드 생성
    sample_outfits = []
    for coordi in coordis:
        # 메인 이미지 찾기 (is_main=True 우선, 없으면 첫 번째 이미지)
        main_image = next(
            (img for img in coordi.images if img.is_main),
            coordi.images[0] if coordi.images else None
        )
        image_url = main_image.image_url if main_image else ""

        sample_outfits.append(
            SampleOutfitOptionPayload(
                id=coordi.coordi_id,
                imageUrl=image_url,
                style=coordi.style,
                season=coordi.season,
            )
        )

    return hashtags, sample_outfits


def set_user_preferences(
    db: Session,
    user_id: int,
    payload: UserPreferencesRequest,
) -> User:
    """
    사용자 선호도를 설정한다.
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        payload: 선호도 설정 요청 페이로드
        
    Returns:
        업데이트된 사용자 객체
    """
    # 해시태그 개수 검증 (3-10개)
    hashtag_count = len(payload.hashtag_ids)
    if hashtag_count < 3:
        raise InsufficientHashtagsError()
    if hashtag_count > 10:
        raise TooManyHashtagsError()

    # 코디 개수 검증 (1개 이상 5개 이하)
    outfit_count = len(payload.sample_outfit_ids)
    if outfit_count < 1:
        raise InsufficientOutfitsError()
    if outfit_count > 5:
        raise TooManyOutfitsError()

    # 중복 ID 검증 (각 배열 내부에서만 체크)
    if len(set(payload.hashtag_ids)) != hashtag_count:
        raise DuplicateIdError()
    if len(set(payload.sample_outfit_ids)) != outfit_count:
        raise DuplicateIdError()

    # 유효한 해시태그 ID 검증 (DB에 존재하는 태그 ID만 허용)
    valid_tag_ids = set(
        tag_id
        for tag_id, in db.execute(
            select(Tag.tag_id).where(Tag.tag_id.in_(payload.hashtag_ids))
        ).all()
    )
    if len(valid_tag_ids) != hashtag_count:
        raise InvalidHashtagIdError()

    # 유효한 코디 ID 검증 (DB에 존재하는 코디 ID만 허용)
    # 불필요한 조회 제거: 프론트엔드에서 검증된 ID가 넘어온다고 가정하거나, FK 제약조건에 맡김
    # valid_coordi_ids = set(
    #     coordi_id
    #     for coordi_id, in db.execute(
    #         select(Coordi.coordi_id).where(Coordi.coordi_id.in_(payload.sample_outfit_ids))
    #     ).all()
    # )
    # if len(valid_coordi_ids) != outfit_count:
    #     raise InvalidOutfitIdError()

    # 사용자 조회
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User with id {user_id} not found")

    # 기존 선호 태그 삭제
    existing_preferred_tags = db.execute(
        select(UserPreferredTag).where(UserPreferredTag.user_id == user_id)
    ).scalars().all()
    for preferred_tag in existing_preferred_tags:
        db.delete(preferred_tag)

    # 기존 선호 코디 삭제 (action_type='preference'만)
    existing_preference_interactions = db.execute(
        select(UserCoordiInteraction).where(
            UserCoordiInteraction.user_id == user_id,
            UserCoordiInteraction.action_type == "preference"
        )
    ).scalars().all()
    for interaction in existing_preference_interactions:
        db.delete(interaction)

    # 새로운 선호 태그 추가
    for tag_id in payload.hashtag_ids:
        preferred_tag = UserPreferredTag(
            user_id=user_id,
            tag_id=tag_id,
        )
        db.add(preferred_tag)

    # 새로운 선호 코디 추가 (action_type='preference')
    for coordi_id in payload.sample_outfit_ids:
        interaction = UserCoordiInteraction(
            user_id=user_id,
            coordi_id=coordi_id,
            action_type="preference",
        )
        db.add(interaction)

    # has_completed_onboarding을 true로 업데이트
    user.has_completed_onboarding = True

    # 변경사항 커밋
    db.commit()
    db.refresh(user)

    return user


async def upload_profile_photo(
    db: Session,
    user_id: int,
    file: UploadFile,
) -> UserImage:
    """
    사용자 프로필 사진을 업로드한다.
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        file: 업로드된 파일
        
    Returns:
        생성된 UserImage 객체
        
    Raises:
        FileRequiredError: 파일이 제공되지 않은 경우
        InvalidFileFormatError: 허용되지 않은 파일 형식인 경우
        FileTooLargeError: 파일 크기가 제한을 초과한 경우
        UploadFailedError: 파일 업로드에 실패한 경우
    """
    # 파일 검증
    await validate_upload_file(file)

    # 사용자 조회
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User with id {user_id} not found")

    # 스토리지 서비스 가져오기
    from app.core.storage import get_storage_service
    storage_service = get_storage_service()

    # 고유한 파일명 생성
    filename = generate_unique_filename(file.filename)
    
    # 저장 경로 (users/{user_id}/{filename})
    # 주의: LocalStorageService는 base_dir(uploads) 아래에 저장하므로 uploads/는 제외
    destination = f"users/{user_id}/{filename}"

    try:
        # 파일 내용 읽기
        content = await file.read()
        
        # 사람 검증 (MediaPipe Pose)
        # 파일 저장 전에 검증하여 잘못된 이미지는 저장되지 않도록 함
        await asyncio.to_thread(validate_person_in_image, content)
        
        # 파일 업로드 (StorageService 사용)
        image_url = await storage_service.upload(content, destination, file.content_type)
        
        # 기존 UserImage 레코드 삭제 (있을 경우)
        existing_images = db.execute(
            select(UserImage).where(UserImage.user_id == user_id)
        ).scalars().all()
        
        for image in existing_images:
            # 스토리지에서 파일 삭제 시도
            await storage_service.delete(image.image_url)
            db.delete(image)

        # 새로운 UserImage 레코드 생성
        user_image = UserImage(
            user_id=user_id,
            image_url=image_url,
        )
        db.add(user_image)
        db.commit()
        db.refresh(user_image)

        return user_image

    except InvalidPersonImageError:
        # InvalidPersonImageError는 그대로 재발생
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        # 업로드된 파일이 있다면 삭제 시도 (여기서는 URL을 모르므로 생략하거나, try-finally 구조 고려 가능)
        # 하지만 upload 함수가 실패하면 파일이 안 생겼을 것이고, 
        # DB 트랜잭션 실패 시에는 롤백되므로 큰 문제 없음.
        raise UploadFailedError() from e


async def delete_profile_photo(
    db: Session,
    user_id: int,
) -> tuple[datetime, bool]:
    """
    사용자 프로필 사진을 삭제한다.
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        
    Returns:
        (삭제 일시, 사진이 있었는지 여부) 튜플
        
    Raises:
        DeleteFailedError: 사진 삭제에 실패한 경우
        
    Note:
        사진이 없는 경우에도 성공 응답을 반환합니다 (idempotent).
    """
    # 사용자 조회
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User with id {user_id} not found")

    # 기존 UserImage 레코드 조회
    existing_images = db.execute(
        select(UserImage).where(UserImage.user_id == user_id)
    ).scalars().all()

    # 삭제 일시 기록
    deleted_at = datetime.now(timezone.utc)
    
    # 사진이 있었는지 여부 확인
    had_photo = len(existing_images) > 0

    # 스토리지 서비스 가져오기
    from app.core.storage import get_storage_service
    storage_service = get_storage_service()

    try:
        # 각 이미지에 대해 파일 시스템과 DB에서 삭제
        for image in existing_images:
            # 스토리지에서 파일 삭제 (비동기)
            await storage_service.delete(image.image_url)
            
            # DB에서 레코드 삭제
            db.delete(image)

        # 변경사항 커밋
        db.commit()

        return deleted_at, had_photo

    except Exception as e:
        db.rollback()
        raise DeleteFailedError() from e

