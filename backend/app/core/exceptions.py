"""
애플리케이션 전역에서 사용하는 커스텀 예외와 FastAPI 핸들러 정의.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# 비즈니스 로직에서 공통으로 사용하는 기본 예외 클래스.
# 아래에 정의된 각종 도메인 예외(DuplicateEmailError 등)가 이 클래스를 상속한다.
class AppException(Exception):
    """비즈니스 로직에서 사용하는 베이스 예외."""

    code: str = "APP_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "알 수 없는 오류가 발생했습니다."

    # 예외 메시지 초기화
    def __init__(self, *, message: Optional[str] = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)

# 이미 등록된 이메일을 사용할 때 발생하는 예외
class DuplicateEmailError(AppException):
    """이미 등록된 이메일을 사용할 때 발생하는 예외."""

    code = "EMAIL_EXISTS"
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(message="이미 가입된 이메일입니다.")

# 로그인 시 잘못된 자격 증명을 사용할 때 발생하는 예외
class InvalidCredentialsError(AppException):
    """로그인 시 잘못된 자격 증명을 사용할 때 발생하는 예외."""

    code = "INVALID_CREDENTIALS"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(message="이메일 또는 비밀번호가 올바르지 않습니다")

# 인증이 필요한 요청에서 토큰이 없거나 유효하지 않을 때 발생하는 예외
class UnauthorizedError(AppException):
    """인증이 필요한 요청에서 토큰이 없거나 유효하지 않을 때 발생하는 예외."""

    code = "UNAUTHORIZED"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, *, message: Optional[str] = None) -> None:
        super().__init__(message=message or "인증이 필요합니다")

# 요청 유효성 검증 실패 시 발생하는 예외
class ValidationError(AppException):
    """요청 유효성 검증 실패 시 사용하는 예외."""

    code = "VALIDATION_ERROR"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, *, message: Optional[str] = None) -> None:
        super().__init__(message=message or "입력값을 다시 확인해주세요.")

# 요청한 아이템이 존재하지 않을 때 발생하는 예외
class ItemNotFoundError(AppException):
    """요청한 아이템이 존재하지 않을 때 발생하는 예외."""

    code = "ITEM_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self) -> None:
        super().__init__(message="상품을 찾을 수 없습니다")

# 코디 없음 예외
class OutfitNotFoundError(AppException):
    """요청한 코디가 존재하지 않을 때 발생하는 예외."""

    code = "OUTFIT_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self) -> None:
        super().__init__(message="코디를 찾을 수 없습니다")

# 이미 좋아요한 코디 예외
class AlreadyFavoritedError(AppException):
    """이미 좋아요한 코디에 다시 좋아요를 추가할 때 발생하는 예외."""

    code = "ALREADY_FAVORITED"
    status_code = status.HTTP_409_CONFLICT

    def __init__(self) -> None:
        super().__init__(message="이미 좋아요한 코디입니다")

# 좋아요 없음 예외
class FavoriteNotFoundError(AppException):
    """좋아요하지 않은 코디에 대해 취소 요청을 할 때 발생하는 예외."""

    code = "FAVORITE_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self) -> None:
        super().__init__(message="좋아요하지 않은 코디입니다")

# 이미 옷장에 저장된 아이템 예외
class AlreadySavedError(AppException):
    """이미 옷장에 저장된 아이템을 다시 저장할 때 발생하는 예외."""

    code = "ALREADY_SAVED"
    status_code = status.HTTP_409_CONFLICT

    def __init__(self) -> None:
        super().__init__(message="이미 옷장에 저장된 아이템입니다")

# 옷장에 저장되지 않은 아이템을 삭제하려고 할 때 발생하는 예외
class ItemNotInClosetError(AppException):
    """옷장에 저장되지 않은 아이템을 삭제하려고 할 때 발생하는 예외."""

    code = "ITEM_NOT_IN_CLOSET"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self) -> None:
        super().__init__(message="옷장에 저장되지 않은 상품입니다")

# 가상 피팅 관련 예외
class PhotoRequiredError(AppException):
    """가상 피팅을 위해 사진이 필요할 때 발생하는 예외."""

    code = "PHOTO_REQUIRED"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="가상 피팅을 위해 먼저 사진을 업로드해주세요")

class DuplicateCategoryError(AppException):
    """동일한 카테고리의 아이템이 중복되었을 때 발생하는 예외."""

    code = "DUPLICATE_CATEGORY"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="동일한 카테고리의 아이템이 중복되었습니다")

class TooManyItemsError(AppException):
    """아이템 개수가 초과되었을 때 발생하는 예외."""

    code = "TOO_MANY_ITEMS"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str = "각 카테고리당 최대 1개씩만 선택할 수 있습니다") -> None:
        super().__init__(message=message)

class InsufficientItemsError(AppException):
    """아이템 개수가 부족할 때 발생하는 예외."""

    code = "INSUFFICIENT_ITEMS"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="최소 1개 이상의 아이템을 선택해주세요")

class InvalidCategoryError(AppException):
    """유효하지 않은 카테고리일 때 발생하는 예외."""

    code = "INVALID_CATEGORY"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="유효하지 않은 카테고리입니다. (top, bottom, outer 중 하나를 선택해주세요)")

class InvalidItemIdError(AppException):
    """유효하지 않은 아이템 ID가 포함되었을 때 발생하는 예외."""

    code = "INVALID_ITEM_ID"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="유효하지 않은 아이템 ID가 포함되어 있습니다")

class FittingJobNotFoundError(AppException):
    """가상 피팅 작업을 찾을 수 없을 때 발생하는 예외."""

    code = "FITTING_JOB_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self) -> None:
        super().__init__(message="가상 피팅 작업을 찾을 수 없습니다")

class ForbiddenError(AppException):
    """다른 사용자의 작업에 접근할 수 없을 때 발생하는 예외."""

    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self) -> None:
        super().__init__(message="다른 사용자의 작업에 접근할 수 없습니다")

# 해시태그 개수 부족 예외
class InsufficientHashtagsError(AppException):
    """최소 3개의 해시태그를 선택해야 할 때 발생하는 예외."""

    code = "INSUFFICIENT_HASHTAGS"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="최소 3개의 해시태그를 선택해야 합니다")

# 해시태그 개수 초과 예외
class TooManyHashtagsError(AppException):
    """최대 10개의 해시태그만 선택할 수 있을 때 발생하는 예외."""

    code = "TOO_MANY_HASHTAGS"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="최대 10개의 해시태그만 선택할 수 있습니다")

# 코디 개수 부족 예외
class InsufficientOutfitsError(AppException):
    """최소 1개의 코디를 선택해야 할 때 발생하는 예외."""

    code = "INSUFFICIENT_OUTFITS"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="최소 1개의 코디를 선택해야 합니다")

# 코디 개수 초과 예외
class TooManyOutfitsError(AppException):
    """최대 5개의 코디만 선택할 수 있을 때 발생하는 예외."""

    code = "TOO_MANY_OUTFITS"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="최대 5개의 코디만 선택할 수 있습니다")

# 유효하지 않은 해시태그 ID 예외
class InvalidHashtagIdError(AppException):
    """유효하지 않은 해시태그 ID가 포함되어 있을 때 발생하는 예외."""

    code = "INVALID_HASHTAG_ID"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="유효하지 않은 해시태그 ID가 포함되어 있습니다")

# 유효하지 않은 코디 ID 예외
class InvalidOutfitIdError(AppException):
    """유효하지 않은 코디 ID가 포함되어 있을 때 발생하는 예외."""

    code = "INVALID_OUTFIT_ID"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="유효하지 않은 코디 ID가 포함되어 있습니다")

# 중복된 ID 예외
class DuplicateIdError(AppException):
    """중복된 ID가 포함되어 있을 때 발생하는 예외."""

    code = "DUPLICATE_ID"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="중복된 ID가 포함되어 있습니다")

# 파일 형식 오류 예외
class InvalidFileFormatError(AppException):
    """JPG, PNG가 아닌 파일 형식일 때 발생하는 예외."""

    code = "INVALID_FILE_FORMAT"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="JPG, PNG 파일만 업로드 가능합니다")

# 파일 크기 초과 예외
class FileTooLargeError(AppException):
    """10MB를 초과하는 파일일 때 발생하는 예외."""

    code = "FILE_TOO_LARGE"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="파일 크기가 10MB를 초과했습니다")

# 파일 없음 예외
class FileRequiredError(AppException):
    """파일이 제공되지 않았을 때 발생하는 예외."""

    code = "FILE_REQUIRED"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="파일을 선택해주세요")

# 파일 업로드 실패 예외
class UploadFailedError(AppException):
    """파일 업로드에 실패했을 때 발생하는 예외."""

    code = "UPLOAD_FAILED"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self) -> None:
        super().__init__(message="파일 업로드에 실패했습니다")

# 파일 삭제 실패 예외
class DeleteFailedError(AppException):
    """사진 삭제에 실패했을 때 발생하는 예외."""

    code = "DELETE_FAILED"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self) -> None:
        super().__init__(message="사진 삭제에 실패했습니다")

# 사람이 포함되지 않은 이미지 예외
class InvalidPersonImageError(AppException):
    """사진에 사람이 포함되어 있지 않거나 포즈가 적절하지 않을 때 발생하는 예외."""

    code = "INVALID_PERSON_IMAGE"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self) -> None:
        super().__init__(message="사진에 사람이 포함되어 있지 않거나 포즈가 적절하지 않습니다")

# 커스텀 예외 핸들러 등록
def register_exception_handlers(app: FastAPI) -> None:
    """커스텀 예외를 FastAPI 인스턴스에 바인딩."""

    # 요청 유효성 검증 실패 시 발생하는 예외 핸들러
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        message = None
        for error in exc.errors():
            loc = error.get("loc", [])
            error_type = error.get("type")
            field_name = loc[-1] if loc else None
            
            # 이메일 필수값 검증
            if field_name == "email" and error_type == "missing":
                message = "이메일을 입력해주세요"
                break
            # 비밀번호 필수값 검증
            if field_name == "password" and error_type == "missing":
                message = "비밀번호를 입력해주세요"
                break
            # 비밀번호 길이 검증
            if field_name == "password" and error_type == "string_too_short":
                message = "비밀번호가 8자 이상이여야합니다"
                break
            # 성별 필수 검증
            if field_name == "gender" and error_type == "missing":
                message = "성별을 선택해주세요"
                break
            # 이메일 형식 검증
            if field_name == "email" and error_type in ("value_error", "type_error"):
                message = "유효하지 않은 이메일 형식입니다"
                break
            # 페이지 번호 검증
            if field_name == "page" and error_type in ("greater_than_equal", "int_parsing"):
                message = "페이지 번호는 1 이상이어야 합니다"
                break
            # 페이지당 개수 검증
            if field_name == "limit" and error_type in ("greater_than_equal", "less_than_equal", "int_parsing"):
                message = "페이지당 개수는 1 이상 50 이하여야 합니다"
                break
            # season 값 검증
            if field_name == "season" and error_type in ("literal_error", "type_error"):
                message = "유효하지 않은 season 값입니다. (all, spring, summer, fall, winter 중 하나를 선택해주세요)"
                break
            # style 값 검증
            if field_name == "style" and error_type in ("literal_error", "type_error"):
                message = "유효하지 않은 style 값입니다. (all, casual, street, sporty, minimal 중 하나를 선택해주세요)"
                break
            # gender 값 검증
            if field_name == "gender" and error_type in ("literal_error", "type_error"):
                message = "유효하지 않은 gender 값입니다. (all, male, female 중 하나를 선택해주세요)"
                break
            # outfitIds 빈 배열 검증
            if field_name in ("outfitIds", "outfit_ids") and error_type in ("list_too_short", "value_error"):
                message = "outfitIds는 최소 1개 이상이어야 합니다"
                break
            # itemId 필수값 검증
            if field_name in ("itemId", "item_id") and error_type == "missing":
                message = "아이템 ID를 입력해주세요"
                break
            # itemId 형식 검증
            if field_name in ("itemId", "item_id") and error_type in ("int_parsing", "type_error"):
                message = "유효하지 않은 아이템 ID 형식입니다"
                break
            # category 값 검증
            if field_name == "category" and error_type in ("literal_error", "type_error"):
                message = "유효하지 않은 category 값입니다. (all, top, bottom, outer 중 하나를 선택해주세요)"
                break
            # userPhotoUrl 필수값 검증
            if field_name in ("userPhotoUrl", "user_photo_url") and error_type == "missing":
                message = "사용자 사진 URL을 입력해주세요"
                break
            # items 필수값 검증
            if field_name == "items" and error_type == "missing":
                message = "피팅할 아이템 목록을 입력해주세요"
                break
            # items 배열 길이 검증
            if field_name == "items" and error_type == "list_too_short":
                message = "최소 1개 이상의 아이템을 선택해주세요"
                break
            if field_name == "items" and error_type == "list_too_long":
                message = "최대 3개의 아이템만 선택할 수 있습니다"
                break

        # ValidationError 형식으로 직접 응답 반환
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": message or "요청 유효성 검증에 실패했습니다.",
                },
            },
        )
    
    # 비즈니스 로직에서 발생하는 예외 핸들러(DuplicateEmailError, InvalidCredentialsError, UnauthorizedError, ValidationError, ItemNotFoundError 등)
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                },
            },
        )


