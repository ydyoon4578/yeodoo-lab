# -*- coding: utf-8 -*-
"""백업 크론이 헛돌지 않게 — 오늘치가 이미 나왔으면 run=false 를 낸다.

【왜 필요한가】
GitHub 스케줄 크론은 지연·드롭이 잦다. 실측으로 stocks 는 커밋 없이 07-21 에 고착한 적이
있고(build/check_freshness.py 주석의 사고 기록), 그날 하루치 테크니컬 신호뿐 아니라
**소급해서 만들 수 없는 누적물**(target_history·fund_history 스냅샷)이 통째로 비었다.
그래서 본 슬롯 뒤에 백업 슬롯을 둔다 — 본 슬롯이 안 뜬 날을 잃지 않기 위해서다.

그런데 백업이 매일 한 번 더 519종을 받으면 두 가지가 나빠진다.
  · 야후 쓰로틀 위험이 두 배가 되고, 그 피해는 다음 날 본 슬롯이 본다.
  · stocks.json + data/sd/ 518파일을 하루 두 번 커밋해 저장소가 두 배로 불어난다.
백업은 **본 슬롯이 안 떴을 때만** 일해야 한다.

【판정 근거를 왜 git 에서 읽나】
stocks.json 에는 생성 시각 필드가 없다(as_of 는 '자료의 기준일'이지 '돌린 날'이 아니다 —
오늘 돌려도 야후가 어제 종가까지만 주면 as_of 는 어제다). 스키마를 늘리는 대신 이미 있는
사실을 쓴다: 그 파일을 마지막으로 커밋한 시각. 잡이 성공했으면 반드시 커밋이 남는다.

얕은 클론이라 이력이 짧아 못 찾으면 '오늘 안 돎'으로 본다 — 판정을 못 하겠으면 **도는 쪽**이
안전한 방향이다(한 번 더 도는 비용 < 하루를 잃는 비용).

  python build/should_refresh.py <json경로> <event_name> <cron> >> "$GITHUB_OUTPUT"
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta, timezone
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass
try: sys.stderr.reconfigure(encoding="utf-8")   # 판정 사유(::notice::)를 stderr 로 내보내므로 여기도 필요하다
except Exception: pass

KST = timezone(timedelta(hours=9))

# 백업 슬롯의 cron 문자열. 워크플로에서 이 값을 바꾸면 여기도 바꿔야 한다 —
# 안 바꾸면 백업이 '본 슬롯'으로 판정되어 늘 돌고, 이 파일이 있는 이유가 사라진다.
BACKUP_CRON = "42 22 * * 0-5"


def last_commit_kst_date(path: str) -> str | None:
    """그 파일을 마지막으로 건드린 커밋의 KST 날짜(YYYY-MM-DD). 못 찾으면 None."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", path],
            capture_output=True, text=True, timeout=60,
        ).stdout.strip()
    except Exception:
        return None
    if not out:
        return None
    try:
        return datetime.fromisoformat(out).astimezone(KST).strftime("%Y-%m-%d")
    except Exception:
        return None


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/stocks.json"
    event = sys.argv[2] if len(sys.argv) > 2 else ""
    cron = sys.argv[3] if len(sys.argv) > 3 else ""

    # 수동 실행은 사람이 일부러 누른 것이다 — 건너뛰면 안 된다.
    if event != "schedule":
        print("run=true")
        print(f"::notice::{event or '비스케줄'} 실행 — 항상 수집한다", file=sys.stderr)
        return 0
    # 본 슬롯은 언제나 돈다. 판정 대상은 백업 슬롯뿐이다.
    if cron.strip() != BACKUP_CRON:
        print("run=true")
        print(f"::notice::본 슬롯({cron}) — 수집한다", file=sys.stderr)
        return 0

    today = datetime.now(KST).strftime("%Y-%m-%d")
    last = last_commit_kst_date(path)
    if last == today:
        print("run=false")
        print(f"::notice::백업 슬롯 — {path} 가 오늘({today}) 이미 갱신됐다. 건너뛴다", file=sys.stderr)
    else:
        print("run=true")
        print(f"::notice::백업 슬롯 — {path} 최종 갱신 {last or '확인 불가'} ≠ 오늘({today}). "
              "본 슬롯이 유실된 것으로 보고 수집한다", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
