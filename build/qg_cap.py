# -*- coding: utf-8 -*-
"""build/qg_cap.py — 우량성장 30 의 **한 회사 상한**을 바꿔 다시 잰다(재진술).

🚨 이것은 **새 탐색이 아니다.** 사전등록_우량성장선별.md §4 가 상한 메뉴를
   (25·20·15·12·10%) 미리 못박아 두고 «법규·약관이 20% 를 허용하지 않으면 아래에서
   고른다. **고른 뒤에는 바꾸지 않는다**» 라고 적어 뒀다. 값도 이미 실려 있다.
   그런데 그 표는 **옛 잣대**(같은 종목 지수 대비)라 등록서 스스로 이렇게 적었다 —
   «상한 사이의 **상대 관계를 보는 표**로만 쓸 것».
   그래서 확정 잣대 B(바스켓 TR − S&P 500 TR)로 **같은 메뉴를 다시 진술**한다.
   `build/restate_10y.py` 가 창을 재진술한 것과 같은 성격이다.

🚨 사용자 결정 2026-09-21 — *"근데 20%는 너무 커. 10%로 하자"*
   ⚠ 등록서 §4 의 전제는 «법규·약관» 이었고 이번 사유는 **위험 선호**다.
     메뉴가 고정돼 있으므로 사후 탐색은 아니지만, **사유가 다르다는 사실은 적는다.**

⚠ 내가 하지 않는 것
   - 메뉴에 없는 상한(예: 18%·13%)을 만들어 더 나은 값을 찾는 일. 그것이 탐색이다.
   - 상한을 바꾸면서 **다른 손잡이**(종목 수·주기·평활)를 같이 건드리는 일.

앵커 — 20% 판이 `fund_fit.fund_monthly()` 와 맞아야 이 재현을 믿는다.
      안 맞으면 소리 내어 죽는다.
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_qg_cap.json")
sys.path.insert(0, os.path.join(ROOT, "build"))
from fund_fit import D18, fund_monthly                            # noqa: E402
from maxyears import MAX_YEARS, cap as capidx                     # noqa: E402

SRC = os.path.join(D18, r"02_우량성장_최소구성\qg_monthly.pkl")
SRC_IX = os.path.join(D18, r"02_우량성장_최소구성\qg_index.pkl")
DIV = os.path.join(D18, r"01_이관묶음\01_우량성장선별_산출물\idx_div_monthly_20260918.csv")
XL = os.path.join(D18, r"01_이관묶음\01_우량성장선별_산출물\우량성장선별30_준비데이터.xlsx")


def cik_map():
    """종목 → 기업식별번호(CIK). 듀얼클래스를 **한 회사로 묶기** 위해 필요하다.

    🚨 이것 없이 idxw 를 그대로 쓰면 GOOG 가 자기 클래스 몫만 갖고,
      재구성한 20% 판이 원본과 월 최대 1.34%p 어긋난다(앵커②).
    """
    import openpyxl
    ws = openpyxl.load_workbook(XL, read_only=True, data_only=True)["② 종목 기준정보"]
    m = {}
    for r in ws.iter_rows(min_row=3, values_only=True):
        if r and r[0] and r[1]:
            m[str(r[0]).strip()] = str(r[1]).strip()
    return m

CAPS = [25.0, 20.0, 15.0, 12.0, 10.0]     # 등록서 §4 의 메뉴 그대로. 더하지 않는다
COST_SIDE = 0.0025
HOLD0, HOLD1 = "2014-07", "2026-08"


def ym_add(ym, k):
    t = int(ym[:4]) * 12 + int(ym[5:7]) - 1 + k
    return "%04d-%02d" % (t // 12, t % 12 + 1)


def recap(base, cap):
    """상한을 걸고 넘치는 몫을 **남은 것에 비례 재배분**. 수렴까지 반복."""
    w = dict(base)
    for _ in range(200):
        over = [t for t, v in w.items() if v > cap + 1e-12]
        if not over:
            break
        ex = sum(w[t] - cap for t in over)
        for t in over:
            w[t] = cap
        free = [t for t in w if t not in over]
        s = sum(w[t] for t in free)
        if s <= 0:
            break
        for t in free:
            w[t] += ex * w[t] / s
    return w


def run(q, idx_pr, idx_div, cap=None):
    """cap=None 이면 자료의 wtgt 를 그대로 쓴다(=20% 원본)."""
    sel, forms = {}, []
    for f, g in q[q.top30 == "Y"].groupby("ym"):
        if int(f[5:7]) not in (3, 6, 9, 12):
            continue
        if cap is None:
            w = dict(zip(g.tkr, g.wtgt / 100.0))
        else:
            # 🚨 회사 단위로 지수비중을 합친다(듀얼클래스). 보유는 대표 종목 하나.
            pan = q[q.ym == f]
            comp = {}
            for tk, v in zip(pan.tkr, pan.idxw.astype(float)):
                c = CIK.get(tk, tk)
                comp[c] = comp.get(c, 0.0) + (0.0 if pd.isna(v) else float(v))
            iw = {t: comp.get(CIK.get(t, t), 0.0) for t in g.tkr}
            s = sum(iw.values())
            if s <= 0:
                continue
            w = {t: v for t, v in recap({t: v / s * 100.0 for t, v in iw.items()}, cap).items()}
            w = {t: v / 100.0 for t, v in w.items()}
        sel[f] = w
        forms.append(f)
    ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in q.groupby("ym")}
    out, prev, turn = {}, {}, {}
    for f in sorted(forms):
        w = sel[f]
        trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
        ch = False
        for k in (1, 2, 3):
            hm = ym_add(f, k)
            if not (HOLD0 <= hm <= HOLD1):
                continue
            r = ret.get(ym_add(f, k - 1), {})
            ok = {t: v for t, v in w.items() if t in r}
            s = sum(ok.values())
            if s <= 0:
                continue
            g = sum(v / s * r[t] for t, v in ok.items())
            out[hm] = g - (trade * COST_SIDE if not ch else 0.0)
            turn[hm] = trade if not ch else 0.0
            ch = True
            w = {t: (v / s) * (1 + r[t]) for t, v in ok.items()}
            z = sum(w.values()); w = {t: v / z for t, v in w.items()}
        prev = w
    ms = sorted(m for m in out if m in idx_pr and m in idx_div and pd.notna(idx_pr[m]))
    ex = pd.Series([out[m] - (idx_pr[m] + idx_div[m]) for m in ms],
                   index=pd.PeriodIndex(ms, freq="M"), dtype="float64")
    tn = sum(turn[m] for m in ms) / (len(ms) / 12.0) / 2 * 100
    top3 = float(np.mean([sum(sorted(sel[f].values(), reverse=True)[:3]) for f in forms]) * 100)
    return ex, tn, top3, sel


def stats(ex):
    n = len(ex)
    a = float(ex.mean()) * 1200
    te = float(ex.std(ddof=1)) * np.sqrt(12) * 100
    nav = (1 + ex).cumprod()
    return {"n": n, "excess_y_pp": a, "te_y_pct": te, "ir": a / te if te else None,
            "t": float(ex.mean() / (ex.std(ddof=1) / np.sqrt(n))),
            "mdd_ex_pct": float((nav / nav.cummax() - 1).min() * 100),
            "win_rate_pct": float((ex > 0).mean() * 100)}


CIK = {}


def series(cap=None):
    """상한 `cap` 판의 월별 초과 계열. cap=None 이면 자료의 wtgt(=20% 원본).

    🚨 `fund_card.py` 가 이것을 부른다. 상한을 바꾸면 카드의 성적·6팩터가 같이 따라간다.
    ⚠ 앵커는 main() 이 검사한다 — 여기서는 안 한다. 카드를 구울 때마다
      146개월을 두 번 더 돌리는 값을 치르지 않기 위해서다. **상한을 바꾸면
      `python build/qg_cap.py` 를 먼저 돌려 앵커가 서는지 본다.**
    """
    global CIK
    q = pd.read_pickle(SRC)
    if cap is not None and not CIK:
        CIK = cik_map()
    idx = pd.read_pickle(SRC_IX)
    idx_pr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(DIV)
    idx_div = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
    ex, tn, t3, _ = run(q, idx_pr, idx_div, cap=cap)
    # 🚨 2026-09-21 — MAX_YEARS = 10. 카드가 이 함수를 읽으므로 여기서 자른다.
    return ex.reindex(capidx(ex.index)), {"turn_y_pct": tn, "top3_pct": t3}


def main():
    global CIK
    q = pd.read_pickle(SRC)
    CIK = cik_map()
    print("CIK 지도 %d종 · 한 회사에 두 종목인 경우 %d건"
          % (len(CIK), len(CIK) - len(set(CIK.values()))))
    idx = pd.read_pickle(SRC_IX)
    idx_pr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(DIV)
    idx_div = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))

    # ── 앵커 ① 자료의 wtgt 그대로 → fund_monthly() 와 같아야 한다 ─────────
    ex0, tn0, t30, _ = run(q, idx_pr, idx_div, cap=None)
    ex0 = ex0.reindex(capidx(ex0.index))          # 🚨 10년 상한 — 앵커도 같은 창에서
    ref = fund_monthly()
    j = ex0.index.intersection(ref.index)
    gap = float((ex0.reindex(j) - ref.reindex(j)).abs().max())
    print("앵커① 원본 wtgt 재현 — 겹치는 %d개월 · 최대 차 %.2e" % (len(j), gap))
    if gap > 1e-12 or len(j) != len(ref):
        raise SystemExit("🚨 앵커 실패 — fund_monthly() 와 어긋난다. 여기서 멈춘다.")

    # ── 앵커 ② idxw 로 20% 를 다시 만들면 원본 wtgt 와 같은가 ─────────────
    ex20, tn20, t3_20, sel20 = run(q, idx_pr, idx_div, cap=20.0)
    ex20 = ex20.reindex(capidx(ex20.index))
    d = float((ex20 - ex0).abs().max())
    print("앵커② idxw→20%% 재구성 — 월별 초과 최대 차 %.4f%%p" % (d * 100))
    if d > 0.002:
        print("   ⚠ 완전히 같지는 않다(듀얼클래스 합산 등). **그 차이를 결과에 적는다.**")

    res = {"note": "등록서 §4 상한 메뉴를 확정 잣대 B 로 재진술. 새 탐색이 아니다.",
           "anchor_gap": gap, "recon_gap_pp": d * 100,
           "window": [str(ex0.index[0]), str(ex0.index[-1])], "caps": {}}
    print("\n%-8s %9s %8s %7s %7s %8s %9s %8s" %
          ("상한", "연초과%p", "TE%", "IR", "t", "MDD%", "연회전%", "상위3사%"))
    base = None
    for c in CAPS:
        ex, tn, t3, _ = run(q, idx_pr, idx_div, cap=c)
        ex = ex.reindex(capidx(ex.index))         # 🚨 10년 상한
        s = stats(ex); s["turn_y_pct"] = tn; s["top3_pct"] = t3
        if c == 20.0:
            base = s
        res["caps"]["%g" % c] = s
        print("%-8s %+9.2f %8.2f %7.2f %7.2f %8.1f %9.1f %8.1f"
              % ("%g%%" % c, s["excess_y_pp"], s["te_y_pct"], s["ir"], s["t"],
                 s["mdd_ex_pct"], tn, t3))
    for c in CAPS:
        s = res["caps"]["%g" % c]
        s["vs20_pp"] = s["excess_y_pp"] - base["excess_y_pp"]
        s["vs20_ir"] = s["ir"] - base["ir"]
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1, default=float))
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
