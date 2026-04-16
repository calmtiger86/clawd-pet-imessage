#!/bin/bash
# hooks/pet-hook.sh
# -----------------------------------------------------------------
# Claude Code hook → HTTP POST to pet server
# 비동기 실행 (& + --max-time 1)으로 Claude Code 차단 방지
# -----------------------------------------------------------------

EVENT="$1"
BODY=$(cat)

# 빈 이벤트면 무시
[ -z "$EVENT" ] && exit 0

# 서버에 상태 전송 (비동기)
curl -s -X POST "http://127.0.0.1:23456/state" \
  -H "Content-Type: application/json" \
  -d "{\"event\":\"$EVENT\",\"payload\":$BODY}" \
  --max-time 1 2>/dev/null &

exit 0
