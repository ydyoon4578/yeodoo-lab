# -*- coding: utf-8 -*-
"""build/riskonoff.py — 종합 Risk-On/Off 점수 → data/_riskonoff.json

출처. 사용자 제공 「시장 국면 모니터」(KBAM globalpassive · 2026-07-09) ① 「신호군 점수」.
신호군·가중·밴드는 그 문서 값 그대로 쓴다 — 내가 고르면 그것부터가 자유도다.
  추세·모멘텀 18 · 변동성 안정도 18 · 시장 폭 18 · 매크로·신용 18 · 섹터 리더십 18 · 심리 10
  밴드 >=68 Risk-On · 60~67 준Risk-On · 50~59 중립 · 40~49 준Risk-Off · <40 Risk-Off

🚨 **심리 10% 는 자료가 통째로 없다**(CNN F&G · 풋콜 · SKEW · AAII · NAAIM).
   지어 채우지 않는다 — 나머지 다섯의 가중을 **90 으로 재정규화**하고 그 사실을 싣는다.
   ⚠ 그래서 이 점수는 그 문서의 점수와 **같은 수가 아니다.** 밴드는 같이 쓰되
     두 수를 나란히 놓고 «맞다/틀리다» 를 말하면 안 된다.
⚠ 변동성 안정도도 셋 중 하나(VIX)만 있다. 매크로는 다섯 중 넷이다.

🚨 **점수는 판정이 아니다.** 그 문서 자신이 국면표 아래에 적어 뒀다 —
   「최근(2021~) 변별력 크게 약화·OOS 재현성 낮음 → 예측 아닌 역사적 맥락 참고용」.
   그래서 여기서도 **밴드가 다음 달을 가르나** 를 같이 재고, 그 수를 산출물에 싣는다.

⚠ 각 신호군은 0~100 으로 만든다. 방법은 **그 지표의 과거 분포에서의 백분위** 다
  (문서가 산식을 안 밝혔으므로 내가 고른 것이고, 그 사실을 적는다).
  백분위는 **그날까지의 자료만** 쓴다(확장창) — 전 구간 분포를 쓰면 선견이다.

  python build/riskonoff.py
"""
from __future__ import annotations
import io, json, os, statistics as st, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_riskonoff.json")
# 🚨 일별 전량 덤프. _riskonoff.json 의 hist 는 rows[::5] 라 5일마다 뽑은 축약본이고,
#   추세축(d5)·사후창(21일)을 재려면 빠진 4/5 가 필요하다. 그래서 따로 낸다.
#   ⚠ 이 파일은 _riskonoff.json 을 **대체하지 않는다** — 화면이 읽는 건 그쪽이다.
OUT_DAILY = os.path.join(DATA, "_riskonoff_daily.json")
sys.path.insert(0, os.path.join(ROOT, "build"))

W = {"trend": 18, "vol": 18, "breadth": 18, "macro": 18, "sector": 18, "senti": 10}
BANDS = [(68, "Risk-On"), (60, "준Risk-On"), (50, "중립"), (40, "준Risk-Off"), (0, "Risk-Off")]
CYC = ["XLY", "XLK", "XLI", "XLF", "XLE", "XLB", "XLC"]
DEF = ["XLP", "XLU", "XLV", "XLRE"]
WARM = 504          # 백분위를 내기 전에 쌓을 최소 일수(2년)
FWD = 21


def J(n):
    return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))


def band(s):
    for lo, ko in BANDS:
        if s >= lo:
            return ko
    return "Risk-Off"


def expanding_pct(v, warm=WARM, invert=False):
    """그날까지의 분포에서의 백분위(0~100). **선견 금지** — 미래를 안 본다."""
    out, hist = [None] * len(v), []
    for i, x in enumerate(v):
        if x is None:
            out[i] = out[i - 1] if i else None
            continue
        if len(hist) >= warm:
            p = sum(1 for h in hist if h < x) / len(hist) * 100
            out[i] = (100 - p) if invert else p
        hist.append(x)
    return out


def main() -> int:
    import tech_backtest as TB                                   # noqa: E402
    B = J("bench_px.json")
    d, PX = B["dates"], B["series"]["spx"]["px"]
    n = len(d)
    A = J("assets.json")
    ad, apx, mac = A["dates"], A["px"], (A.get("macro") or {})
    ai = {x: k for k, x in enumerate(ad)}

    def asset(t, i):
        k = ai.get(d[i])
        if k is None:
            return None
        s = apx.get(t) or []
        return s[k] if k < len(s) else None

    def mv(code, i, back=0):
        s = mac.get(code) or {}
        for t in range(i - back, max(0, i - back - 10), -1):
            if t < 0:
                return None
            v = s.get(d[t])
            if v is not None:
                return v
        return None

    # ── ① 추세·모멘텀 · ③ 시장 폭 — 518종 패널이 필요하다 ────────────────
    print("518종 패널 적재 중…")
    sd, spx_, svl, shi, slo, smeta, _rf = TB.load(full=True)
    tk = sorted(spx_)
    si = {x: k for k, x in enumerate(sd)}

    def breadth_at(i):
        """그날의 %>MA200 · %>MA50 · 20일 상승비율 · 52주 신고-신저."""
        k = si.get(d[i])
        if k is None or k < 252:
            return None
        a200 = a50 = up20 = hi52 = lo52 = tot = 0
        for t in tk:
            p = spx_[t]
            c = p[k]
            if c is None:
                continue
            w200 = [x for x in p[k - 199:k + 1] if x is not None]
            w50 = [x for x in p[k - 49:k + 1] if x is not None]
            if len(w200) < 100 or len(w50) < 25:
                continue
            tot += 1
            if c > sum(w200) / len(w200):
                a200 += 1
            if c > sum(w50) / len(w50):
                a50 += 1
            p20 = p[k - 20]
            if p20:
                up20 += 1 if c > p20 else 0
            w252 = [x for x in p[k - 251:k + 1] if x is not None]
            if w252:
                if c >= max(w252):
                    hi52 += 1
                if c <= min(w252):
                    lo52 += 1
        if tot < 100:
            return None
        return {"a200": a200 / tot * 100, "a50": a50 / tot * 100,
                "up20": up20 / tot * 100, "nhnl": (hi52 - lo52) / tot * 100, "n": tot}

    print("시장 폭 계산 중(주 1회 격자)…")
    BR = {}
    step = 5
    for i in range(252, n, step):
        b = breadth_at(i)
        if b:
            BR[i] = b
    # 주 1회 격자를 앞으로 채운다(그날까지의 최신값 — 선견 아님)
    last, BRD = None, [None] * n
    for i in range(n):
        if i in BR:
            last = BR[i]
        BRD[i] = last

    # ── 원시 지표 계열 ──────────────────────────────────────────────────
    ma50 = [None] * n
    ma200 = [None] * n
    for i in range(n):
        w = [x for x in PX[max(0, i - 49):i + 1] if x is not None]
        ma50[i] = sum(w) / len(w) if len(w) >= 25 else None
        w = [x for x in PX[max(0, i - 199):i + 1] if x is not None]
        ma200[i] = sum(w) / len(w) if len(w) >= 100 else None

    dist50 = [None if (PX[i] is None or not ma50[i]) else (PX[i] / ma50[i] - 1) * 100
              for i in range(n)]
    dist200 = [None if (PX[i] is None or not ma200[i]) else (PX[i] / ma200[i] - 1) * 100
               for i in range(n)]
    vix = [mv("VIXCLS", i) for i in range(n)]
    baa = [mv("BAA10Y", i) for i in range(n)]
    t102 = [mv("T10Y2Y", i) for i in range(n)]
    d10y = [None if (mv("DGS10", i) is None or mv("DGS10", i, 63) is None)
            else mv("DGS10", i) - mv("DGS10", i, 63) for i in range(n)]
    dxy = [None if (mv("DTWEXBGS", i) is None or not mv("DTWEXBGS", i, 63))
           else (mv("DTWEXBGS", i) / mv("DTWEXBGS", i, 63) - 1) * 100 for i in range(n)]

    def sector_spread(i, back):
        cy, df = [], []
        for t in CYC + DEF:
            a, b = asset(t, i), asset(t, i - back)
            if a is None or b is None:
                continue
            (cy if t in CYC else df).append((a / b - 1) * 100)
        if len(cy) < 4 or len(df) < 2:
            return None, None
        part = sum(1 for x in cy + df if x > 0) / len(cy + df) * 100
        return st.mean(cy) - st.mean(df), part

    sp1m = [sector_spread(i, 21)[0] for i in range(n)]
    sp3m = [sector_spread(i, 63)[0] for i in range(n)]
    part3 = [sector_spread(i, 63)[1] for i in range(n)]

    # ── 신호군 점수 = 구성 지표 백분위의 평균 ───────────────────────────
    P = {
        "trend": [expanding_pct(dist50), expanding_pct(dist200),
                  expanding_pct([b["a200"] if b else None for b in BRD]),
                  expanding_pct([b["a50"] if b else None for b in BRD])],
        "vol": [expanding_pct(vix, invert=True)],
        "breadth": [expanding_pct([b["nhnl"] if b else None for b in BRD]),
                    expanding_pct([b["up20"] if b else None for b in BRD])],
        "macro": [expanding_pct(baa, invert=True), expanding_pct(t102),
                  expanding_pct(d10y, invert=True), expanding_pct(dxy, invert=True)],
        "sector": [expanding_pct(sp1m), expanding_pct(sp3m), expanding_pct(part3)],
    }

    rows = []
    wsum = sum(W[k] for k in P)          # 심리 10 을 뺀 90
    for i in range(n):
        g, ok = {}, True
        for k, arrs in P.items():
            v = [a[i] for a in arrs if a[i] is not None]
            g[k] = st.mean(v) if v else None
            if g[k] is None:
                ok = False
        if not ok:
            continue
        s = sum(g[k] * W[k] for k in P) / wsum
        rows.append({"d": d[i], "score": round(s, 1), "band": band(s),
                     "g": {k: round(v, 1) for k, v in g.items()},
                     "spx": PX[i]})

    # ── 🚨 밴드가 다음 달을 가르나 ──────────────────────────────────────
    ix = {r["d"]: k for k, r in enumerate(rows)}
    di = {x: k for k, x in enumerate(d)}
    fwd = {}
    for r in rows:
        i = di[r["d"]]
        if i + FWD < n and PX[i] and PX[i + FWD]:
            fwd.setdefault(r["band"], []).append((PX[i + FWD] / PX[i] - 1) * 100)
    allf = [x for v in fwd.values() for x in v]
    bt = {"base": {"n": len(allf), "mean": st.mean(allf),
                   "win": sum(1 for x in allf if x > 0) / len(allf) * 100}}
    for b, v in fwd.items():
        bt[b] = {"n": len(v), "mean": st.mean(v),
                 "win": sum(1 for x in v if x > 0) / len(v) * 100,
                 "lift": st.mean(v) - bt["base"]["mean"]}

    cur = rows[-1]
    doc = {"note": "종합 Risk-On/Off — 설계 출처는 사용자 제공 KBAM 시장 국면 모니터 ①. "
                   "신호군·가중·밴드는 그 문서 값. 산식(백분위)은 문서가 안 밝혀 내가 골랐다.",
           "as_of": cur["d"], "score": cur["score"], "band": cur["band"],
           "groups": cur["g"], "weights": W,
           "weight_note": "심리 10%% 는 자료가 없어 뺐다(F&G·풋콜·SKEW·AAII·NAAIM). "
                          "나머지 다섯을 %d 으로 재정규화했다 — 그 문서의 점수와 같은 수가 아니다."
                          % wsum,
           "missing": ["심리 전체", "VIX 기간구조", "VVIX", "MOVE"],
           "backtest": bt, "n_days": len(rows),
           "hist": [{"d": r["d"], "score": r["score"], "band": r["band"]}
                    for r in rows[::5]]}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    # 일별 전량 — 추세축(d5)·사후창을 재는 쪽이 읽는다. indent 없이 줄여 쓴다.
    io.open(OUT_DAILY, "w", encoding="utf-8").write(json.dumps(
        {"note": "riskonoff.py 일별 전량. _riskonoff.json 의 hist(rows[::5]) 축약 이전 값이다. "
                 "화면은 이 파일을 안 읽는다 — 검정기 전용.",
         "as_of": cur["d"], "n": len(rows), "fwd_days": FWD,
         "rows": [{"d": r["d"], "score": r["score"], "band": r["band"], "spx": r["spx"]}
                  for r in rows]}, ensure_ascii=False) + "\n")

    print("\n기준 %s · 종합 **%.1f** → %s" % (cur["d"], cur["score"], cur["band"]))
    print("  %-14s %s" % ("신호군", "점수"))
    KO = {"trend": "추세·모멘텀", "vol": "변동성 안정도", "breadth": "시장 폭",
          "macro": "매크로·신용", "sector": "섹터 리더십"}
    for k in ("trend", "vol", "breadth", "macro", "sector"):
        print("  %-14s %5.1f  (가중 %d%%)" % (KO[k], cur["g"][k], W[k]))
    print("  %-14s %5s  (가중 10%% — **자료 없음, 뺐다**)" % ("심리", "—"))

    print("\n🚨 밴드가 다음 달을 가르나 (일 %d · 기준선 %+.2f%% · 승률 %.0f%%)"
          % (bt["base"]["n"], bt["base"]["mean"], bt["base"]["win"]))
    print("  %-12s %7s %8s %7s %9s" % ("밴드", "일수", "1개월", "승률", "기준선차"))
    for _lo, b in BANDS:
        if b in bt:
            v = bt[b]
            print("  %-12s %7d %+8.2f%% %6.0f%% %+9.2f%%p"
                  % (b, v["n"], v["mean"], v["win"], v["lift"]))
    print("\n→ %s" % os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
