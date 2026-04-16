#!/bin/bash
# start.sh — iMessage Pet Bot 시작
# -----------------------------------------------------------------
cd "$(dirname "$0")"

# .env 파일 확인 — 없으면 setup 자동 실행
if [ ! -f .env ]; then
    echo "⚠️  초기 설정이 필요합니다. setup을 시작합니다..."
    echo ""
    bash "$(dirname "$0")/setup.sh"
    [ ! -f .env ] && exit 1
fi

# GIF 에셋 확인
if [ ! -f assets/gif/idle.gif ]; then
    echo "🎨 GIF 에셋 생성 중..."
    python3 assets/generate_gifs.py
fi

echo "🦀 iMessage Pet Bot 시작..."
python3 main.py
