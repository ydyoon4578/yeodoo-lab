# -*- coding: utf-8 -*-
"""갱신 주기 라벨(data/schedule.json) 생성 — 워크플로 cron이 단일 출처.

【왜 필요한가】
sources.html '한눈에 보기'의 갱신 시각을 손으로 적어 왔는데, cron을 바꿀 때 라벨을 같이 안 고쳐
**전면적으로 어긋났다**(2026-07-25 실측: SEC 공시 라벨 10:15 ↔ 실제 08:45, 13F 12:15 ↔ 09:25,
종목 08:35 ↔ 08:15, 포트폴리오 '매월 1일' ↔ 실제 2일, 이미 없어진 백업 크론 '08:35 + 09:10' 표기).
사이트가 사용자에게 갱신 시각을 조용히 틀리게 말하고 있었다 — 이 랩이 가장 경계하는 실패 유형이다.

그래서 라벨을 **cron에서 파생**시킨다. 워크플로를 고치면 라벨이 자동으로 따라오고,
매핑이 빠진 워크플로가 생기면 CI가 실패한다(아래 ROWS/NO_ROW 이중 선언).

  python build/schedule_index.py          # data/schedule.json 굽기
  python build/schedule_index.py --check  # 커밋본과 일치하는지만 확인(CI용)
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
WF = os.path.join(ROOT, ".github", "workflows")
OUT = os.path.join(ROOT, "data", "schedule.json")

# 워크플로 → sources.html 표의 행 id. 표에 안 싣는 잡은 NO_ROW에 사유와 함께 적는다.
#   둘 중 어디에도 없는 워크플로가 생기면 CI가 잡는다(라벨 없는 잡이 조용히 늘어나는 것 방지).
ROWS = {
    "refresh-stocks.yml":    "src-stk",
    "refresh-regime.yml":    "src-rg",
    "refresh-sentiment.yml": "src-snt",
    "refresh-facts.yml":     "src-fx",
    "refresh-13f.yml":       "src-guru",
    "refresh-calendar.yml":  "src-cal",
    "refresh-insider.yml":   "src-ins",
    "refresh-filings.yml":   "src-fil",
    "refresh-holdings.yml":  "src-hold",
    "refresh-cot.yml":       "src-cot",
}
# 자동 잡이 없는 행 — 라벨을 여기서 같이 관리해 표 전체가 한 곳에서 나오게 한다.
#   src-rot: 로컬 스케줄러 잡이 있으나 헤드리스 인증 실패로 자주 죽어, 사실상 사람이 돌린다
#            (2026-07-25 '갱신 주기 주장을 사실로 고침' 정정을 유지).
STATIC = {
    "src-rot": "수시 (자동 잡 아님)",
    "src-bt":  "수시(정적)",
}
NO_ROW = {
    "refresh-earnings.yml":  "실적 원자료 — 종목 시그널 행이 대표",
    "refresh-estimates.yml": "컨센서스 원자료 — 종목 시그널 행이 대표",
    "refresh-members.yml":   "유니버스 스냅샷 — 종목 시그널 행이 대표",
    "refresh-metrics.yml":   "전략 지표 재계산 — 백테스트 행이 대표(수시·정적)",
    # 13F 이력은 화면에 '13F 보유' 행 하나로 나오고 그 대표는 guru.json(refresh-13f.yml)이다.
    #   이력(guru_history.json)은 복제 백테스트 입력이라 표에 따로 실을 축이 아니다.
    "refresh-13f-history.yml": "13F 보유 **이력** — 화면 대표는 refresh-13f.yml(guru.json)이다",
    "refresh-tech.yml":      "종목 전략 재계산 — 백테스트 행이 대표",
    "refresh-assets.yml":    "자산배분 전략 재계산 — 백테스트 행이 대표",
    "validate.yml":          "검증 전용(데이터 산출 없음)",
    # ── cron 이 없는 잡. 라벨을 만들 수 없어 표에는 못 실리지만 사유는 남긴다 ──
    "pit-facts.yml":         "편출 종목 SEC 재무 — 수시(workflow_dispatch). 명단이 바뀔 때만 돈다",
    "refresh-ml.yml":        "ML 연구 산출물 — refresh-assets 직후 연쇄(workflow_run)라 "
                             "고유 주기가 없다. 백테스트 행이 대표",
}

DOW = "일월화수목금토"


def _expand(field: str):
    """cron 요일/일자 필드 → 정수 리스트. '*'는 None(매일)."""
    if field == "*":
        return None
    out = []
    for part in field.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def kst_label(cron: str) -> str:
    """UTC cron → 한국어 KST 라벨. +9h이라 자정을 넘으면 요일·일자가 하루 밀린다."""
    mi, hh, dom, mon, dow = cron.split()
    h = int(hh) + 9
    shift, h = divmod(h, 24)          # shift=1이면 KST 기준 다음 날
    t = f"{h:02d}:{int(mi):02d}"

    d = _expand(dom)
    if d:                              # 월간
        days = [(x + shift - 1) % 31 + 1 for x in d]
        return f"매월 {days[0]}일 {t} KST"

    w = _expand(dow)
    if w is None:                      # 매일
        return f"매일 {t} KST"
    w = sorted({(x + shift) % 7 for x in w})
    if len(w) == 7:
        return f"매일 {t} KST"
    # 연속 구간이면 '월~토', 아니면 '월·수·금'
    if len(w) > 1 and w == list(range(w[0], w[0] + len(w))):
        span = f"{DOW[w[0]]}~{DOW[w[-1]]}"
    else:
        span = "·".join(DOW[x] for x in w)
    return (f"매일({span}) {t} KST" if len(w) > 1 else f"매주 {span} {t} KST")


def build() -> dict:
    rows, jobs, unmapped = dict(STATIC), {}, []
    for p in sorted(glob.glob(os.path.join(WF, "*.yml"))):
        fn = os.path.basename(p)
        src = io.open(p, encoding="utf-8").read()
        crons = re.findall(r"-\s*cron:\s*'([^']+)'", src)
        # ⚠ 등록 여부를 cron 유무보다 **먼저** 본다. 전에는 cron 이 없으면 여기서 continue 로
        #   빠져 ROWS/NO_ROW 등록을 아무도 안 물었다 — 이 게이트가 막으려던 '라벨 없는 잡이
        #   조용히 느는 것'이 정확히 그 경로로 일어난다. 실제로 pit-facts.yml(workflow_dispatch)
        #   이 그렇게 미등록 상태로 들어와 있었고, 2026-08-03 refresh-ml.yml(workflow_run)이
        #   두 번째였다. **둘 다 데이터를 커밋한다** — 표에 실을지는 선택이지만, 그 선택을
        #   한 번은 하게 만드는 것이 이 게이트의 일이다.
        if fn not in ROWS and fn not in NO_ROW:
            unmapped.append(fn)
        if not crons:
            continue
        labels = [kst_label(c) for c in crons]
        jobs[fn] = {"cron": crons, "label": labels}
        if fn in ROWS:
            rows[ROWS[fn]] = " + ".join(labels)
    if unmapped:
        raise SystemExit(
            f"❌ 워크플로 {unmapped} 가 build/schedule_index.py의 ROWS/NO_ROW 어디에도 없습니다.\n"
            "   표에 실을 행이면 ROWS에, 안 실을 잡이면 NO_ROW에 사유와 함께 등록하세요\n"
            "   (라벨 없는 잡이 조용히 늘어나는 것을 막는 게이트입니다).")
    return {"note": "갱신 주기 라벨의 단일 출처 — .github/workflows/*.yml의 cron에서 파생. "
                    "손으로 고치지 말 것(python build/schedule_index.py로 재생성).",
            "rows": rows, "jobs": jobs}


if __name__ == "__main__":
    doc = build()
    if "--check" in sys.argv:
        cur = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else None
        ok = cur == doc
        print("일치" if ok else "불일치 — python build/schedule_index.py 로 다시 구울 것")
        raise SystemExit(0 if ok else 1)
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for rid, lab in doc["rows"].items():
        print(f"  {rid:10} {lab}")
    print(f"→ {OUT} · 행 {len(doc['rows'])} · 잡 {len(doc['jobs'])}")
