# -*- coding: utf-8 -*-
"""build/sgc_import.py — S&P 500 성장 전환 전략 저장소의 월말 산출물을 랩으로 옮긴다.

전략 저장소(ydyoon4578/SP500-Growth-Conversion-Strategy)는 월말에 판단 문서와
실제 보유(체결 문턱을 거친 장부)를 snapshot/ 에 낸다. 이 스크립트는 그중 일간 추적에
필요한 것만 골라 data/sgc/ 에 얇게 옮긴다. 매일 도는 것은 build/sgc_track.py 이고,
이 스크립트는 **월 1회(새 판단이 나왔을 때)** 사람이 돌린다.

  python build/sgc_import.py --src ../SP500-Growth-Conversion-Strategy

  data/sgc/inputs.json         보유 · 묶음 · 판단 상태 · 백테스트 요약
  data/sgc/sp500tr_daily.json  S&P 500 TR 일간(신호 · 비교 기준의 뿌리)
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "sgc")

# 전략 저장소 README 1절(모의 운용 2016-10 ~ 2026-09)의 숫자. 판단마다 바뀌지 않는 기록이다.
BACKTEST = {
    "window": "2016-10 ~ 2026-09 (120개월)",
    "cost": "편도 10bp",
    "rows": [
        ["연 수익률 (전략 / S&P 500 TR)", "16.67% / 15.33%", "24.50% / 22.89%"],
        ["연 초과수익", "+1.34%p", "+1.61%p"],
        ["추적오차", "0.79%", "0.71%"],
        ["정보비율", "1.55", "1.91"],
        ["월 승률", "68.33%", "72.22%"],
        ["최대 낙폭 (전략 / S&P 500 TR)", "−24.11% / −23.87%", "−7.89% / −7.50%"],
    ],
    "cols": ["전체 2016-10 ~ 2026-09", "최근 3년 2023-10 ~ 2026-09"],
}
BOOK_NM = {"E": "기대성장 상위 40", "V": "가치주 40"}


def latest(pattern: str) -> str:
    fs = sorted(glob.glob(pattern))
    if not fs:
        sys.exit(f"없음: {pattern}")
    return fs[-1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="전략 저장소 경로")
    a = ap.parse_args()
    snap = os.path.join(a.src, "snapshot")
    hp = latest(os.path.join(snap, "analysis", "actual_holdings_*.json"))
    dp = latest(os.path.join(snap, "decisions", "RD_월말판단_*.json"))
    hold = json.load(open(hp, encoding="utf-8"))
    dec = json.load(open(dp, encoding="utf-8"))

    rows = {r["t"]: r for r in dec["sleeve"]["rows"]}
    names = {}
    for t in set(hold["hold_nav"]) | set(hold.get("target_nav", {})):
        r = rows.get(t, {})
        books = [b for b in ("E", "V") if r.get("w_" + b)]
        names[t] = {"name": r.get("name") or t, "sector": r.get("sector") or "",
                    "books": books}
    st = dec["states"]
    inputs = {
        "note": "build/sgc_import.py 가 전략 저장소 snapshot/ 에서 옮긴 월말 입력. 손으로 고치지 말 것.",
        "src_repo": "https://github.com/ydyoon4578/SP500-Growth-Conversion-Strategy",
        "src_files": [os.path.relpath(hp, a.src).replace("\\", "/"),
                      os.path.relpath(dp, a.src).replace("\\", "/")],
        "decision_date": dec["dates"]["dec_date"],
        "exec_date": hold["exec_date"],
        "shares": dec["shares"]["decision"],
        "shares_prev": dec["shares"]["previous"],
        "states": {"decision": st["decision"], "previous": st["previous"]},
        "next_decision_month": dec.get("ops", {}).get("reconstitution", {}).get("next_decision_month"),
        "hold_nav": hold["hold_nav"],
        "target_nav": hold.get("target_nav", {}),
        "n_target": dec["sleeve"]["n_names"],
        "names": names,
        "book_nm": BOOK_NM,
        "backtest": BACKTEST,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, ensure_ascii=False, indent=1)
    tr = json.load(open(os.path.join(snap, "bench", "sp500tr_daily.json"), encoding="utf-8"))
    keep = [i for i, d in enumerate(tr["dates"]) if d >= "2015-01-01"]
    out_tr = {"source": tr.get("source"), "ticker": tr.get("ticker", "^SP500TR"),
              "dates": [tr["dates"][i] for i in keep],
              "px": [round(tr["px"][i], 4) for i in keep]}
    with open(os.path.join(OUT, "sp500tr_daily.json"), "w", encoding="utf-8") as f:
        json.dump(out_tr, f, separators=(",", ":"))
    print(f"판단 {inputs['decision_date']} · 체결 {inputs['exec_date']} · 보유 {len(inputs['hold_nav'])}종 · TR {len(keep)}일")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
