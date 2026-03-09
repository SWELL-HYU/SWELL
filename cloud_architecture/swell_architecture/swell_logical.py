# swell_logical.py
from diagrams import Diagram, Cluster, Edge
from diagrams.generic.device import Mobile
from diagrams.programming.framework import React, Fastapi
from diagrams.onprem.database import Postgresql
from diagrams.programming.language import Python
from diagrams.aws.ml import Sagemaker  
from diagrams.aws.ml import Rekognition  
from diagrams.aws.storage import S3 # S3 아이콘 추가
from diagrams.onprem.compute import Server 

# 다이어그램(배경/선형), 노드(아이콘), 화살표(텍스트)의 시각적 상세 설정을 위한 속성 정의
graph_attr = {
    "splines": "ortho",        
    "nodesep": "1.2",          # 아이콘 간격 강제 확장 (글씨 겹침 최소화)
    "ranksep": "2.0",          # 노드 간 세로(가로) 흐름 간격 대폭 확장
    "bgcolor": "#F9F9F9",      
    "fontsize": "26",          
    "fontname": "Arial-Bold"   # 가독성 및 Best-practice를 위해 가장 명확한 Arial-Bold 폰트로 교체
}

node_attr = {
    "width": "0.9",            
    "height": "0.9",           
    "fontsize": "14",          
    "fontname": "Arial-Bold" 
}

edge_attr = {
    "fontsize": "13",          
    "fontname": "Arial-Bold",  
    "penwidth": "3.0",         # 화살표 굵게
    "color": "black"           # 웬만하면 화살표를 제일 깔끔한 검정색으로 통일
}

with Diagram(
    "SWELL Architecture", 
    show=False, 
    direction="LR", 
    graph_attr=graph_attr, 
    node_attr=node_attr, 
    edge_attr=edge_attr
):
    
    user_app = Mobile("User App")
    
    with Cluster("Frontend Layer"):
        frontend = React("Next.js")
        
    with Cluster("Backend Layer: AI Orchestration"):
        fastapi = Fastapi("FastAPI (Main Server)")
        
        with Cluster("Recommendation Engine"):
            cold_start = Python("Cold Start (CLIP)")
            day_model = Python("Day Model (Fast)")
            night_model = Python("Night Model (NeuMF)")
            
    with Cluster("Data & Storage Layer"):
        db = Postgresql("PostgreSQL DB")
        s3_storage = S3("S3 Bucket\n(Generated Images)") # S3 리소스 추가
        
    with Cluster("Virtual Fitting Service"):
        fitting_engine = Sagemaker("NanoBanana Engine")
        evaluation = Rekognition("Gemini API")

    # 1. 프론트엔드 - 백엔드 통신 (색상을 지정 안 하면 기본 black이 적용됨)
    user_app >> Edge(label="Swipe / Click") >> frontend
    frontend >> Edge(label="REST API") >> fastapi
    
    # 2. 백엔드 내부 추천 엔진 로직 통신 (FastAPI -> 추천 서비스들)
    fastapi >> Edge(label="1) Init User") >> cold_start
    fastapi >> Edge(label="2) Swipe Update") >> day_model
    fastapi >> Edge(label="3) Night Sync") >> night_model
    
    # 추천 로직들과 DB간의 통신
    cold_start >> Edge(label="Save") >> db
    day_model >> Edge(label="Update") >> db
    db >> Edge(label="Fetch", style="dashed") >> night_model
    night_model >> Edge(label="Retrain") >> db
    
    # 3. Virtual Fitting 요청 및 결과 반환
    fastapi >> Edge(label="Try-on Req") >> fitting_engine
    fitting_engine >> Edge(label="Validate\nQuality") >> evaluation
    evaluation >> Edge(label="Response", style="dashed") >> fastapi
    
    # 4. S3에 최종 결과 이미지 저장
    fitting_engine >> Edge(label="Save Gen-Image\n(SWELL Storage)", minlen="2") >> s3_storage
