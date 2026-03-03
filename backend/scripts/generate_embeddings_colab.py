# -*- coding: utf-8 -*-
"""
###코랩환경에서 실행하세요
"""

# @title 1. 환경 설정 및 라이브러리 설치
# 필요한 라이브러리 설치
# !pip install -q ultralytics git+https://github.com/openai/CLIP.git torch torchvision ftfy regex tqdm

import os
import json
import torch
import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm
from ultralytics import YOLO
import clip
import requests
from io import BytesIO
import re

# GPU 설정
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# 모델 로드
# 1. YOLOv8 (Person Detection)
yolo_model = YOLO("yolov8n.pt")  # nano 모델 사용 (속도 빠름), 더 정확한 성능을 원하면 yolov8x.pt 사용

# 2. CLIP (ViT-B/32)
clip_model, preprocess = clip.load("ViT-B/32", device=device)

print("Models loaded successfully!")

# @title 2. 핵심 유틸리티 함수 정의

def crop_person_from_image(image_source):
    """
    이미지(URL 또는 PIL Image)에서 사람을 탐지하여 크롭합니다.
    사람이 없으면 원본을 반환합니다.
    """
    try:
        # URL인 경우 이미지 다운로드
        if isinstance(image_source, str) and image_source.startswith('http'):
            response = requests.get(image_source, stream=True, timeout=10)
            img = Image.open(BytesIO(response.content)).convert("RGB")
        else:
            img = image_source

        # YOLO 추론
        results = yolo_model(img, verbose=False, classes=[0], conf=0.5) # class 0 = person

        # 가장 신뢰도 높은 사람 1명 찾기
        best_box = None
        max_conf = 0

        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                if conf > max_conf:
                    max_conf = conf
                    best_box = box.xyxy[0].cpu().numpy() # [x1, y1, x2, y2]

        # 크롭
        if best_box is not None:
            x1, y1, x2, y2 = map(int, best_box)
            # 여유 공간(Padding)을 약간 주면 좋음 (옵션)
            width, height = img.size
            pad_x = int((x2 - x1) * 0.05)
            pad_y = int((y2 - y1) * 0.05)

            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(width, x2 + pad_x)
            y2 = min(height, y2 + pad_y)

            cropped_img = img.crop((x1, y1, x2, y2))
            return cropped_img, True # Cropped

        return img, False # Not cropped (원본 반환)

    except Exception as e:
        print(f"Error processing image: {e}")
        return None, False

## TODO: alpha 가중치를 변경 가능
def generate_multimodal_embedding(image, description_text, alpha=0.7):
    """
    이미지와 텍스트 임베딩을 결합하여 생성합니다.
    alpha: 이미지 임베딩 가중치 (0.0 ~ 1.0)
    """
    try:
        # 1. Image Embedding
        image_input = preprocess(image).unsqueeze(0).to(device)
        with torch.no_grad():
            image_features = clip_model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        # 2. Text Embedding (Optional)
        cleaned_text = description_text

        if cleaned_text and len(cleaned_text) > 1:
            # CLIP은 77 토큰 제한이 있으므로 truncate=True
            text_input = clip.tokenize([cleaned_text], truncate=True).to(device)
            with torch.no_grad():
                text_features = clip_model.encode_text(text_input)
            text_features /= text_features.norm(dim=-1, keepdim=True)

            # 3. Combine (Weighted Average)
            # 텍스트가 있으면 섞음
            final_embedding = (alpha * image_features) + ((1 - alpha) * text_features)
            final_embedding /= final_embedding.norm(dim=-1, keepdim=True)
        else:
            # 텍스트가 없으면 이미지만 사용
            final_embedding = image_features

        ## TODO: float32 타입인데, 수정가능
        return final_embedding.cpu().float().numpy().flatten().tolist()

    except Exception as e:
        print(f"Error generating embedding: {e}")
        return np.zeros(512).tolist()

# @title 3. 실행 및 테스트 (단일 샘플)

# 테스트용 이미지 URL 및 설명
test_url = "https://image.msscdn.net/images/style/list/2025041614264200000004483.jpg?w=260"
test_description = "깔끔한 무드의 미니멀 룩 #겨울코디 #미니멀 #남친룩 #코트"

print(f"Original Description: {test_description}")

# 1. 이미지 로드 및 크롭
print("Processing image...")
cropped_img, is_cropped = crop_person_from_image(test_url)

if cropped_img:
    # Colab에서 이미지 확인
    display(cropped_img)
    print(f"Cropped: {is_cropped}, Size: {cropped_img.size}")

    # 2. 임베딩 생성
    embedding = generate_multimodal_embedding(cropped_img, test_description)
    print(f"Embedding generated! Dimension: {len(embedding)}")
    print(f"Preview (first 5): {embedding[:5]}")
else:
    print("Failed to load image.")

# @title 4. JSON 파일 일괄 처리 (Batch Processing)

input_json_path = "coordis_export.json"  # 업로드한 파일 이름과 일치해야 함!
output_json_path = "coordis_with_embeddings.json"

def process_json_file(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found. Please upload it first.")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    processed_count = 0
    results = []

    print(f"Starting processing {len(data)} items...")

    for item in tqdm(data):
        try:
            url = item.get('image_url') or item.get('img_url')
            # coordis_export.json has 'coordi_id', make sure to preserve it
            
            desc = item.get('description', '')

            if not url:
                print(f"Skipping item {item.get('coordi_id')}: No image URL")
                results.append(item) # Keep item even if skipped, or maybe skip embedding
                continue

            # 1. Crop Person
            cropped_img, _ = crop_person_from_image(url)

            if cropped_img:
                # 2. Generate Embedding
                embedding = generate_multimodal_embedding(cropped_img, desc)

                # 결과 저장 (리스트 형태)
                item['description_embedding'] = embedding # DB Column name
                
                results.append(item)
                processed_count += 1
            else:
                 print(f"Skipping item {item.get('coordi_id')}: Crop failed")
                 results.append(item)

        except Exception as e:
            print(f"Skipping item {item.get('coordi_id')}: {e}")
            results.append(item)
            continue

    # 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Done! Processed {processed_count}/{len(data)} items.")
    print(f"Saved to {output_path}")

# 실행
if __name__ == "__main__":
    # Colab에서 실행 시 바로 작동하도록
    process_json_file(input_json_path, output_json_path)

