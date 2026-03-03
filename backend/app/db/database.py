import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 데이터베이스 URL 로딩
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")

# Engine 생성(Application에서 공유할 DB connection pool 생성)
engine = create_engine(
    DATABASE_URL,   
    pool_pre_ping=True,  # 연결 상태 확인: 
    echo=False  # SQL 쿼리 로깅 비활성화 (TODO: 개발 시 필요하면 True로 변경)
)

# SessionLocal 생성(Application에서 공유할 DB session 생성)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성
Base = declarative_base()

# Transaction을 위한 DB session 제공 함수
def get_db():
    """
    데이터베이스 세션 의존성 주입
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

