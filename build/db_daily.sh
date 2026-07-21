#!/bin/bash
# =====================================================================
# yeouido-lab · Postgres 일일 적재 (tailnet 안 머신에서 실행)
# =====================================================================
# GitHub Actions 러너는 Tailscale 밖이라 DB에 도달하지 못한다. 그래서 사이트
# 생성은 GH Actions가, DB 적재는 이 스크립트가 나눠 맡는다.
#
# 순서: git pull(=오늘자 산출물 수신) → 적재 → 백필(놓친 날 자동 복구)
# 이 머신이 며칠 꺼져 있어도 --backfill 이 git 이력에서 전부 되살리므로
# 실행 실패가 데이터 유실로 이어지지 않는다.
#
# 설치(매일 08:40 KST — GH Actions 푸시 07:35~08:10 이후):
#   cp build/io.yeouido.dbload.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/io.yeouido.dbload.plist
# 수동 실행: bash build/db_daily.sh
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
LOG="$REPO/.dbload.log"
exec >>"$LOG" 2>&1
echo "───── $(date '+%F %T') 시작 ─────"

# DB 도달 가능 여부 먼저 확인 — tailnet 밖이면 조용히 종료(에러 스팸 방지)
HOST="${YEOUIDO_DB_HOST:-100.88.75.91}"
if ! nc -z -G 5 "$HOST" 5432 2>/dev/null; then
  echo "DB($HOST:5432) 도달 불가 — 스킵. 다음 실행의 --backfill 이 이 날짜를 복구한다."
  exit 0
fi

git pull --rebase --autostash origin main || echo "⚠ git pull 실패 — 로컬 상태로 진행"
python3 build/db_load.py --backfill
echo "───── $(date '+%F %T') 종료 ─────"

# 로그 무한 증식 방지 (최근 2000줄만)
tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
