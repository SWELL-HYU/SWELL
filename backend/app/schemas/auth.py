"""
인증 관련 스키마 정의.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.users import UserGender, UserPayload  # 직접 import


# 사용자 회원가입 요청 스키마
class UserCreateRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=50)
    gender: UserGender


# 사용자 로그인 요청 스키마
class UserLoginRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8)


# 회원가입 응답 데이터 스키마 1
class SignupResponseData(BaseModel):
    user: UserPayload  # forward reference 제거


# 회원가입 응답 데이터 스키마 2
class SignupResponse(BaseModel):
    success: bool = True
    data: SignupResponseData


# 로그인 응답 데이터 스키마 1
class LoginResponseData(BaseModel):
    user: UserPayload  # forward reference 제거
    token: str


# 로그인 응답 데이터 스키마 2
class LoginResponse(BaseModel):
    success: bool = True
    data: LoginResponseData


# 로그아웃 응답 데이터 스키마
class LogoutResponse(BaseModel):
    success: bool = True
    message: str = "로그아웃되었습니다"

