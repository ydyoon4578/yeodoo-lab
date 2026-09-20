# -*- coding: utf-8 -*-
"""build/qg_lag.py — 연간 재무 지연 N개월(3·4·5). 규약은 PREREG-2026-09-21-QGLAG.md.

🚨 등록서에 적은 것만 한다. **성적을 보고 N 을 고르지 않는다**(§5).
   기본값은 4개월이고, 버리는 조건은 «아직 안 나온 재무» 관측이 0건이 아닐 때 하나뿐이다.
   3개월은 후보가 아니라 대조군이다 — SEC 비가속 마감 90일과 사실상 같다.

🚨 **재현판은 펀드가 아니다.** 펀드 원본의 roe·eg 는 122일이 이미 적용된 완성품이라
   지연을 바꿀 수 없다. 그래서 랩의 data/fx 로 다시 만든다. F0 이 그 재현을 판정한다.

무엇을 랩 자료로 만들고 무엇을 원본에서 그대로 쓰나 — **바꾸는 것을 하나로 묶기 위해서다**
   랩 data/fx 로 새로 : roe · eg (점수의 두 축)
   원본에서 그대로     : 유니버스·시가총액·지수비중·월수익(r_tr)·금융제외·CIK
   등록서 그대로       : 백분위 평균 → 6개월 평활 → 상위 30 회사 → 지수비중 비례 +
                       10% 상한 → 분기 형성 · 3개월 보유 · 왕복 25bp
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FX = os.path.join(DATA, "fx")
OUT = os.path.join(DATA, "_qg_lag.json")
sys.path.insert(0, os.path.join(ROOT, "build"))
import qg_cap as QC                                               # noqa: E402

MONTHS = [3, 4, 5]          # 등록서 §3-1 의 메뉴. 더하지 않는다
ANCHOR_DAYS = 122           # 펀드 원본 규칙 — 앵커용
Q_LAG_M = 4                 # 분기 재무: 분기말 + 4개월(발표일 없음 · 세 판 공통)
SMOOTH = 6                  # 점수 평활 개월
TOPN = 30
CAP = 10.0                  # 2026-09-21 사용자 결정


def eom(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return dt.date(y + m // 12, m % 12 + 1, 1) - dt.timedelta(days=1)


def minus_months(d, n):
    """달력으로 n개월 뺀 날. 말일이면 그 달 말일로 맞춘다."""
    y, m = d.year, d.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    last = (dt.date(y + m // 12, m % 12 + 1, 1) - dt.timedelta(days=1)).day
    return dt.date(y, m, min(d.day, last))


def load_fx():
    """종목 → {태그: {'q': [(날짜,값)], 'a': [...]}}. 날짜 오름차순."""
    out = {}
    for fn in os.listdir(FX):
        if not fn.endswith(".json"):
            continue
        t = fn[:-5]
        try:
            d = json.load(io.open(os.path.join(FX, fn), encoding="utf-8"))
        except Exception:
            continue
        g = {}
        for tag, v in (d.get("tags") or {}).items():
            gg = {}
            for kind in ("q", "a", "i"):   # i = 시점값(재무상태표) — 등록서 §3-2-a
                s = v.get(kind) or []
                gg[kind] = sorted(((x[0], float(x[1])) for x in s if x and x[1] is not None),
                                  key=lambda z: z[0])
            g[tag] = gg
        out[t] = g
    return out


def _annual(f, tag):
    """시점값(`i`)에서 **회계연도 말** 관측만 골라 연간 계열을 만든다(등록서 §3-2-a).

    회계연도 말은 «연간 순이익(`ni.a`)이 찍힌 날짜» 로 정한다 — 그것이 그 회사의 결산일이다.
    ⚠ 결산일에 `i` 관측이 없으면 그 해는 버린다. 가까운 날로 당겨 쓰지 않는다.
    """
    ends = {d for d, _ in ((f.get("ni") or {}).get("a") or [])}
    return [(d, v) for d, v in ((f.get(tag) or {}).get("i") or []) if d in ends]


def _annual_prev(f, tag, fy_iso):
    s = _annual(f, tag)
    return [x for x in s if x[0] < fy_iso]


def asof(series, cut_iso):
    """cut 이전(포함)의 **가장 최근** 관측. 없으면 None."""
    best = None
    for d, v in series:
        if d <= cut_iso:
            best = (d, v)
        else:
            break
    return best


def build_scores(FXD, panel, lag_m=None, lag_days=None):
    """형성월 × 종목 → (roe, eg). lag_m 이면 달력 개월, lag_days 면 일수(앵커).

    ROE — 분기 순이익 ÷ 직전 분기말 자기자본. **분기 지연은 세 판 공통**(Q_LAG_M).
    EG  — 다음 해 투자증가율 예측. log q · cop · dROE 의 **과거 평균 기울기**를 곱한다.
          ⚠ 원문(Hou·Mo·Xue·Zhang 2021)의 cop 는 매출·매입채무 등의 증감까지 쓰는데
            data/fx 에 그 구성요소가 없다. **cfo/asset 을 대용**으로 쓴다. 결과에 적는다.
    """
    yms = sorted(panel.ym.unique())
    roe_by, eg_in, late = {}, {}, 0
    for ym in yms:
        e = eom(ym)
        qcut = minus_months(e, Q_LAG_M).isoformat()
        acut = (minus_months(e, lag_m) if lag_m is not None
                else (e - dt.timedelta(days=lag_days))).isoformat()
        # 🚨 «아직 안 나온 재무» 감시 — 결산일이 acut 이전인데 SEC 비가속 마감(90일)이
        #   형성일보다 뒤인 관측. 등록서 §4-4 · §5-② 가 요구한 수다.
        R, G = {}, {}
        for t in panel.loc[panel.ym == ym, "tkr"]:
            f = FXD.get(t)
            if not f:
                continue
            ni = asof((f.get("ni") or {}).get("q") or [], qcut)
            eqs = (f.get("eq") or {}).get("i") or []
            if ni:
                prev = [x for x in eqs if x[0] < ni[0]]
                if prev and prev[-1][1] > 0:
                    R[t] = ni[1] / prev[-1][1]
            aa = _annual(f, "asset")
            a0 = asof(aa, acut)
            if not a0:
                continue
            if (dt.date.fromisoformat(a0[0]) + dt.timedelta(days=90)) > e:
                late += 1
            ap = [x for x in aa if x[0] < a0[0]]
            if not ap or ap[-1][1] <= 0 or a0[1] <= 0:
                continue
            ia = (a0[1] - ap[-1][1]) / ap[-1][1]
            cfo = asof((f.get("cfo") or {}).get("a") or [], acut)
            nia = asof((f.get("ni") or {}).get("a") or [], acut)
            eqa = asof((f.get("eq") or {}).get("i") or [], acut)
            if not (cfo and nia and eqa) or eqa[1] <= 0:
                continue
            nip = [x for x in ((f.get("ni") or {}).get("a") or []) if x[0] < nia[0]]
            eqp = _annual_prev(f, "eq", eqa[0])
            droe = (nia[1] / eqa[1] - nip[-1][1] / eqp[-1][1]) if (nip and eqp and eqp[-1][1] > 0) else np.nan
            liab = asof((f.get("liab") or {}).get("i") or [], acut)
            G[t] = {"ia": ia, "fy": a0[0], "asset": a0[1],
                    "cop": cfo[1] / a0[1], "droe": droe,
                    "liab": (liab[1] if liab else 0.0)}
        roe_by[ym] = R
        eg_in[ym] = G
    return roe_by, eg_in, late


def eg_predict(eg_in, mcap_by):
    """과거 평균 기울기로 다음 해 투자증가율을 예측한다(확장창 · 시점정확).

    각 형성월에서 **그때까지 결과가 드러난** (특성, 다음해 IA) 짝만 모아 회귀한다.
    """
    yms = sorted(eg_in)
    # 회사별 회계연도 → ia, 그리고 그 다음 회계연도의 ia
    hist = {}                                   # t -> {fy: ia}
    for ym in yms:
        for t, g in eg_in[ym].items():
            hist.setdefault(t, {})[g["fy"]] = g["ia"]
    nxt = {}
    for t, m in hist.items():
        ks = sorted(m)
        for a, b in zip(ks, ks[1:]):
            nxt[(t, a)] = m[b] - m[a]           # 다음 해 투자증가율의 변화

    out = {}
    for ym in yms:
        mc = mcap_by.get(ym, {})
        rows, X, y = [], [], []
        for t, g in eg_in[ym].items():
            m = mc.get(t)
            if not m or m <= 0 or not np.isfinite(g["droe"]):
                continue
            q = (m + g["liab"]) / g["asset"]
            if q <= 0:
                continue
            x = [np.log(q), g["cop"], g["droe"]]
            rows.append((t, x))
            v = nxt.get((t, g["fy"]))
            if v is not None and np.isfinite(v):
                X.append(x); y.append(v)
        if len(X) < 50 or not rows:
            out[ym] = {}
            continue
        A = np.column_stack([np.ones(len(X)), np.asarray(X, float)])
        b, *_ = np.linalg.lstsq(A, np.asarray(y, float), rcond=None)
        out[ym] = {t: float(b[0] + np.dot(b[1:], x)) for t, x in rows}
    return out


def pct_rank(d):
    if not d:
        return {}
    s = pd.Series(d, dtype="float64").dropna()
    if s.empty:
        return {}
    return (s.rank(pct=True)).to_dict()


def select(roe_by, eg_by, panel, cikmap, fin):
    """백분위 평균 → 6개월 평활 → 회사 단위 상위 30."""
    yms = sorted(roe_by)
    raw = {}
    for ym in yms:
        ok = set(panel.loc[(panel.ym == ym), "tkr"]) - fin
        r = pct_rank({t: v for t, v in roe_by[ym].items() if t in ok})
        g = pct_rank({t: v for t, v in (eg_by.get(ym) or {}).items() if t in ok})
        both = set(r) & set(g)
        raw[ym] = {t: (r[t] + g[t]) / 2 for t in both}
    sm, sel = {}, {}
    for i, ym in enumerate(yms):
        win = yms[max(0, i - SMOOTH + 1):i + 1]
        acc = {}
        for w in win:
            for t, v in raw[w].items():
                acc.setdefault(t, []).append(v)
        sm[ym] = {t: float(np.mean(v)) for t, v in acc.items() if len(v) >= 1}
        # 회사 단위 — 같은 CIK 는 점수 최고 종목 하나만
        best = {}
        for t, v in sm[ym].items():
            c = cikmap.get(t, t)
            if c not in best or v > best[c][1]:
                best[c] = (t, v)
        top = sorted(best.values(), key=lambda z: (-z[1], z[0]))[:TOPN]
        sel[ym] = [t for t, _ in top]
    return sel


def main():
    print("자료 읽는 중 …")
    q = pd.read_pickle(QC.SRC)
    QC.CIK = QC.cik_map()
    cikmap = QC.CIK
    idx = pd.read_pickle(QC.SRC_IX)
    idx_pr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    Xd = pd.read_csv(QC.DIV)
    idx_div = dict(zip(Xd.iloc[:, 0].astype(str), Xd.iloc[:, 4]))
    FXD = load_fx()
    print("  data/fx %d종 · 패널 %d월" % (len(FXD), q.ym.nunique()))

    # 금융업 — 원본의 점수대상 판정을 그대로 쓴다(scored != 'Y' 중 금융제외분)
    fin = set(q.loc[q.scored.astype(str).str.contains("금융", na=False), "tkr"])
    if not fin:
        fin = set()
    mcap_by = {m: dict(zip(g.tkr, g.mcap)) for m, g in q.groupby("ym")}
    panel = q[["ym", "tkr"]]

    res = {"prereg": "PREREG-2026-09-21-QGLAG.md", "cap_pct": CAP,
           "note": "랩 data/fx 로 만든 **재현판**이다. 펀드 카드에 싣지 않는다.",
           "cop_proxy": "cfo/asset — 원문의 cop 구성요소가 data/fx 에 없다",
           "runs": {}}

    # ── 앵커: 122일판 ─────────────────────────────────────────────────────
    print("\n앵커 — 122일 재현판을 만든다")
    roe_a, egin_a, late_a = build_scores(FXD, panel, lag_days=ANCHOR_DAYS)
    eg_a = eg_predict(egin_a, mcap_by)
    sel_a = select(roe_a, eg_a, panel, cikmap, fin)

    forms = [m for m in sorted(sel_a) if int(m[5:7]) in (3, 6, 9, 12)]
    orig = {m: set(g.tkr) for m, g in q[q.top30 == "Y"].groupby("ym") if int(m[5:7]) in (3, 6, 9, 12)}
    ov = [len(set(sel_a[m]) & orig[m]) for m in forms if m in orig and sel_a[m]]
    print("  상위30 겹침 — 중앙 %.1f/30 · 최저 %d · 평균 %.1f (형성 %d회)"
          % (np.median(ov), min(ov), np.mean(ov), len(ov)))
    res["anchor"] = {"overlap_median": float(np.median(ov)), "overlap_min": int(min(ov)),
                     "overlap_mean": float(np.mean(ov)), "n_form": len(ov),
                     "late_obs": late_a}
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1, default=float))
    if np.median(ov) < 20:
        print("\n🚨 F0 — 앵커 겹침 중앙 %.1f/30 < 20. **측정 불가로 닫는다**(등록서 §6)."
              % np.median(ov))
        print("→ %s" % OUT)
        return 0
    print("  F0 1차 통과 — 월별 초과 상관은 아래에서 본다")
    return run_menu(res, q, idx_pr, idx_div, FXD, panel, mcap_by, cikmap, fin, sel_a, forms)


def run_menu(res, q, idx_pr, idx_div, FXD, panel, mcap_by, cikmap, fin, sel_a, forms):
    def perf(sel):
        qq = q.copy()
        key = {(m, t) for m in sel for t in sel[m]}
        qq["top30"] = ["Y" if (a, b) in key else None for a, b in zip(qq.ym, qq.tkr)]
        ex, tn, t3, _ = QC.run(qq, idx_pr, idx_div, cap=CAP)
        return ex, tn, t3
    ex_a, _, _ = perf(sel_a)
    ex_o, _, _ = QC.run(q, idx_pr, idx_div, cap=CAP)[:1] + (0, 0)
    j = ex_a.index.intersection(ex_o.index)
    c = float(np.corrcoef(ex_a.reindex(j), ex_o.reindex(j))[0, 1])
    print("  월별 초과 상관(재현 122일 vs 원본) = %.3f" % c)
    res["anchor"]["ret_corr"] = c
    if c < 0.80:
        print("\n🚨 F0 — 상관 %.3f < 0.80. **측정 불가로 닫는다**(등록서 §6)." % c)
        io.open(OUT, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1, default=float))
        return 0
    print("\n%-6s %9s %8s %7s %7s %9s %10s" %
          ("N개월", "연초과%p", "TE%", "IR", "t", "상위3사%", "늦은관측"))
    sels = {}
    for N in MONTHS:
        roe, egin, late = build_scores(FXD, panel, lag_m=N)
        eg = eg_predict(egin, mcap_by)
        s = select(roe, eg, panel, cikmap, fin)
        sels[N] = s
        ex, tn, t3 = perf(s)
        st = QC.stats(ex)
        st.update({"turn_y_pct": tn, "top3_pct": t3, "late_obs": late})
        res["runs"]["%dM" % N] = st
        print("%-6s %+9.2f %8.2f %7.2f %7.2f %9.1f %10d"
              % ("%d개월" % N, st["excess_y_pp"], st["te_y_pct"], st["ir"], st["t"], t3, late))
    ks = sorted(sels)
    res["menu_overlap"] = {
        "%dM_vs_%dM" % (a, b): float(np.mean([len(set(sels[a][m]) & set(sels[b][m]))
                                              for m in forms if m in sels[a] and m in sels[b]]))
        for a in ks for b in ks if a < b}
    print("\n판 사이 명단 겹침(30 중):", " · ".join(
        "%s %.1f" % (k, v) for k, v in res["menu_overlap"].items()))
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1, default=float))
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
