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

【오늘 돌았어도 «미국 장이 안 들어왔으면» 다시 — 2026-09-18】
실측 09-18: 본 슬롯이 09:27 KST 에 stocks.json 을 커밋했는데 격자가 09-16 에서 멈춰
09-17 미국 세션이 빠졌다(펀더멘털·점수만 바뀜). 몇 시간 뒤 야후는 09-17 봉을 100% 주었다.
백업은 «오늘 이미 커밋됐다» 만 보고 건너뛰었고, 종목 패널에서 굽는 것(style_perf·
home_ind_perf·스타일 PDF 2쪽)이 전부 하루 뒤처졌다. 커밋 시각은 «돌았나» 이지
«다 받았나» 가 아니다.
  → --session=<json> : 그 파일의 마지막 날이 **기대 최신 미국 세션**(KST 오늘 직전의
    NYSE 거래일)보다 이르면, 오늘 이미 커밋됐어도 돈다. 뒤처졌을 때만 돌므로 쓰로틀
    절감이라는 백업의 목적은 그대로다.
  ⚠ assets.json as_of 와 비교하지 않는 이유: 그 패널엔 한국 지수가 있어 낮 슬롯에서는
    KST 오늘 날짜가 되고, 그러면 미국 격자가 늘 «뒤처짐» 으로 보여 매번 돈다.
    또 크론이 늦게 뜨면 assets 가 stocks 보다 뒤에 돌아 비교 기준 자체가 낡는다(09-18 이 그랬다).

  python build/should_refresh.py <json경로> <event_name> <cron> [--behind=산출:입력] [--session=json] >> "$GITHUB_OUTPUT"
  python build/should_refresh.py --report-session=data/stocks.json   # 판정만 출력(워크플로 경고용)
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
    # 🚨 2026-09-03 — refresh-members 에 백업 슬롯을 준다. **주 1회 잡이라 한 번 드롭되면
    #   일주일이 빈다** — 매일 잡은 다음 날 스스로 낫지만 이쪽은 안 낫는다.
    #   그리고 같은 날 이 잡에 data/index_history.json(시점정합 편입 이력) 갱신을 얹었다.
    #   그 파일은 랩 전체의 생존편향·선견 보정이 읽는 정본이고, 월 키가 밀리면
    #   index_members.at 의 이월 한도(2달)에 걸려 결국 엔진이 죽는다.
    #   ⚠ 20개 잡 중 슬롯이 하나뿐인 것이 16개다. 나머지 15개를 한꺼번에 고치지 않은 것은
    #     의도다 — 매일 잡은 다음 날 낫고, 오늘 붙인 신선도 검사가 드롭을 붉게 띄운다.
    #     주기가 길어 스스로 못 낫는 잡부터 준다.
    "45 22 * * 5": "refresh-members.yml",
    # 🚨 2026-09-18 — refresh-stocks 재시도 슬롯(11:15 KST). 야후가 전날 봉을 늦게 주는 날,
    #   07:42 백업도 같이 헛받을 수 있다. --session 판정이 «뒤처졌을 때만» 돌린다.
    "15 2 * * 1-6": "refresh-stocks.yml",
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


def _us_holidays(y):
    """NYSE 휴장일 규칙 — build/refresh_events.py 의 것을 그대로 쓴다(규칙은 한 곳에만)."""
    try:
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from refresh_events import _holidays
        return set(_holidays(y))
    except Exception:
        return set()     # 못 읽으면 주말만 뺀다 — 휴일 다음 날 한 번 더 도는 쪽으로 틀린다(안전)


def expected_us_session(now=None):
    """지금(KST) 기준으로 «이미 끝났어야 할» 가장 최근 미국 세션 날짜.

    미국 D 세션은 KST D+1 05:00~06:00 에 끝난다. 모든 슬롯이 06:50 KST 이후라
    'KST 오늘보다 앞선 마지막 NYSE 거래일' 이 곧 기대값이다.
    """
    d = (now or datetime.now(KST)).date() - timedelta(days=1)
    hol = {}
    for _ in range(15):
        if d.year not in hol:
            hol[d.year] = _us_holidays(d.year)
        if d.weekday() < 5 and d.isoformat() not in hol[d.year]:
            return d.isoformat()
        d -= timedelta(days=1)
    return None


def session_behind(path):
    """(파일의 마지막 날, 기대 세션) — 뒤처졌으면 둘을, 아니면 None."""
    got, want = _latest(path), expected_us_session()
    if got and want and got < want:
        return (got, want)
    return None


def main() -> int:
    rep = [x.split("=", 1)[1] for x in sys.argv[1:] if x.startswith("--report-session=")]
    if rep:
        # 판정만 알린다. 잡을 세우지 않는다 — 야후 지연은 실패가 아니고 재시도 슬롯이 따라온다.
        for p in rep:
            sb = session_behind(p)
            if sb:
                print("::warning::%s 가 %s 까지다 — 기대 최신 미국 세션 %s 가 아직 없다. "
                      "재시도 슬롯이 다시 받는다" % (p, sb[0], sb[1]))
            else:
                print("%s — 기대 최신 미국 세션(%s)까지 있다" % (p, expected_us_session()))
        return 0
    argv = [x for x in sys.argv[1:] if not x.startswith("--")]
    pairs = [x.split("=", 1)[1] for x in sys.argv[1:] if x.startswith("--behind=")]
    sess = [x.split("=", 1)[1] for x in sys.argv[1:] if x.startswith("--session=")]
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
    for p in sess:
        sb = session_behind(p)
        if sb:
            print("run=true")
            print("::notice::백업 슬롯 — %s 가 %s 까지인데 기대 최신 미국 세션은 %s 다. "
                  "오늘 커밋이 있어도 그 세션이 안 들어왔으므로 다시 돈다" % (p, sb[0], sb[1]),
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
