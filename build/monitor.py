# -*- coding: utf-8 -*-
"""build/monitor.py — 여두 전략 랩 시장 국면 모니터 → data/_monitor.json

설계 출처는 사용자 제공 「시장 국면 모니터」(KBAM, 2026-07-09)지만 **자료는 이 랩 것만** 쓴다.
사내 DB·내부 테이블·사내 경로는 쓰지 않는다 — 설계와 방법론만 가져왔다.

무엇을 싣나
  ① 종합 Risk-On/Off      — _riskonoff.json (5 신호군 · 심리 10%는 자료가 없어 뺐다)
  ② 지금 시장             — 여기서 계산. 실제 값 + «역사적으로 어디쯤»(백분위)
  ③ 극단 플래그           — _flags.json (9개)
  ④ 랩 전략 온도계        — 여기서 계산. 201종 중 지금 S&P 를 이기는 비율
  ⑤ 국면 15칸 중 지금 칸  — _regime_grid.json (판정 「측정만」)
  ⑥ 안 선다고 잰 것       — 이 랩이 **기각**한 기록. 모니터가 예언으로 읽히지 않게 같이 싣는다

🚨 이 파일은 **새 주장을 만들지 않는다.** ①③⑤는 이미 판정이 붙은 것을 옮기고,
   ②는 사실이고, ④는 «지난달에 이런 일이 있었다»이지 예측이 아니다.
   그래서 사전등록이 필요 없다. 여기에 «그러니 무엇을 사라» 를 더하면 그때는 필요하다.

⚠ 여기서 백테스트도 점수도 다시 굽지 않는다. 이미 구운 산출물을 읽어 모은다.
   ②와 ④만 계산하고, 그것도 assets.json · strategy_charts.json 만 읽는다.

  python build/monitor.py
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_monitor.json")

J = lambda n: json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))  # noqa: E731

CYC = [("XLK", "기술"), ("XLC", "커뮤니케이션"), ("XLY", "경기소비"), ("XLF", "금융"),
       ("XLI", "산업"), ("XLE", "에너지"), ("XLB", "소재")]
DEF = [("XLV", "헬스케어"), ("XLP", "필수소비"), ("XLU", "유틸리티"), ("XLRE", "리츠")]
IXE = [("SPY", "S&P 500"), ("QQQ", "나스닥 100"), ("RSP", "S&P 동일가중"),
       ("IWM", "소형주"), ("EFA", "선진 해외"), ("EEM", "신흥")]
BND = [("TLT", "미 장기국채"), ("IEF", "미 중기국채"), ("HYG", "하이일드"),
       ("GLD", "금"), ("UUP", "달러")]


def pct_rank(v, hist):
    """지금 값이 그 계열 역사에서 몇 %. 선견 없음 — 오늘까지만 본다."""
    h = [x for x in hist if x is not None]
    if not h or v is None:
        return None
    return sum(1 for x in h if x < v) / len(h) * 100


def main() -> int:
    RO = J("_riskonoff.json")
    FL = J("_flags.json")
    RG = J("_regime_grid.json")
    A = J("assets.json")
    d, px, mac = A["dates"], A["px"], (A.get("macro") or {})
    k = len(d) - 1

    def ret(t, n):
        p = px.get(t)
        if not p or k - n < 0 or p[k] is None or p[k - n] is None:
            return None
        return (p[k] / p[k - n] - 1) * 100

    def rets(t):
        return {"1m": ret(t, 21), "3m": ret(t, 63), "12m": ret(t, 252)}

    # ── ② 지금 시장 ───────────────────────────────────────────────────
    ixe = [{"t": t, "ko": ko, **rets(t)} for t, ko in IXE if t in px]
    bnd = [{"t": t, "ko": ko, **rets(t)} for t, ko in BND if t in px]
    sec = [{"t": t, "ko": ko, "grp": g, **rets(t)}
           for g, lst in (("경기민감", CYC), ("방어", DEF)) for t, ko in lst if t in px]
    cy = [s["1m"] for s in sec if s["grp"] == "경기민감" and s["1m"] is not None]
    df = [s["1m"] for s in sec if s["grp"] == "방어" and s["1m"] is not None]

    def mv(code, back=0):
        s = mac.get(code) or {}
        ks = sorted(s)
        if len(ks) <= back:
            return None, None
        return s[ks[-1 - back]], ks[-1 - back]

    MACRO = [("DGS10", "미 10년 금리", "%"), ("DGS2", "미 2년 금리", "%"),
             ("T10Y2Y", "장단기차 10-2", "%p"), ("DFII10", "실질금리 10년", "%"),
             ("T10YIE", "기대 인플레", "%"), ("BAA10Y", "회사채 가산(BAA)", "%p"),
             ("BAMLH0A0HYM2", "하이일드 OAS", "%p"), ("EBP", "초과채권프리미엄", ""),
             ("DTWEXBGS", "달러지수(광의)", ""), ("VIXCLS", "VIX", "")]
    macro = []
    for code, ko, unit in MACRO:
        s = mac.get(code)
        if not s:
            continue
        ks = sorted(s)
        now = s[ks[-1]]
        m1 = s[ks[-22]] if len(ks) > 22 else None
        m3 = s[ks[-64]] if len(ks) > 64 else None
        macro.append({"code": code, "ko": ko, "unit": unit, "now": now, "as_of": ks[-1],
                      "d1m": (now - m1) if m1 is not None else None,
                      "d3m": (now - m3) if m3 is not None else None,
                      "pct": pct_rank(now, [s[x] for x in ks])})

    # ── ④ 랩 전략 온도계 ──────────────────────────────────────────────
    CH = J("strategy_charts.json")
    IXm = CH["idx_monthly"]["S&P 500"]
    IDX = {s["sid"]: s for s in J("strategy_index.json")["items"]}
    months = sorted(IXm)
    # 🚨 마지막 달은 부분 달일 수 있다 — 완전한 달만 센다.
    #   strategy_charts 의 partial 이 연도 단위라 달로는 못 쓴다. 그래서 _riskonoff 기준일의
    #   달이 아직 안 끝났으면(기준일이 말일이 아니면) 그 달을 뺀다.
    last_full = months[-2] if RO["as_of"][:7] == months[-1] else months[-1]
    W = [("1m", 1), ("3m", 3), ("12m", 12)]
    temp, by_role = {}, {}
    for hz, nmo in W:
        sel = [m for m in months if m <= last_full][-nmo:]
        beat = tot = 0
        rr = {}
        for sid, c in CH["charts"].items():
            s = IDX.get(sid)
            if not s:
                continue
            mo = {m["m"]: m.get("r") for m in (c.get("monthly") or [])}
            v = [mo.get(m) for m in sel]
            if any(x is None for x in v):
                continue
            f = b = 1.0
            for m, x in zip(sel, v):
                f *= 1 + x / 100.0
                b *= 1 + IXm[m] / 100.0
            w = f > b
            tot += 1
            beat += 1 if w else 0
            role = s.get("role") or "?"
            a, t2 = rr.get(role, (0, 0))
            rr[role] = (a + (1 if w else 0), t2 + 1)
        temp[hz] = {"beat": beat, "n": tot, "pct": (beat / tot * 100) if tot else None,
                    "months": sel}
        by_role[hz] = {r: {"beat": a, "n": t2, "pct": a / t2 * 100} for r, (a, t2) in rr.items()}

    # ── ⑤ 국면 15칸에서 지금 칸 ───────────────────────────────────────
    hist = RO.get("hist") or []
    d5 = (hist[-1]["score"] - hist[-2]["score"]) if len(hist) >= 2 else None
    tr = ("▲ 오름" if d5 is not None and d5 >= 2 else
          "▼ 내림" if d5 is not None and d5 <= -2 else "→ 옆")
    cell_key = "%s|%s" % (RO["band"], tr)
    cell = (RG.get("grid") or {}).get(cell_key)

    doc = {
        "note": "여두 전략 랩 시장 국면 모니터. 설계 출처는 사용자 제공 KBAM 「시장 국면 모니터」"
                "(2026-07-09)이고 **자료는 이 랩 것만** 쓴다. 새 주장을 만들지 않는다 — "
                "①③⑤는 이미 판정이 붙은 것을 옮기고, ②는 사실, ④는 지난달 기록이다.",
        "as_of": RO["as_of"], "spx": FL.get("spx"),
        "s1": {"score": RO["score"], "band": RO["band"], "groups": RO["groups"],
               "weights": RO["weights"], "missing": RO["missing"],
               "breadth_now": RO.get("breadth_now"), "d5": d5, "trend": tr,
               "weight_note": RO.get("weight_note")},
        "s2": {"index": ixe, "bond": bnd, "sector": sec,
               "cyc_1m": (sum(cy) / len(cy)) if cy else None,
               "def_1m": (sum(df) / len(df)) if df else None,
               "macro": macro, "as_of": d[k]},
        "s3": {"as_of": FL["as_of"], "base": FL["base"], "flags": FL["flags"],
               "dropped": FL.get("dropped")},
        "s4": {"temp": temp, "by_role": by_role, "last_full": last_full,
               "bench": "S&P 500", "note": "완전한 달만 센다. 부분 달은 빼고 계산했다."},
        "s5": {"cell": cell_key, "stat": cell, "verdict": RG.get("verdict"),
               "base_mean": RG.get("base_mean"),
               "note": "판정 「측정만」 — 밴드가 거꾸로 가고 추세축으로도 안 풀렸다"
                       "(PREREG-2026-09-21-REGIMEGRID). 방향을 믿고 쓰는 표가 아니다."},
        # 🚨 ⑥ 이 칸이 이 모니터를 사내 자료와 가르는 자리다. 안 선 것을 같이 실어야
        #   나머지 다섯 칸이 예언으로 안 읽힌다.
        "s6": [
            {"무엇": "유사 달 찾기(3개월 궤적)", "판정": "기각",
             "잰 것": "닮은 달로 고른 전략 0.55/5 vs 그냥 최다 진입 0.75/5 · "
                     "방향 54.2% vs 기준선 65.4%",
             "출처": "build/analog.py · 2026-09-21"},
            # ⚠ 이 칸 글은 표에서 74자에 잘린다 — 잘리지 않게 여기서 줄여 적는다.
            {"무엇": "RRG 4분면 팩터 로테이션", "판정": "기각",
             "잰 것": "시계 67.4% vs 뒤섞은 귀무 67.0% — 회전은 산식의 성질. 주도는 기준선 아래",
             "출처": "PREREG-2026-09-22-RRG-RESULT"},
            {"무엇": "종합 점수 밴드의 방향", "판정": "측정만(역방향)",
             "잰 것": "Risk-Off +2.02% vs Risk-On +0.34%. 추세축 더해도 3/3 · 겹침 빼면 t 0.29",
             "출처": "PREREG-2026-09-21-REGIMEGRID-RESULT"},
            {"무엇": "국면 조건부 규칙 전반", "판정": "12번 중 11번 기각",
             "잰 것": "이 랩이 국면으로 규칙을 가르려 한 시도의 성적",
             "출처": "랩 등록부"},
            {"무엇": "t-stat + 단조성 결합(Two Heads)", "판정": "측정만",
             "잰 것": "OOS Combined +37.6bp 인데 t 0.99 · walk-forward 에서 부호 뒤집힘",
             "출처": "PREREG-2026-09-21-TWOHEADS-RESULT"},
        ],
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    # ── 화면 ──────────────────────────────────────────────────────────
    b = doc["s1"]["breadth_now"] or {}
    print("\n여두 전략 랩 시장 국면 모니터 — 기준 %s · S&P %.0f" % (doc["as_of"], doc["spx"] or 0))
    print("\n① 종합 **%.1f** → %s   (5일 변화 %+.1f · %s)"
          % (doc["s1"]["score"], doc["s1"]["band"], d5 or 0, tr))
    for kk, ko in (("trend", "추세·모멘텀"), ("vol", "변동성 안정도"), ("breadth", "시장 폭"),
                   ("macro", "매크로·신용"), ("sector", "섹터 리더십")):
        print("     %-12s %5.1f" % (ko, doc["s1"]["groups"][kk]))
    if b:
        print("   시장 폭 원수치 — %%>MA200 %.1f%% · %%>MA50 %.1f%% · 20일상승 %.1f%% · 신고-신저 %+.1f%%p"
              % (b["a200"], b["a50"], b["up20"], b["nhnl"]))

    print("\n② 지금 시장")
    for r in ixe:
        print("   %-12s 1M %+6.2f%%  3M %+6.2f%%  12M %+6.2f%%"
              % (r["ko"], r["1m"] or 0, r["3m"] or 0, r["12m"] or 0))
    print("   경기민감 %+.2f%%  vs  방어 %+.2f%%  → 차 %+.2f%%p"
          % (doc["s2"]["cyc_1m"] or 0, doc["s2"]["def_1m"] or 0,
             (doc["s2"]["cyc_1m"] or 0) - (doc["s2"]["def_1m"] or 0)))
    for m in macro:
        print("   %-16s %8.2f%-2s  1M %+6.2f  3M %+6.2f   역사 %3.0f%%"
              % (m["ko"], m["now"], m["unit"], m["d1m"] or 0, m["d3m"] or 0, m["pct"] or 0))

    on = [f for f in FL["flags"] if f["now"] == "ON"]
    wn = [f for f in FL["flags"] if f["now"] == "주의"]
    print("\n③ 극단 플래그 — ON %d · 주의 %d / %d개" % (len(on), len(wn), len(FL["flags"])))
    for f in on + wn:
        print("   %-6s %-18s %s" % (f["now"], f["ko"], f["value"]))

    print("\n④ 랩 전략 온도계 (S&P 대비 · 완전한 달만 · %s 까지)" % last_full)
    for hz, _n in W:
        t2 = temp[hz]
        print("   최근 %-4s 이긴 전략 %3d / %3d = **%.0f%%**"
              % (hz, t2["beat"], t2["n"], t2["pct"] or 0))
    print("   1개월 역할별 — " + " · ".join(
        "%s %.0f%%(%d)" % (r, v["pct"], v["n"]) for r, v in sorted(by_role["1m"].items())))

    print("\n⑤ 국면 15칸에서 지금 칸: **%s**" % cell_key)
    if cell and cell.get("n"):
        print("   역사적으로 이 칸 다음 달 %+.2f%% (%d일 · 기준선 %+.2f%%) — 판정 %s"
              % (cell["mean"], cell["n"], doc["s5"]["base_mean"], doc["s5"]["verdict"]))

    print("\n⑥ 안 선다고 잰 것 %d건 — 이 칸이 나머지를 예언으로 안 읽히게 한다" % len(doc["s6"]))
    for x in doc["s6"]:
        print("   %-26s %s" % (x["무엇"], x["판정"]))
    print("\n→ _monitor.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
