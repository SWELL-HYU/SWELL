"""
LLM 서비스 (Gemini API 호출).
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx
from google.genai import Client, types

from app.models.coordi import Coordi
from app.models.user import User

# Gemini API 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "") 
GEMINI_MODEL = "gemini-2.5-flash"  # Gemini 모델 이름
TIMEOUT_SECONDS = 15.0  # 타임아웃 설정
# TODO: 15초가 적당함


def _generate_sync(
    prompt: str,
    image_bytes: Optional[bytes],
    mime_type: Optional[str],
) -> Optional[str]:
    """
    동기 방식으로 LLM 메시지를 생성합니다.
    
    Parameters
    ----------
    prompt:
        텍스트 프롬프트
    image_bytes:
        이미지 bytes (없으면 None)
    mime_type:
        이미지 MIME 타입 (없으면 None)
        
    Returns
    -------
    Optional[str]:
        생성된 LLM 메시지. 실패 시 None 반환.
    """
    try:
        # Gemini API 클라이언트 생성
        client = Client(api_key=GOOGLE_API_KEY)
        
        # 콘텐츠 구성 (이미지가 있으면 이미지와 텍스트 함께 전달)
        contents = [prompt]
        
        # 이미지가 있으면 추가
        if image_bytes and mime_type:
            try:
                # 이미지 파트 생성
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                )
                contents = [prompt, image_part]
            except Exception:
                # 이미지 파트 생성 실패 시 텍스트만 전달
                pass
        
        # 콘텐츠 생성
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
        )
        
        # 응답 텍스트 추출
        if hasattr(response, "text") and response.text:
            return response.text.strip()
        
        return None
    except Exception:
        # 모든 예외를 무시하고 None 반환
        return None


async def generate_llm_message(coordi: Coordi, user: User) -> Optional[str]:
    """
    Gemini API를 사용하여 코디에 대한 개인화된 추천 메시지를 생성합니다.
    
    비동기 처리: google.genai Client는 동기 방식이므로 asyncio.to_thread를 사용하여
    별도 스레드에서 실행하여 비동기 컨텍스트를 블로킹하지 않도록 합니다.

    Parameters
    ----------
    coordi:
        코디 정보 (Coordi 모델)
    user:
        사용자 정보 (User 모델)

    Returns
    -------
    Optional[str]:
        생성된 LLM 메시지. 실패 시 None 반환.
    """
    # API Key 확인
    if not GOOGLE_API_KEY:
        return None

    # 코디 이미지 URL 조회 (메인 이미지 우선, 없으면 첫 번째 이미지)
    image_url = None
    if coordi.images:
        main_image = next(
            (img for img in coordi.images if img.is_main),
            coordi.images[0] if coordi.images else None
        )
        if main_image:
            image_url = main_image.image_url
    
    # 이미지 다운로드 (비동기 처리)
    image_bytes = None
    mime_type = None
    if image_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                image_response = await client.get(image_url)
                image_response.raise_for_status()
                image_bytes = image_response.content
                
                # MIME 타입 추정 (URL 확장자 기반)
                mime_type = "image/jpeg"  # 기본값
                if image_url.lower().endswith((".png",)):
                    mime_type = "image/png"
                elif image_url.lower().endswith((".jpg", ".jpeg")):
                    mime_type = "image/jpeg"

        except Exception:
            # 이미지 다운로드 실패 시 None 유지 (텍스트만 전달)
            image_bytes = None
            mime_type = None
    
    # 프롬프트 구성
    # TODO: 사용자 선호 반영 가능여부 조사, 프롬프트 메세지도 변경해야함
    prompt = f"""다음 코디 정보를 바탕으로 사용자에게 친근하고 매력적인 추천 메시지를 작성해주세요.

코디 정보:
- 스타일: {coordi.style or '알 수 없음'}
- 계절: {coordi.season or '알 수 없음'}
- 설명: {coordi.description or '설명 없음'}

사용자 정보:
- 이름: {user.name or '사용자'}
- 성별: {user.gender or '알 수 없음'}

메시지는 한 문장으로, 이모지를 포함하여 친근하고 매력적으로 작성해주세요. (최대 50자)"""

    try:
        # 동기 함수를 별도 스레드에서 실행하여 비동기 컨텍스트를 블로킹하지 않음
        result = await asyncio.wait_for(
            asyncio.to_thread(_generate_sync, prompt, image_bytes, mime_type),
            timeout=TIMEOUT_SECONDS,
        )
        return result
    except asyncio.TimeoutError:
        # 타임아웃 발생 시 None 반환
        return None
    except Exception:
        # 모든 예외를 무시하고 None 반환
        return None

