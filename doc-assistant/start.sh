#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 가상환경 생성 (없으면)
if [ ! -d "venv" ]; then
  echo ">>> 가상환경 생성 중..."
  python3 -m venv venv
fi

source venv/bin/activate

# Tesseract (nix-env로 설치된 경우 PATH에 추가)
TESSERACT_NIX=$(find /nix/store -maxdepth 2 -name "tesseract" -path "*/bin/tesseract" 2>/dev/null | grep "tesseract-5" | tail -1)
if [ -n "$TESSERACT_NIX" ]; then
  export PATH="$(dirname "$TESSERACT_NIX"):$PATH"
fi

echo ">>> 패키지 설치 중 (처음 실행 시 수 분 소요)..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# .env 파일에 API 키가 설정되어 있는지 확인
if grep -q "your_openai_api_key_here" .env 2>/dev/null; then
  echo ""
  echo "⚠️  .env 파일에 OPENAI_API_KEY를 설정해주세요!"
  echo "   파일 위치: $SCRIPT_DIR/.env"
  echo ""
  exit 1
fi

echo ""
echo ">>> 서버 시작: http://localhost:8000"
echo "    브라우저에서 위 주소로 접속하세요"
echo ""

cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
