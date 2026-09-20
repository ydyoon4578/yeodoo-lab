# -*- coding: utf-8 -*-
"""build/forward_track.py — 사전등록 뒤 **실제로 어떻게 갔나**를 매월 쌓는다(append-only).

🚨 왜 따로 있나 — «얼린 기록» 과 «월간 갱신» 은 충돌하는 것처럼 보이지만 아니다.

  · **판정(등록)은 얼린다.** 결과문서가 인용한 수가 말없이 바뀌면 그 문서가 거짓이 된다.
    그래서 `_valsleeve.json` 같은 산출물은 `audit_unbuilt.py` KNOWN 에
    «자동 재굽기 금지 — 기록이다» 로 적혀 있다.
  · **운용 추적은 굴린다.** 등록 이후 실제로 어떻게 갔는지는 매월 쌓아야 한다.
    안 쌓으면 «표본 밖에서 확인한다» 는 말이 영영 말로만 남는다.

  **이 파일은 뒤쪽이다.** 앞쪽(판정)은 건드리지 않는다.

무엇을 쌓나
   등록마다 «그 등록이 창을 끊은 달» 을 경계로 삼고, 그 **뒤에 실제로 생긴 달**을
   한 줄씩 붙인다. 10년 창은 `maxyears.cap` 으로 함께 굴린다.

     frozen  — 등록 당시의 수(결과문서가 인용한 것). **절대 안 바뀐다.**
     rolled  — 오늘 자료로 같은 창 길이(10년)를 다시 잰 것.
     forward — 등록 뒤 새로 생긴 달만으로 잰 것. **이것이 표본 밖이다.**

⚠ 지금은 forward 가 0개월이다 — 등록이 오늘이기 때문이다. 다음 달부터 쌓인다.
  **0개월을 «아직 증거 없음» 으로 정직하게 적는 것이 이 파일의 첫 일이다.**

  python build/forward_track.py            지금 상태만 본다
  python build/forward_track.py --append   새 달을 붙인다(월초에 monthly_refresh 가 부른다)
"""
from __future__ import annotations
import datetime as dt
import io
import json
import os
import sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_forward_track.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maxyears import MAX_YEARS, cap                              # noqa: E402

# (이름, 산출물, 계열 키, 등록 판정, 결과문서)
REG = [
    ("VALSLEEVE", "_valsleeve.json", "sleeve", "보류(조건 일곱 전부 통과)",
     "PREREG-2026-09-20-VALSLEEVE-RESULT.md"),
    ("GURUACC", "_guruacc_fund.json", "guru", "기각(F3)",
     "PREREG-2026-09-20-GURUACC-RESULT.md"),
    ("RESIDMOM", "_residmom_fund.json", "resid", "기각(아홉 중 여섯)",
     "PREREG-2026-09-20-RESIDMOM-RESULT.md"),
    ("RUNS", "_runs_fund.json", "runs", "기각(F3·F9)",
     "PREREG-2026-09-20-RUNS-RESULT.md"),
    ("RUNS2", "_runs2_fund.json", "runs2", "기각(넷 · 축 폐쇄)",
     "PREREG-2026-09-20-RUNS2-RESULT.md"),
    ("REVCOMP", "_revcomp.json", "comp", "—",
     "PREREG-2026-09-20-REVCOMP-RESULT.md"),
]


def y(e):
    return float(e.mean() * 1200) if len(e) else float("nan")


def tstat(e):
    if len(e) < 6:
        return float("nan")
    return float(e.mean() / (e.std(ddof=1) / np.sqrt(len(e))))


def main(argv):
    append = "--append" in argv
    prev = {}
    if os.path.exists(OUT):
        prev = json.load(io.open(OUT, encoding="utf-8"))
    rows, missing = [], []

    for name, fn, key, verdict, doc in REG:
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            missing.append((name, fn)); continue
        d = json.load(io.open(p, encoding="utf-8"))
        S = (d.get("series") or {})
        if key not in S:
            missing.append((name, "%s 안에 계열 %s 없음" % (fn, key))); continue
        E = pd.Series({pd.Period(k, freq="M"): v for k, v in S[key].items()},
                      dtype="float64").sort_index()
        # 등록이 끊은 달 = 그 산출물의 마지막 달. 그 뒤가 표본 밖이다.
        froze_at = str(E.index[-1])
        old = (prev.get("rows") or {}).get(name) or {}
        anchor = old.get("froze_at") or froze_at

        fwd = E[E.index > pd.Period(anchor, freq="M")]
        rolled = E.reindex(cap(E.index))
        rows.append({
            "name": name, "verdict": verdict, "doc": doc,
            "froze_at": anchor,
            "frozen": {"n": int(len(E)), "y_pp": y(E), "t": tstat(E),
                       "start": str(E.index[0]), "end": str(E.index[-1])},
            "rolled_10y": {"n": int(len(rolled)), "y_pp": y(rolled),
                           "t": tstat(rolled), "start": str(rolled.index[0]),
                           "end": str(rolled.index[-1])},
            "forward": {"n": int(len(fwd)), "y_pp": y(fwd) if len(fwd) else None,
                        "t": tstat(fwd) if len(fwd) >= 6 else None},
        })

    print("=" * 76)
    print("  사전등록 전방 추적 — 등록 뒤 실제로 어떻게 갔나 (%s)" % dt.date.today())
    print("=" * 76)
    print("  %-11s %-22s %11s %11s %10s" %
          ("등록", "판정", "얼린 값", "10년 굴림", "**표본 밖**"))
    for r in rows:
        f = r["forward"]
        fw = ("%+.2f%%p (%d개월)" % (f["y_pp"], f["n"])) if f["n"] else "**0개월**"
        print("  %-11s %-22s %+10.2f%%p %+10.2f%%p %10s"
              % (r["name"], r["verdict"][:22], r["frozen"]["y_pp"],
                 r["rolled_10y"]["y_pp"], fw))
        print("  %-11s   얼린 창 %s~%s(%d) · 기준달 %s"
              % ("", r["frozen"]["start"], r["frozen"]["end"],
                 r["frozen"]["n"], r["froze_at"]))
    for n, why in missing:
        print("  %-11s (아직 없다 — %s)" % (n, why))

    nofwd = [r["name"] for r in rows if not r["forward"]["n"]]
    if nofwd:
        print("""
🚨 표본 밖이 **0개월**인 등록 %d건: %s
   등록이 오늘이라 당연하다. **«아직 증거 없음» 을 그대로 적는 것이 이 표의 첫 일이다.**
   다음 달 첫 실행부터 한 줄씩 쌓인다. 표본 밖이 12개월을 넘기 전에는
   **어떤 등록도 «표본 밖에서 확인됐다» 고 말하지 않는다.**""" % (len(nofwd), " · ".join(nofwd)))

    print("""
⚠ 세 칸을 헷갈리지 않는다:
   · 얼린 값  — 결과문서가 인용한 수. **절대 안 바뀐다.**
   · 10년 굴림 — 오늘 자료로 같은 창 길이를 다시 잰 것. 참고이지 판정이 아니다.
   · 표본 밖  — 등록 뒤 새로 생긴 달만. **이것만이 진짜 확인이다.**""")

    if append:
        io.open(OUT, "w", encoding="utf-8").write(json.dumps({
            "note": ("사전등록 전방 추적. 판정은 얼리고 운용 추적만 굴린다. "
                     "forward 가 «표본 밖» 이고 그것만이 진짜 확인이다."),
            "generated": dt.datetime.now().isoformat(timespec="seconds"),
            "max_years": MAX_YEARS,
            "rows": {r["name"]: r for r in rows},
        }, ensure_ascii=False, indent=1, default=float) + "\n")
        print("\n→ %s" % OUT)
    else:
        print("\n(안 썼다. 붙이려면 --append)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
