# -*- coding: utf-8 -*-
"""build/monthly_refresh.py — 월초에 **10년 창을 한 달 굴린다**. 빠진 곳만 채운다.

🚨 먼저 — 이 랩의 대부분은 **이미 자동이다.** 없는 것을 새로 만들지 않는다.

| 무엇 | 언제 | 창 |
|---|---|---|
| 종목 규칙 125종 (`tech_backtest.py`) | **매월 1일** + 매주 토 | `MAX_YEARS=10` · 격자를 **전월말**에서 끊는다(`asof_cut`) |
| 자산배분 64종 (`asset_backtest.py`) | 매일(평일) | `MAX_YEARS=10` · `cap_start()` |
| 시점정확 레그 (`pit_backtest.py`) | 로컬 | 10년 창에 맞춰 2021-07 시작 |
| 지표 (`strategy_metrics.py`) | **매월 1일** + 매주 토 | — |

그 구성은 **2026-08-14 사용자 지시**로 들어간 것이다 —
«성과는 전월말까지로 하고 월 1회 자동 업데이트 하는 식으로 구성해.»
전월말에서 끊으므로 **한 달 안에서는 몇 번을 돌려도 산출이 한 바이트도 안 바뀌고**,
실질 갱신은 달이 넘어간 뒤 첫 실행 한 번이다. 10년 창은 그때 **저절로 한 달 굴러간다.**

──────────────────────────────────────────────────────────────────────────
그래서 **여기서 채우는 것은 그 잡들이 안 건드리는 다섯뿐**이다.

  ① 펀드 카드          `fund_card.py`      → 새 달의 펀드 성적·국면
  ② 국면표             `regime_table.py`   → 새 달의 FF 팩터 칸
  ③ 단일 신호 정본 표    `single_table.py`
  ④ 분기 보고 깃발       `quarterly_report.py` (읽기 전용)
  ⑤ 🚨 **사전등록 전방 추적** `forward_track.py`

🚨 ⑤ 가 이 파일의 핵심이고, 규율이 걸리는 자리다.
   오늘 낸 사전등록 여섯(VALSLEEVE·GURUACC·RESIDMOM·RUNS·RUNS2·REVCOMP)의 산출물은
   `audit_unbuilt.py` 의 KNOWN 에 «자동 재굽기 금지 — 기록이다» 로 적혀 있다.
   그런데 «모든 전략을 월 1회 갱신» 과 충돌하는 것처럼 보인다. 충돌이 아니다 —
   **둘은 다른 것이다.**

     · **판정(등록)은 얼린다.** 결과문서가 인용한 수가 말없이 바뀌면 그 문서는 거짓이 된다.
     · **운용 추적은 굴린다.** 등록 이후 실제로 어떻게 갔는지는 매월 쌓는다.

   랩에 이미 같은 모양이 있다 — `strategy_forward.json`(틸트 계열 전방 주간 기록 ·
   append-only). **여기서는 월간판을 만든다.**

  python build/monthly_refresh.py            무엇을 할지만 보여준다
  python build/monthly_refresh.py --run      실제로 돌린다
"""
from __future__ import annotations
import datetime as dt
import io
import json
import os
import subprocess
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# 자동 잡이 이미 도는 것 — 여기서 **안 부른다**(두 번 굽지 않는다)
ALREADY = [
    ("tech_backtest.py", "종목 규칙 125종", "refresh-tech.yml · 매월 1일 + 매주 토"),
    ("asset_backtest.py", "자산배분 64종", "refresh-assets.yml · 매일(평일)"),
    ("strategy_metrics.py", "지표", "refresh-metrics.yml · 매월 1일 + 매주 토"),
    ("strategy_index.py", "통합 목록", "refresh-tech.yml 안"),
    ("strategy_report.py", "복제 리포트", "refresh-tech.yml 안"),
]

# 여기서 도는 것 — (스크립트, 설명, 인자)
STEPS = [
    ("fund_card.py", "펀드 카드(우량성장 30)", []),
    ("regime_table.py", "국면표 — 새 달의 FF 팩터 칸", []),
    ("single_table.py", "단일 신호 정본 표", []),
    ("forward_track.py", "🚨 사전등록 전방 추적(append-only)", ["--append"]),
    ("quarterly_report.py", "분기 보고 — 깃발만 읽는다", []),
]


def prev_month_end():
    t = dt.date.today().replace(day=1) - dt.timedelta(days=1)
    return t


def main(argv):
    run = "--run" in argv
    pm = prev_month_end()
    print("=" * 74)
    print("  월간 갱신 — 성과 기준일 **전월말 %s** · 10년 창이 한 달 굴러간다" % pm)
    print("=" * 74)

    print("\n■ 이미 자동으로 도는 것 — 여기서 다시 안 부른다")
    for f, what, when in ALREADY:
        print("   %-22s %-16s %s" % (f, what, when))
    print("""
   ⚠ 전월말에서 격자를 끊으므로 **한 달 안에서는 몇 번 돌려도 산출이 안 바뀐다.**
     실질 갱신은 달이 넘어간 뒤 첫 실행 한 번이고, 10년 창은 그때 저절로 굴러간다.
     🚨 이 클론에서는 tech_backtest.py 를 못 돌린다(_ratings_cache.json 부재) —
        돌리면 투자의견 3종이 조용히 무보유가 되어 게시 산출물을 덮는다.
        **월간 갱신은 러너(GitHub Actions)가 한다. 여기서 손으로 돌리지 않는다.**""")

    print("\n■ 여기서 도는 것 — 위 잡들이 안 건드리는 자리")
    for f, what, args in STEPS:
        p = os.path.join(ROOT, "build", f)
        ok = "있다" if os.path.exists(p) else "🚨 없다"
        print("   %-22s %-34s [%s]" % (f, what, ok))

    if not run:
        print("\n(안 돌렸다. 실제로 돌리려면 --run)")
        return 0

    fails = []
    for f, what, args in STEPS:
        p = os.path.join(ROOT, "build", f)
        if not os.path.exists(p):
            fails.append((f, "파일 없음")); continue
        print("\n" + "─" * 74)
        print("▶ %s — %s" % (f, what))
        r = subprocess.run([sys.executable, "-X", "utf8", "-W", "ignore", p] + args,
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        out = (r.stdout or "").rstrip().split("\n")
        for ln in out[-12:]:
            print("   " + ln)
        if r.returncode != 0:
            fails.append((f, (r.stderr or "").strip().split("\n")[-1][:120]))
            print("   🚨 실패 — %s" % fails[-1][1])

    print("\n" + "=" * 74)
    if fails:
        print("🚨 실패 %d건:" % len(fails))
        for f, why in fails:
            print("   %-22s %s" % (f, why))
    else:
        print("✅ 전부 돌았다.")
    print("""
다음에 할 것 — 손으로 본다:
  1. build/quarterly_report.py 의 «설계를 의심할 자리인가» 깃발
     → 켜졌으면 build/qg_2026.py 로 팩터 귀속을 본다(설계 탓인가 국면 탓인가).
  2. build/validate_site.py 가 통과하는가.
  3. 전방 추적에 새 달이 붙었는가(data/_forward_track.json).
     🚨 **사전등록 결과문서의 수는 고치지 않는다.** 그것은 판정이고, 전방 추적은 운용이다.""")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
