"""
파일 업로드 관련 유틸리티 함수.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.exceptions import FileRequiredError, FileTooLargeError, InvalidFileFormatError

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
}


def validate_file_format(file: UploadFile) -> None:
    """
    파일 형식을 검증합니다.
    
    * **검증 항목**: 파일 존재 여부, 확장자, MIME 타입
    * **허용 형식**: JPG, JPEG, PNG
    
    Args:
        file (UploadFile): 업로드된 파일
        
    Raises:
        FileRequiredError: 파일이 제공되지 않은 경우
        InvalidFileFormatError: 허용되지 않은 파일 형식인 경우
    """
    if not file or not file.filename:
        raise FileRequiredError()

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileFormatError()

    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise InvalidFileFormatError()


def validate_file_size(file: UploadFile) -> None:
    """
    파일 크기를 검증합니다. (메모리에 로드된 경우 빠른 검증)
    
    Args:
        file (UploadFile): 업로드된 파일
        
    Raises:
        FileTooLargeError: 파일 크기가 제한을 초과한 경우
    """
    if hasattr(file, "size") and file.size and file.size > MAX_FILE_SIZE:
        raise FileTooLargeError()


async def validate_upload_file(file: UploadFile) -> None:
    """
    업로드 파일을 검증합니다 (형식 및 크기).
    
    Args:
        file (UploadFile): 업로드된 파일
        
    Raises:
        FileRequiredError: 파일이 제공되지 않은 경우
        InvalidFileFormatError: 허용되지 않은 파일 형식인 경우
        FileTooLargeError: 파일 크기가 제한을 초과한 경우
    """
    validate_file_format(file)
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise FileTooLargeError()
    
    await file.seek(0)


def generate_unique_filename(original_filename: str) -> str:
    """
    고유한 파일명을 생성합니다.
    
    Args:
        original_filename (str): 원본 파일명
        
    Returns:
        str: 생성된 고유 파일명
    """
    file_ext = Path(original_filename).suffix.lower()
    unique_id = uuid.uuid4().hex[:16]
    return f"profile_{unique_id}{file_ext}"


def get_upload_directory(user_id: int) -> Path:
    """
    사용자별 업로드 디렉토리 경로를 반환합니다.
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        Path: 업로드 디렉토리 경로
    """
    return Path("uploads") / "users" / str(user_id)


def ensure_upload_directory(upload_dir: Path) -> None:
    """
    업로드 디렉토리가 존재하는지 확인하고, 없으면 생성합니다.
    
    Args:
        upload_dir (Path): 업로드 디렉토리 경로
    """
    upload_dir.mkdir(parents=True, exist_ok=True)


