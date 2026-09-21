# -*- coding: utf-8 -*-
"""build/qg_size.py — 국면으로 비중을 줄이는 판. 규약은 PREREG-2026-09-21-QGSIZE.md.

🚨 등록서에 적은 것만 한다. 문턱·k·w 를 결과를 보고 바꾸지 않는다(§7-2).
🚨 판정은 **연 초과가 아니라 비율**이다 — 민감도 ÷ 오경보율 > S⁺/|S⁻|(§2).
🚨 다섯 조건을 다섯 번의 시행으로 세지 않는다. 같은 리플레이션 국면이라 **하나**다(§7-1).
⚠ §4-5 의 흔들기 표는 **참고**이지 선택지가 아니다. 판정은 아래 상수로만 한다.
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
OUT = os.path.join(DATA, "_qg_size.json")
sys.path.insert(0, os.path.join(ROOT, "build"))
import qg_cap as QC                                                # noqa: E402
from maxyears import MAX_YEARS, cap as capidx, check_const         # noqa: E402

# ── 등록서 §3 의 상수. 손대지 않는다 ──────────────────────────────────────
CAP = 10.0            # 펀드의 한 회사 상한(2026-09-21 사용자 결정)
W_OFF = 0.60          # 켜졌을 때의 비중
K_ON = 3              # 다섯 중 몇 개면 켜지나(과반)
T_RATE = 0.50         # C1 DGS10 3개월 상승 %p
T_CYC = 5.0           # C2 (XLE,XLB) − SPY %p
T_FIN = 3.0           # C3 XLF − SPY %p
T_BRD = 55.0          # C4 패널 3개월 지수초과 비율 %
T_VIX = 20.0          # C5 형성월말 VIX
COST_SW = 0.0025      # 전환비용 — 비중 이동폭에 곱한다(왕복 25bp)
FORM_M = (3, 6, 9, 12)


def eom(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return dt.date(y + m // 12, m % 12 + 1, 1) - dt.timedelta(days=1)


def ym_add(ym, k):
    t = int(ym[:4]) * 12 + int(ym[5:7]) - 1 + k
    return "%04d-%02d" % (t // 12, t % 12 + 1)


def load_assets():
    d = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    dts = d["dates"]
    px = {k: np.asarray([np.nan if v is None else float(v) for v in v_], float)
          for k, v_ in d["px"].items()}
    # ⚠ macro 는 px 와 **모양이 다르다** — 날짜→값 딕셔너리다(px 는 dates 와 같은 길이 배열).
    #   한 파일 안에서 두 모양이 섞여 있으므로 여기서 갈라 읽는다.
    mac = {k: {d_: (None if v is None else float(v)) for d_, v in (v_ or {}).items()}
           for k, v_ in (d.get("macro") or {}).items()}
    return dts, px, mac


def mac_asof(series, iso):
    """날짜→값 딕셔너리에서 iso 이전(포함) 마지막 값. 없으면 nan."""
    best = np.nan
    for d_, v in series.items():
        if d_ <= iso and v is not None:
            if not isinstance(best, tuple) or d_ > best[0]:
                best = (d_, v)
    return best[1] if isinstance(best, tuple) else np.nan


def asof_i(dts, iso):
    """iso 이전(포함) 마지막 거래일 인덱스. 없으면 None."""
    lo, hi = 0, len(dts) - 1
    if dts[0] > iso:
        return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if dts[mid] <= iso:
            lo = mid
        else:
            hi = mid - 1
    return lo


def last_valid(a, i):
    """i 이하에서 유효한 마지막 값."""
    for k in range(i, max(-1, i - 40), -1):
        if k >= 0 and np.isfinite(a[k]):
            return a[k]
    return np.nan


def conditions(forms, q, ipr, idiv):
    """형성월 말까지의 **후행** 자료로 다섯 조건. 반환 {형성월: [C1..C5]}"""
    dts, px, mac = load_assets()
    ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in q.groupby("ym")}
    out, raw = {}, {}
    for f in forms:
        e = eom(f).isoformat()
        i1 = asof_i(dts, e)
        i0 = asof_i(dts, (eom(ym_add(f, -3))).isoformat())
        if i1 is None or i0 is None:
            continue

        def ch(tk):
            a = px.get(tk)
            if a is None:
                return np.nan
            x0, x1 = last_valid(a, i0), last_valid(a, i1)
            return (x1 / x0 - 1) * 100 if (np.isfinite(x0) and np.isfinite(x1) and x0 > 0) else np.nan

        spy = ch("SPY")
        d10 = mac.get("DGS10") or {}
        r0 = mac_asof(d10, eom(ym_add(f, -3)).isoformat())
        r1 = mac_asof(d10, e)
        c1 = (r1 - r0)
        c2 = np.nanmean([ch("XLE"), ch("XLB")]) - spy
        c3 = ch("XLF") - spy
        # C4 — 패널 종목의 직전 3개월 지수 초과 비율
        hits, tot = 0, 0
        for t in set(q.loc[q.ym == f, "tkr"]):
            c, b, ok = 1.0, 1.0, True
            for k in (2, 1, 0):
                m = ym_add(f, -k)
                r = ret.get(ym_add(m, -1), {}).get(t)
                if r is None:
                    ok = False
                    break
                c *= (1 + r)
                b *= (1 + ipr.get(m, 0) + idiv.get(m, 0))
            if ok:
                tot += 1
                hits += 1 if c > b else 0
        c4 = (hits / tot * 100) if tot else np.nan
        c5 = last_valid(px.get("^VIX", np.array([np.nan])), i1)
        raw[f] = {"C1_rate_pp": c1, "C2_cyc_pp": c2, "C3_fin_pp": c3,
                  "C4_breadth_pct": c4, "C5_vix": c5, "n_breadth": tot}
        out[f] = [int(c1 >= T_RATE) if np.isfinite(c1) else 0,
                  int(c2 >= T_CYC) if np.isfinite(c2) else 0,
                  int(c3 >= T_FIN) if np.isfinite(c3) else 0,
                  int(c4 >= T_BRD) if np.isfinite(c4) else 0,
                  int(c5 >= T_VIX) if np.isfinite(c5) else 0]
    return out, raw


def qseries(ex):
    """보유 분기별 초과(%p)와 그 분기의 형성월."""
    ms = [str(p) for p in ex.index]
    v = ex.to_numpy()
    rows = []
    for i in range(0, len(v) - len(v) % 3, 3):
        f = ym_add(ms[i], -1)                      # 첫 보유월의 직전 = 형성월
        rows.append((f, ms[i], float(np.prod(1 + v[i:i + 3]) - 1) * 100))
    return rows


def run(rows, on, w_off, k_on, cost=True):
    """on[f] = 켜진 조건 수. 반환 (분기 수익 배열, 켜짐 배열, 전환 횟수)"""
    out, flag, prev, sw = [], [], 1.0, 0
    for f, m0, x in rows:
        n = on.get(f)
        w = w_off if (n is not None and n >= k_on) else 1.0
        c = abs(w - prev) * COST_SW * 100 if cost else 0.0
        if abs(w - prev) > 1e-9:
            sw += 1
        out.append(x * w - c)
        flag.append(w < 1.0)
        prev = w
    return np.asarray(out), np.asarray(flag), sw


def ann(a):
    return (float(np.prod(1 + np.asarray(a) / 100)) ** (4.0 / len(a)) - 1) * 100


def main():
    check_const()
    q = pd.read_pickle(QC.SRC); QC.CIK = QC.cik_map()
    idx = pd.read_pickle(QC.SRC_IX)
    ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    Xd = pd.read_csv(QC.DIV)
    idiv = dict(zip(Xd.iloc[:, 0].astype(str), Xd.iloc[:, 4]))
    ex, _a, _b, _c = QC.run(q, ipr, idiv, cap=CAP)
    ex = ex.reindex(capidx(ex.index))                     # 🚨 10년 상한
    rows = qseries(ex)
    print("창 %s ~ %s · %d개월 · 분기 %d개"
          % (ex.index[0], ex.index[-1], len(ex), len(rows)))

    forms = [f for f, _m, _x in rows]
    on5, raw = conditions(forms, q, ipr, idiv)
    on = {f: sum(v) for f, v in on5.items()}

    qv = np.asarray([x for _f, _m, x in rows])
    Sp, Sm = qv[qv > 0].sum(), qv[qv <= 0].sum()
    need = Sp / abs(Sm)
    base = ann(qv)
    print("  대조군(늘 100%%) 연 %+.2f%%p · S+ %+.1f · S− %+.1f · 필요 비율 %.2f"
          % (base, Sp, Sm, need))

    r, flag, sw = run(rows, on, W_OFF, K_ON)
    neg, pos = qv <= 0, qv > 0
    sens = float(flag[neg].mean()) if neg.sum() else np.nan
    fpr = float(flag[pos].mean()) if pos.sum() else np.nan
    ratio = (sens / fpr) if fpr > 0 else np.inf
    a = ann(r)
    print("\n── 판정 ──")
    print("  켜진 분기 %d/%d · 전환 %d회" % (flag.sum(), len(flag), sw))
    print("  민감도 %.1f%% (마이너스 %d분기 중 %d) · 오경보율 %.1f%% (플러스 %d분기 중 %d)"
          % (sens * 100, neg.sum(), flag[neg].sum(), fpr * 100, pos.sum(), flag[pos].sum()))
    print("  🚨 비율 %.2f  vs  필요 %.2f  →  %s" % (ratio, need, "통과" if ratio > need else "❌ F1"))
    print("  연 초과 %+.2f%%p (대조군 %+.2f · 차 %+.2f)" % (a, base, a - base))

    F = {"F1_ratio": bool(ratio <= need), "F2_ann": bool(a <= base),
         "F3_few": bool(flag.sum() < 5), "F4_many": bool(flag.sum() > 25)}
    for k, v in F.items():
        if v:
            print("  ❌ %s 걸림" % k)

    # 상관 — 벽 ③
    C = pd.DataFrame({f: v for f, v in on5.items()}).T
    C.columns = ["C1", "C2", "C3", "C4", "C5"]
    cm = C.corr()
    iu = np.triu_indices(5, 1)
    print("\n  다섯 조건 상호 상관 평균 %.2f (최대 %.2f)"
          % (float(np.nanmean(cm.to_numpy()[iu])), float(np.nanmax(cm.to_numpy()[iu]))))
    print("  각 조건이 켜진 분기 수: " + " · ".join(
        "%s %d" % (c, int(C[c].sum())) for c in C.columns))

    # §4-5 흔들기 — 참고
    print("\n── 흔들기(참고 · 판정 아님) ──")
    shake = {}
    for k in (2, 3, 4):
        for w in (0.5, 0.6, 0.7):
            rr, ff, _s = run(rows, on, w, k)
            shake["k%d_w%.1f" % (k, w)] = {"ann": ann(rr), "n_on": int(ff.sum()),
                                           "sens": float(ff[neg].mean()) if neg.sum() else None,
                                           "fpr": float(ff[pos].mean()) if pos.sum() else None}
            print("   k=%d w=%.1f  연 %+6.2f%%p  켜짐 %2d  (대조군 대비 %+.2f)"
                  % (k, w, ann(rr), ff.sum(), ann(rr) - base))
    signs = [1 if v["ann"] > base else -1 for v in shake.values()]
    f5 = len(set(signs)) > 1
    print("  F5 — 부호가 갈리나: %s" % ("❌ 갈린다(측정만으로 닫는다)" if f5 else "안 갈린다"))

    res = {"prereg": "PREREG-2026-09-21-QGSIZE.md",
           "window": [str(ex.index[0]), str(ex.index[-1])], "n_q": len(rows),
           "cap_pct": CAP, "w_off": W_OFF, "k_on": K_ON,
           "thresholds": {"rate_pp": T_RATE, "cyc_pp": T_CYC, "fin_pp": T_FIN,
                          "breadth_pct": T_BRD, "vix": T_VIX},
           "base_ann": base, "S_plus": float(Sp), "S_minus": float(Sm),
           "need_ratio": float(need),
           "sens": sens, "fpr": fpr, "ratio": float(ratio), "ann": a,
           "n_on": int(flag.sum()), "n_switch": sw,
           "fail": F, "F5_sign_flip": bool(f5),
           "cond_corr_mean": float(np.nanmean(cm.to_numpy()[iu])),
           "quarters": [{"form": f, "hold_from": m0, "excess_pp": x,
                         "n_on": on.get(f), "cond": on5.get(f), "raw": raw.get(f)}
                        for (f, m0, x) in rows],
           "shake": shake}
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1, default=float))
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
