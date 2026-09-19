# -*- coding: utf-8 -*-
"""build/f6_screen.py — 자료 커버리지가 만드는 선택 편향을 **등록 전에** 잰다.

🚨 왜 만드나. ORGCAP(A21)이 F1~F5 가 아니라 **F5(자료 유무 수익차)** 때문에 죽었다 —
   판관비를 보고하는 409종이 안 하는 109종보다 연 +4.89%p 더 벌었고, 그래서 그 태그로
   만든 신호는 «조직자본» 이 아니라 «판관비를 보고하는 회사» 를 사는 것이었다.
   OPLEV(E58)에서도 같은 관문이 +3.96%p 로 걸렸다.

   **그 관문을 카드마다 사전등록 뒤에 발견하는 것은 낭비다.** 여기서 전수로 먼저 재고,
   크게 걸리는 조합은 **등록하지 않는다.**

읽는 법 — 「차」는 그 자료가 되는 회사와 안 되는 회사의 연 수익 차이다.
  |차| > 3%p 면 그 태그로 만든 신호는 자료 유무와 구분되지 않을 위험이 크다.
  ⚠ 커버리지와 단조가 아니다(실측: 98.8%→2.50 · 80.2%→4.89 · 56.6%→3.96).
    **누가 빠지는가**가 숫자보다 중요하므로 빠지는 쪽의 섹터 분포를 같이 낸다.

  python build/f6_screen.py
"""
from __future__ import annotations
import glob, io, json, os, sys, collections

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_f6_screen.json")
GATE = 3.0

# 카드가 요구하는 태그 조합 — (이름, [필요한 키], 여는 카드)
COMBOS = [
    ("tax", ["tax"], "E56 세금비용 서프라이즈 (쟀다 · 통과)"),
    ("sga", ["sga"], "A21 조직자본 (쟀다 · 걸림)"),
    ("cogs+sga", ["cogs", "sga"], "E58 영업레버리지 (쟀다 · 걸림) · E36 비용규율"),
    ("rnd", ["rnd"], "E40 R&D 집약도 · B3 혁신효율"),
    ("dep+sga", ["dep", "sga"], "E58 Chen 척도"),
    ("sti", ["sti"], "E57 현금보유 (정의 교정)"),
    ("cash+sti", ["cash", "sti"], "E57 원문 분자(현금+단기투자)"),
    ("opex", ["opex"], "E58 대체"),
    ("inv+ar", ["inv", "ar"], "E7 발생액"),
    ("dtl+pfd", ["dtl", "pfd"], "A23 · E60 장부자본"),
    ("intexp", ["intexp"], "E60 영업수익성(OP) 정의"),
    ("rev+opinc", ["rev", "opinc"], "(대조군) 기존 22태그"),
]


def main():
    have = collections.defaultdict(set)
    for d in (os.path.join(DATA, "fx"), os.path.join(DATA, "fxe")):
        for p in glob.glob(os.path.join(d, "*.json")):
            j = json.load(io.open(p, encoding="utf-8"))
            for k, v in (j.get("tags") or {}).items():
                if v and (v.get("a") or v.get("q") or v.get("i")):
                    have[k].add(j["t"])

    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    px = {}
    for s in st["stocks"]:
        p = os.path.join(DATA, "sd", "%s.json" % s["t"])
        if os.path.exists(p):
            v = json.load(io.open(p, encoding="utf-8")).get("pxd")
            if isinstance(v, list) and len(v) == len(dates):
                px[s["t"]] = v
    P = pd.DataFrame(px, index=pd.to_datetime(dates))
    R = P.pct_change()
    uni = list(P.columns)
    mem = json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
    sect = {t: (v.get("sector") or "?") for t, v in mem.items() if isinstance(v, dict)}
    print("유니버스 %d종 · %s ~ %s\n" % (len(uni), dates[0], dates[-1]))

    print("   %-11s %7s %8s %8s %9s  %s" % ("조합", "커버", "있는쪽", "없는쪽", "차", "판정"))
    rows = {}
    for nm, keys, opens in COMBOS:
        hv = [t for t in uni if all(t in have.get(k, ()) for k in keys)]
        nv = [t for t in uni if t not in hv]
        if len(hv) < 20 or len(nv) < 5:
            print("   %-11s %6.1f%% %27s  표본 부족" % (nm, len(hv) / len(uni) * 100, ""))
            rows[nm] = {"cover": len(hv) / len(uni) * 100, "note": "표본 부족"}
            continue
        a = R[hv].mean(axis=1).mean() * 25200
        b = R[nv].mean(axis=1).mean() * 25200
        gap = a - b
        # 🚨 섹터를 맞추고 다시 — 빠지는 쪽이 금융·유틸리티에 몰려 있으면 이 «차» 는
        #   자료 유무가 아니라 **섹터** 를 재게 된다. 섹터마다 따로 재서 평균한다.
        gs, wts = [], []
        for s in {sect.get(t, "?") for t in uni}:
            h2 = [t for t in hv if sect.get(t, "?") == s]
            n2 = [t for t in nv if sect.get(t, "?") == s]
            if len(h2) >= 5 and len(n2) >= 5:
                gs.append(R[h2].mean(axis=1).mean() * 25200 - R[n2].mean(axis=1).mean() * 25200)
                wts.append(len(h2) + len(n2))
        gap_sn = float(np.average(gs, weights=wts)) if gs else float("nan")
        mark = "❌ 위험" if abs(gap) > GATE else ("⚠ 경계" if abs(gap) > GATE * 0.6 else "✅")
        mark_sn = ("❌" if abs(gap_sn) > GATE else ("⚠" if abs(gap_sn) > GATE * 0.6 else "✅")) \
            if gap_sn == gap_sn else "—"
        miss = collections.Counter(sect.get(t, "?") for t in nv).most_common(3)
        rows[nm] = {"cover": len(hv) / len(uni) * 100, "have": a, "none": b, "gap": gap,
                    "gap_sector_neutral": gap_sn, "n_sectors_compared": len(gs),
                    "n_have": len(hv), "n_none": len(nv), "opens": opens,
                    "missing_sectors": miss}
        print("   %-11s %6.1f%% %+7.2f%% %+7.2f%% %+8.2f%%p  %-7s 섹터맞춤 %+6.2f%%p %s(섹터 %d)"
              % (nm, rows[nm]["cover"], a, b, gap, mark, gap_sn, mark_sn, len(gs)))
        print("       빠지는 쪽 %d종 — %s" % (len(nv), " · ".join("%s %d" % x for x in miss)))
        print("       여는 카드: %s" % opens)

    print("\n■ 읽는 법")
    print("   ❌ 위험(|차| > %.0f%%p) — 그 태그로 만든 신호는 «자료 유무» 와 구분 안 될 수 있다." % GATE)
    print("      등록하기 전에 대안을 찾거나, 그 편향을 제거하는 설계를 먼저 세운다.")
    print("   ⚠ 경계 — 등록은 하되 F6 을 반드시 판정 조건에 넣는다.")
    print("   실측 눈금: tax 98.8%→+2.50 통과 · sga 80.2%→+4.89 걸림 · cogs+sga 56.6%→+3.96 걸림")
    print("   → 커버리지와 단조가 아니다. 빠지는 쪽의 섹터가 어디인지를 같이 볼 것.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"gate_pp": GATE, "n_universe": len(uni), "rows": rows,
         "note": "자료 커버리지가 만드는 선택 편향. 사전등록 전에 본다."},
        ensure_ascii=False, indent=1, default=float) + "\n")
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
