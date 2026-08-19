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

【무엇을 지키나 — 2026-08-12】
stocks 만 이 보호를 받고 있었다. assets 는 백업 슬롯이 없어 **본 슬롯이 안 뜬 날을 통째로
잃었다**(실측 08-11: 크론이 아예 발화하지 않아 시장판·스타일 성과가 하루 고착. 그 다음 날
사용자가 "기간별 수익률 업데이트가 늦네"로 알아챘다 — 화면도 그때까지 조용했다).
같은 보호를 assets 에도 붙인다.

  python build/should_refresh.py <json경로> <event_name> <cron> >> "$GITHUB_OUTPUT"
"""
from __future__ import annotations

import io
import subprocess
import sys
from datetime import datetime, timedelta, timezone
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass
try: sys.stderr.reconfigure(encoding="utf-8")   # 판정 사유(::notice::)를 stderr 로 내보내므로 여기도 필요하다
except Exception: pass

KST = timezone(timedelta(hours=9))

# 백업 슬롯의 cron 문자열들. 워크플로에서 이 값을 바꾸면 여기도 바꿔야 한다 —
# 안 바꾸면 백업이 '본 슬롯'으로 판정되어 늘 돌고, 이 파일이 있는 이유가 사라진다.
# 🚨 2026-08-12 — 문자열 하나에서 **표**로 바꿨다. assets 에도 백업을 붙이는데, 종전처럼
#   상수 하나면 assets 의 백업 cron 이 BACKUP_CRON 과 달라 '본 슬롯' 으로 판정되고
#   **매일 두 번 도는** 정반대 결과가 난다. 값이 무엇에 쓰이는지가 아니라 '어느 워크플로의
#   백업인가' 가 정보이므로 워크플로 이름을 같이 적는다(검증기가 이 표를 대조한다).
BACKUP_CRONS = {
    "42 22 * * 0-5": "refresh-stocks.yml",
    "20 23 * * 0-5": "refresh-assets.yml",
}


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


def _latest(path):
    """그 파일이 «어느 날짜까지의 자료인가». as_of 를 먼저 보고, 없으면 격자의 마지막 날."""
    import json
    try:
        d = json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return None
    v = d.get("as_of")
    if isinstance(v, str) and len(v) >= 10:
        return v[:10]
    for k in ("pxd_dates", "dates"):
        a = d.get(k)
        if isinstance(a, list) and a:
            return str(a[-1])[:10]
    return None


def behind(pairs):
    """«산출물이 입력보다 뒤처졌나» — 뒤처진 첫 쌍을 돌려준다.

    🚨 왜 필요한가(2026-08-19 사용자 지적: "스타일 전략은 왜 아직 8월 17일이 최신인교").
      refresh-assets 의 게이트는 assets.json 이 오늘 갱신됐는지만 본다. 그런데 그 잡의
      뒷단계(style_top_pdf·market_board·home_perf)는 **stocks.json** 을 읽는다.
      실측 08-19: refresh-stocks 가 06:58 에 실패했고(가격 격자 구멍) 재시도가 07:56 에야
      성공했는데, 그 사이 07:54 에 refresh-assets 가 돌아 **08-17 격자**로 스타일을 계산했다.
      그 뒤 백업 슬롯은 «assets.json 이 오늘 갱신됐다» 며 건너뛰었고, 스타일만 하루 뒤처진
      채로 굳었다. 게이트가 자기 입력만 보고 **자기 산출물은 안 봤기 때문**이다.
    ⚠ 이 판정은 «한 번 더 도는 비용 < 하루를 잃는 비용» 쪽으로 기운다 — 읽지 못하면 안 민다.
    """
    for spec in pairs:
        if ":" not in spec:
            continue
        out_p, in_p = spec.split(":", 1)
        o, i = _latest(out_p), _latest(in_p)
        if o and i and o < i:
            return (out_p, o, in_p, i)
    return None


def main() -> int:
    argv = [x for x in sys.argv[1:] if not x.startswith("--behind=")]
    pairs = [x.split("=", 1)[1] for x in sys.argv[1:] if x.startswith("--behind=")]
    path = argv[0] if len(argv) > 0 else "data/stocks.json"
    event = argv[1] if len(argv) > 1 else ""
    cron = argv[2] if len(argv) > 2 else ""

    # 수동 실행은 사람이 일부러 누른 것이다 — 건너뛰면 안 된다.
    if event != "schedule":
        print("run=true")
        print(f"::notice::{event or '비스케줄'} 실행 — 항상 수집한다", file=sys.stderr)
        return 0
    # 본 슬롯은 언제나 돈다. 판정 대상은 백업 슬롯뿐이다.
    if cron.strip() not in BACKUP_CRONS:
        print("run=true")
        print(f"::notice::본 슬롯({cron}) — 수집한다", file=sys.stderr)
        return 0

    today = datetime.now(KST).strftime("%Y-%m-%d")
    # 🚨 산출물이 입력보다 뒤처져 있으면 «오늘 이미 돌았다» 여도 돈다.
    b = behind(pairs)
    if b:
        print("run=true")
        print("::notice::백업 슬롯 — %s 가 %s 까지인데 입력 %s 는 %s 다. "
              "산출물이 입력보다 뒤처졌으므로 다시 돈다" % (b[0], b[1], b[2], b[3]),
              file=sys.stderr)
        return 0
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
