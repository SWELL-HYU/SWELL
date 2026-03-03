"""
이미지 검증 관련 유틸리티 함수.
"""

from __future__ import annotations

from io import BytesIO

import mediapipe as mp
import numpy as np
from PIL import Image

from app.core.exceptions import InvalidPersonImageError

# MediaPipe Pose 초기화 (모듈 레벨에서 한 번만 초기화)
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=1,
    enable_segmentation=False,
    min_detection_confidence=0.5,
)


def validate_person_in_image(image_bytes: bytes) -> None:
    """
    이미지에 사람이 포함되어 있는지 검증합니다. MediaPipe Pose를 사용합니다.
    
    * **검증 기준**:
      - 코(NOSE) 키포인트 가시성 >= 0.5
      - 발목(LEFT_ANKLE 또는 RIGHT_ANKLE) 키포인트 가시성 >= 0.5 중 하나 이상
    
    Args:
        image_bytes (bytes): 이미지 바이너리 데이터
        
    Raises:
        InvalidPersonImageError: 사람이 포함되지 않거나 포즈가 적절하지 않은 경우
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        image_rgb = image.convert("RGB")
        
        image_array = np.array(image_rgb)
        results = pose.process(image_array)
        
        if not results.pose_landmarks:
            raise InvalidPersonImageError()
        
        landmarks = results.pose_landmarks.landmark
        
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        if nose.visibility < 0.5:
            raise InvalidPersonImageError()
        
        left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
        right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
        if left_ankle.visibility < 0.5 and right_ankle.visibility < 0.5:
            raise InvalidPersonImageError()
        
        return None
        
    except InvalidPersonImageError:
        raise
    except Exception as e:
        raise InvalidPersonImageError() from e

