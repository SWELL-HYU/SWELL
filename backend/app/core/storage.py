"""
스토리지 서비스 추상화 및 구현 (Local / GCS).
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import io
import aiofiles
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class StorageService(ABC):
    """스토리지 서비스 추상 클래스"""

    @abstractmethod
    async def upload(self, content: bytes, destination: str, mime_type: str = "application/octet-stream") -> str:
        """
        파일을 업로드합니다.

        Args:
            content (bytes): 파일 내용
            destination (str): 저장 경로 (파일명 포함, 예: "users/1/profile.jpg")
            mime_type (str): MIME 타입

        Returns:
            str: 업로드된 파일의 접근 가능한 URL (또는 경로)
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        파일을 삭제합니다.

        Args:
            file_path (str): 파일 경로 (upload 메서드가 반환한 값)

        Returns:
            bool: 삭제 성공 여부
        """
        pass

    @abstractmethod
    async def get_presigned_url(self, file_path: str, expiration: int = 360) -> str:
        """
        파일에 접근할 수 있는 (임시) URL을 반환합니다.

        Args:
            file_path (str): upload 메서드가 반환한 Object Key 또는 경로
            expiration (int): URL의 유효 시간 (초 단위)

        Returns:
            str: 접근 가능한 임시 URL
        """
        pass


class LocalStorageService(StorageService):
    """로컬 파일 시스템 스토리지 서비스"""

    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, content: bytes, destination: str, mime_type: str = "application/octet-stream") -> str:
        full_path = self.base_dir / destination
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)
            
        logger.info(f"Local storage upload success: {full_path}")
        return f"/{self.base_dir.as_posix()}/{destination}"

    async def delete(self, file_path: str) -> bool:
        try:
            if file_path.startswith("/"):
                file_path = file_path.lstrip("/")
            
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Local storage delete success: {path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Local storage delete failed: {e}")
            return False

    async def get_presigned_url(self, file_path: str, expiration: int = 360) -> str:
        # 로컬 환경에서는 Pre-signed 개념이 없으므로 정적 파일 서빙 URL을 반환 (보안 적용 안 됨)
        return file_path


class S3StorageService(StorageService):
    """AWS S3 스토리지 서비스"""

    def __init__(
        self,
        region_name: str,
        bucket_name: str
    ):
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.s3_client = boto3.client('s3', region_name=region_name)

    async def upload(self, content: bytes, destination: str, mime_type: str = "application/octet-stream") -> str:
        import asyncio
        
        def _upload_sync():
            file_obj = io.BytesIO(content)
            try:
                self.s3_client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    destination,
                    ExtraArgs={'ContentType': mime_type}
                )
                logger.info(f"S3 upload success, Object Key: {destination}")
                # 프라이빗 아키텍처이므로 S3 절대 URL 대신 Object Key만 반환하여 DB에 저장
                return destination
            except ClientError as e:
                logger.error(f"S3 upload failed: {e}")
                raise

        try:
            return await asyncio.to_thread(_upload_sync)
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise e

    async def delete(self, file_path: str) -> bool:
        import asyncio
        
        def _delete_sync():
            try:
                if "amazonaws.com/" in file_path:
                    key = file_path.split("amazonaws.com/")[-1]
                else:
                    key = file_path
                    
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                logger.info(f"S3 delete success: {key}")
                return True
                
            except ClientError as e:
                logger.error(f"S3 delete failed: {e}")
                return False

        try:
            return await asyncio.to_thread(_delete_sync)
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    async def get_presigned_url(self, file_path: str, expiration: int = 360) -> str:
        import asyncio
        
        def _get_url_sync():
            try:
                # file_path가 이미 Object Key 상태이므로 바로 사용
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': file_path},
                    ExpiresIn=expiration
                )
                return url
            except ClientError as e:
                logger.error(f"S3 pre-signed URL generation failed: {e}")
                return file_path
                
        try:
            return await asyncio.to_thread(_get_url_sync)
        except Exception as e:
            logger.error(f"S3 pre-signed URL task failed: {e}")
            return file_path



def get_storage_service() -> StorageService:
    """환경 변수에 따라 적절한 StorageService 인스턴스를 반환합니다."""
    storage_type = os.getenv("STORAGE_TYPE", "local").lower()
    
    if storage_type == "s3":
        region = os.getenv("AWS_REGION", "ap-northeast-2")
        bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        
        if not bucket_name:
            logger.warning("AWS_S3_BUCKET_NAME not set, falling back to local storage")
            return LocalStorageService()
            
        logger.info("Initializing S3StorageService with IAM Instance Profile / Default Credentials")
        return S3StorageService(
            region_name=region, 
            bucket_name=bucket_name
        )
    
    return LocalStorageService()

