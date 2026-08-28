# -*- coding: utf-8 -*-
"""build/grppick_probe.py — 사전등록 §2-3·§4-4 를 잰다 → data/grppick_probe.json

규약: build/PREREG-2026-08-29-GRPPICK.md (b697d290).

  이 등록의 고유한 질문은 성적이 아니라 이것이다 —
    「산업별로 나눠 담기」가 **그 자체로** 값을 하는가.
  같은 복합 점수를 (A) 산업그룹 제약으로 담을 때와 (B) 제약 없이 담을 때를
  같은 격자·같은 바스켓 크기·같은 비용으로 나란히 돌려 그 차만 떼어 본다.

🚨 점수도 선택도 엔진 것을 **그대로 부른다.** 밖에서 xsec_pick_at 을 감싸 그 달의 sc 를
  가로채고, 같은 sc 에서 제약 없는 상위 N 을 따로 뽑아 둔다. 복합 점수를 여기서 다시
  만들면 두 벌이 된다.
🚨 대조판(B)은 엔진에 **등록하지 않는다** — 형제 둘을 같이 등록하면 incr5 이웃에 서로가
  나와 증분 검정이 상쇄된다(REVDRIFT-RESULT §7).
🚨 사이트 산출물을 덮지 않는다 — TB.OUT 을 로컬 캐시로 돌린다.
⚠ B 의 바스켓 크기는 그 달 A 의 보유 수에 맞춘다. 크기가 다르면 분산 차이가 성적으로 샌다.

    python build/grppick_probe.py
"""
from __future__ import annotations
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "grppick_probe.json")
RAW = os.path.join(DATA, "_grppick_raw.json")      # 밑줄 = 로컬 전용
sys.path.insert(0, HERE)

MIN_N = 8          # 사전등록 §1-2 — 새로 고른 값이 아니다
MIN_GROUPS = 15    # §4-4 — 이보다 적은 달이 5% 를 넘으면 «25그룹 분산» 이 사실이 아니다
COST = 0.0005

REC = []           # (i0, A 보유, B 보유, 그 달 문턱 통과 그룹 수)


def main():
    import tech_backtest as TB
    TB.OUT = RAW
    _orig = TB.xsec_pick_at

    def wrapped(S, i, X, sc, ind_raw, held=None):
        out = _orig(S, i, X, sc, ind_raw, held=held)
        if TB._BASE_SID(S["sid"]) == "x-grppick":
            meta = X["meta"]
            names = out[0] or []
            # 그 달 문턱 통과 그룹 수 — §4-4
            cnt = {}
            for _v, t in sc:
                g = (meta.get(t) or {}).get("grp") or ""
                if g:
                    cnt[g] = cnt.get(g, 0) + 1
            ng = sum(1 for g, c in cnt.items() if c >= MIN_N)
            # B — 같은 sc 에서 제약 없이 상위 N(= A 의 보유 수)
            free = [t for _v, t in sc[:len(names)]]
            REC.append((i, list(names), free, ng))
        return out

    TB.xsec_pick_at = wrapped
    print("감싸기 걸었다 — x-grppick 의 그 달 sc 에서 제약 없는 판을 같이 뽑는다")
    TB.run()

    dates, px = TB.load(full=True)[0], TB.load(full=True)[1]

    def leg(key):
        r, turn, prev = [], [], None
        for k in range(len(REC) - 1):
            i0, a, b, _ng = REC[k]
            i1 = REC[k + 1][0]
            names = a if key == "A" else b
            g = [px[t][i1] / px[t][i0] - 1 for t in names
                 if px.get(t) and i1 < len(px[t]) and px[t][i0] and px[t][i1]]
            if not g:
                continue
            cur = set(names)
            tv = 1.0 if prev is None else len(cur - prev) / max(1, len(cur))
            prev = cur
            turn.append(tv)
            r.append(sum(g) / len(g) - tv * COST)
        return r, turn

    def stat(xs, per=12.0):
        g = 1.0
        for x in xs:
            g *= (1 + x)
        cagr = (g ** (per / len(xs)) - 1) * 100
        m = sum(xs) / len(xs)
        vol = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs)) * math.sqrt(per) * 100
        gg, pk, w = 1.0, 1.0, 0.0
        for x in xs:
            gg *= (1 + x)
            pk = max(pk, gg)
            w = min(w, gg / pk - 1)
        return {"cagr": round(cagr, 2), "vol": round(vol, 2),
                "sharpe": round(cagr / vol, 3) if vol else None, "mdd": round(w * 100, 1)}

    res = {}
    for k in ("A", "B"):
        r, turn = leg(k)
        res[k] = stat(r)
        res[k]["turnover"] = round(sum(turn) / len(turn) * 12, 2)
        res[k]["n_months"] = len(r)
        res[k]["_r"] = r

    d = [a - b for a, b in zip(res["A"]["_r"], res["B"]["_r"])]
    md = sum(d) / len(d)
    sd = math.sqrt(sum((x - md) ** 2 for x in d) / (len(d) - 1))
    tt = md / sd * math.sqrt(len(d)) if sd else None

    ngs = [x[3] for x in REC]
    thin = sum(1 for n in ngs if n < MIN_GROUPS)
    doc = {
        "note": ("산업그룹 제약(A) vs 제약 없음(B) — 같은 복합 점수·같은 바스켓 크기·같은 비용. "
                 "규약 build/PREREG-2026-08-29-GRPPICK.md §2-3·§4-4."),
        "A_constrained": {k: v for k, v in res["A"].items() if k != "_r"},
        "B_free": {k: v for k, v in res["B"].items() if k != "_r"},
        "A_minus_B": {"ann_pp": round(res["A"]["cagr"] - res["B"]["cagr"], 2),
                      "d_sharpe": round((res["A"]["sharpe"] or 0) - (res["B"]["sharpe"] or 0), 3),
                      "monthly_t": round(tt, 2) if tt else None},
        "groups": {"mean": round(sum(ngs) / len(ngs), 1), "min": min(ngs), "max": max(ngs),
                   "months_below_%d" % MIN_GROUPS: thin,
                   "pct_below": round(thin / len(ngs) * 100, 1)},
        "n_months": len(REC),
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("\n%-14s %7s %7s %7s %7s %7s" % ("", "CAGR", "Vol", "샤프", "MDD", "회전"))
    for k, nm in (("A", "산업그룹 제약"), ("B", "제약 없음")):
        s = res[k]
        print("%-14s %7.2f %7.2f %7.3f %7.1f %7.2f" %
              (nm, s["cagr"], s["vol"], s["sharpe"], s["mdd"], s["turnover"]))
    ab = doc["A_minus_B"]
    print("\nA−B  연 %+.2f%%p · 샤프차 %+.3f · 월간차 t %s" % (ab["ann_pp"], ab["d_sharpe"], ab["monthly_t"]))
    g = doc["groups"]
    print("문턱 통과 그룹 평균 %.1f (%d~%d) · %d 미만인 달 %d (%.1f%%)"
          % (g["mean"], g["min"], g["max"], MIN_GROUPS, g["months_below_%d" % MIN_GROUPS], g["pct_below"]))
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
