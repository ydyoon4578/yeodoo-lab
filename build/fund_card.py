# -*- coding: utf-8 -*-
"""build/fund_card.py — 우량성장선별 30 을 **랩의 전략 하나로** 등재한다.

왜 이것이 필요한가
   펀드는 랩의 세 목록(살아 있는 189 · 은퇴 13 · 돌렸지만 게시 안 됨 214) 어디에도
   없었다. 규칙 엔진(`tech_backtest.py`)이 만든 것이 아니라 밖에서 만든 바스켓이고,
   잣대도 다르기 때문이다(공식 S&P 500 **TR** 대비 · 규칙들은 PR 대비).
   그래서 «랩에 전략이 몇 개냐» 에 답할 때 펀드가 빠져 있었다.

   **목록에 없으면 비교도 안 되고 비교가 안 되면 관리도 안 된다.**
   그래서 규칙 항목과 같은 모양의 카드를 따로 굽는다.

   ⚠ 규칙 목록에 **섞지 않는다.** 잣대가 다른 것을 한 표에 넣으면 그 표가 거짓말을 한다.
     별도 파일(`data/_fund_card.json`)로 두고, 문서에서 나란히 읽는다.

담는 것
   ① 규칙 문장 · 운용 제원        ② 성적(확정 잣대 B = 바스켓 TR − S&P 500 TR)
   ③ 국면별 성적(15칸)           ④ 오늘까지 측정된 «바꾸면 드는 비용» 네 가지
   ⑤ 6팩터 회귀로 본 스타일       ⑥ 못 하는 것 · 알려진 한계
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fund_fit import fund_monthly, ols          # noqa: E402

OUT = os.path.join(DATA, "_fund_card.json")

RULE = ("S&P 500 안에서 **수익성·성장·재무건전성**으로 점수를 내 상위 30종을 뽑고, "
        "분기(3·6·9·12월) 말에 다시 고른다. 목표비중으로 담고 분기 중에는 표류를 "
        "그대로 둔다. 리밸런스 거래에 왕복 25bp 를 물린다.")

# 오늘까지 사전등록·측정으로 확인된 «설계를 바꾸면 드는 비용»
COSTS = [
    ("종목을 빼면(최대 −N)", -0.80, "QGMAX", "기각"),
    ("신규 편입을 1개월 미루면", -0.26, "QGDELAY", "기각"),
    ("분기 대신 매월 리밸런스하면", -0.97, "qg_reb", "측정만"),
    ("한 계열 상한을 60%로 걸면", -1.64, "qg_max", "측정만"),
]


def main():
    F = fund_monthly()
    n = len(F)
    mu_m, mu_y = float(F.mean() * 100), float(F.mean() * 1200)
    sd_y = float(F.std(ddof=1) * np.sqrt(12) * 100)
    t = float(F.mean() / (F.std(ddof=1) / np.sqrt(n)))
    ir = mu_y / sd_y if sd_y else np.nan
    win = float((F > 0).mean() * 100)

    card = {
        "sid": "qg30",
        "name": "우량성장선별 30",
        "family": "바스켓(펀드)",
        "role": "수익엔진",
        "kind": "basket",
        "rule": RULE,
        "bench": "S&P 500 총수익(TR · 배당 포함)",
        "basis_note": ("확정 잣대는 **B = 바스켓 TR − S&P 500 TR** 이다. "
                       "예전에 쓰던 잣대 C(+9.98%p)는 쓰지 않는다 — 지수 쪽 배당이 "
                       "빠져 있어 펀드에 유리하게 기울어 있었다."),
        "window": {"start": str(F.index[0]), "end": str(F.index[-1]), "n_months": n},
        "perf": {"excess_m_pct": mu_m, "excess_y_pp": mu_y, "te_y_pct": sd_y,
                 "t": t, "ir": ir, "win_rate_pct": win},
        "costs": [{"what": a, "pp_per_year": b, "src": c, "verdict": d} for a, b, c, d in COSTS],
        "limits": [
            "이 랩의 규칙들과 **잣대가 다르다**(펀드는 TR, 규칙은 PR 대비). 한 표에 섞지 말 것.",
            "초과의 섹터·종목 분해는 **폐기**했다 — 재구성 지수가 생존편향 덩어리다"
            "(AUDIT-2026-09-20-SHARES2 §5).",
            "시점정확 다리가 따로 없다. 바스켓 자체가 그때그때 편입명단에서 골라졌다면 "
            "생존편향이 없지만, 그것은 바스켓을 만든 쪽의 기록으로만 확인된다.",
        ],
    }

    # 국면 — regime_table 이 이미 펀드 행을 갖고 있다
    try:
        RT = json.load(io.open(os.path.join(DATA, "_regime_table.json"), encoding="utf-8"))
        reg = {}
        for ax, rows in (RT.get("table") or {}).items():
            for nm, cells in rows.items():
                if nm.startswith("펀드"):
                    reg[ax] = cells
        card["regime"] = reg
    except Exception:
        card["regime"] = {}

    # 6팩터 — 스타일로 얼마나 설명되나
    try:
        ff = json.load(io.open(os.path.join(DATA, "ff_daily.json"), encoding="utf-8"))
        FD = pd.DataFrame(ff["series"], index=pd.to_datetime(ff["dates"])) / 100.0
        MF = (1 + FD).groupby(FD.index.to_period("M")).prod() - 1
        cols = ["mkt_rf", "smb", "hml", "rmw", "cma", "mom"]
        j = MF.index.intersection(F.index)
        y, Xf = F.reindex(j).to_numpy(), MF.reindex(j)[cols].to_numpy()
        X = np.column_stack([np.ones(len(j)), Xf])
        bh, *_ = np.linalg.lstsq(X, y, rcond=None)
        e = y - X @ bh
        s2 = float(e @ e) / (len(y) - X.shape[1])
        se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * s2))
        ss = float(((y - y.mean()) ** 2).sum())
        card["factor6"] = {
            "n_months": int(len(j)),
            "alpha_m_pct": float(bh[0] * 100), "alpha_t": float(bh[0] / se[0]),
            "loadings": {c: {"b": float(bh[i + 1]), "t": float(bh[i + 1] / se[i + 1])}
                         for i, c in enumerate(cols)},
            "r2": 1 - float(e @ e) / ss if ss else None,
        }
    except Exception as ex:
        card["factor6"] = {"error": str(ex)}

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(card, ensure_ascii=False, indent=1, default=float) + "\n")

    print("=" * 72)
    print("  우량성장선별 30 — 전략 카드")
    print("=" * 72)
    print("  잣대   %s" % card["bench"])
    print("  창     %s ~ %s (%d개월)" % (card["window"]["start"], card["window"]["end"], n))
    print("  초과   월 %+.3f%% · 연 %+.2f%%p · TE %.2f%% · t %.2f · IR %.2f · 승률 %.1f%%"
          % (mu_m, mu_y, sd_y, t, ir, win))
    f6 = card["factor6"]
    if "alpha_m_pct" in f6:
        print("  6팩터  알파 월 %+.3f%% (t %.2f) · R² %.2f"
              % (f6["alpha_m_pct"], f6["alpha_t"], f6["r2"]))
        print("         " + " · ".join("%s %+.2f(t%.1f)" % (k, v["b"], v["t"])
                                       for k, v in f6["loadings"].items()))
    print("\n  바꾸면 드는 비용 (오늘까지 잰 것)")
    for a, b, c, d in COSTS:
        print("     %-26s %+6.2f%%p/년   [%s · %s]" % (a, b, c, d))
    if card["regime"]:
        print("\n  국면별 초과 (월 %) — 열다섯 칸")
        for ax, cells in card["regime"].items():
            print("     %-14s 하위 %+.3f · 중간 %+.3f · 상위 %+.3f"
                  % (ax, cells.get("low", np.nan), cells.get("mid", np.nan),
                     cells.get("high", np.nan)))
    print("\n→ %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
