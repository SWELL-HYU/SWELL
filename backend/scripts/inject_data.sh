#!/bin/bash
# ============================================================
# SWELL DB 데이터 주입 스크립트
#
# 실행 방법:
#   cd /home/ubuntu/SWELL/backend
#   chmod +x scripts/inject_data.sh
#   ./scripts/inject_data.sh
#
# 주의:
#   - .env의 DATABASE_URL이 올바르게 설정되어 있어야 한다.
#   - FK 제약 조건 때문에 반드시 아래 순서대로 실행해야 한다.
#   - seed_data.py는 개발 환경에서만 실행할 것! (운영 DB 오염 위험)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

# 가상환경 활성화
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "[✓] 가상환경 활성화 완료"
else
    echo "[✗] .venv/bin/activate를 찾을 수 없습니다. 가상환경을 먼저 생성하세요."
    exit 1
fi

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "[✗] .env 파일이 없습니다. .env를 먼저 설정하세요."
    exit 1
fi

echo ""
echo "========== SWELL 데이터 주입 시작 =========="
echo ""

# ① 태그 데이터 주입
echo "[1/3] 태그 데이터 주입 중..."
python scripts/load_tags.py data/final_data_태그.json
echo "[✓] 태그 데이터 주입 완료"
echo ""

# ② 코디/아이템 데이터 주입 (남성 + 여성)
echo "[2/3] 코디 데이터 주입 중... (시간이 걸릴 수 있습니다)"
python scripts/load_coordis.py data/final_data_남자.json
echo "  → 남성 데이터 완료"
python scripts/load_coordis.py data/final_data_여자.json
echo "  → 여성 데이터 완료"
echo "[✓] 코디 데이터 주입 완료"
echo ""

# ③ 테스트용 가짜 유저 데이터
echo "[3/3] 테스트용 유저 데이터 주입 중..."
echo "  ⚠️  운영 DB에서는 절대 실행하지 마세요!"
python scripts/seed_data.py
echo "[✓] 테스트 유저 데이터 주입 완료"
echo ""

echo "========== SWELL 데이터 주입 완료 =========="
