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
import qg_cap                                   # noqa: E402

OUT = os.path.join(DATA, "_fund_card.json")

# 🚨 사용자 결정 2026-09-21 — *"근데 20%는 너무 커. 10%로 하자"*
#   사전등록_우량성장선별 §4 가 상한 메뉴(25·20·15·12·10%)를 **미리** 못박고
#   «고른 뒤에는 바꾸지 않는다» 고 적어 뒀다. 그 메뉴 안의 선택이라 사후 조정이 아니다.
#   ⚠ 등록서의 전제는 «법규·약관» 이었고 이번 사유는 **위험 선호**다. 사유가 다르다는
#     사실을 적어 둔다(build/qg_cap.py 머리말에도 같은 말이 있다).
#   ⚠ 상한을 바꾸면 `python build/qg_cap.py` 를 먼저 돌려 **앵커 둘**이 서는지 본다.
CAP = 10.0
PREV_CAP = 20.0

# 🚨 2026-09-21 정정 — 종전 문구는 «수익성·성장·재무건전성» 셋이라고 적었는데
#   산출물(02_우량성장_최소구성/qg_monthly.pkl)을 열어 보니 **점수는 두 축뿐**이다.
#   `score_raw = (roe_pct + eg_pct) / 2` 로 재현된다(가중치 최적화해도 0.50 · 잔차 2.5e-5).
#   **재무건전성에 해당하는 칸이 자료에 아예 없다.** 없는 축을 카드가 말하고 있었다.
# ⚠ `eg` 는 **이익성장이 아니라 기대투자성장**이다(2026-09-21 확인). 준비데이터 시트:
#   «다음 해 투자증가율 예측값. log q · Cop · dRoe 에 평균기울기를 곱해 만든다»
#   = q^5 모형의 Eg 팩터 구성(Hou·Mo·Xue·Zhang 2021). 애널리스트 컨센서스가 아니다.
RULE = ("S&P 500 안에서 **ROE 백분위와 기대투자성장(EG) 백분위를 반씩 평균**해 점수를 "
        "내고, 그 점수를 **6개월 이동평균**으로 눅인 뒤 상위 30종을 뽑는다. "
        "분기(3·6·9·12월) 말에 다시 고른다. 비중은 **지수비중 비례 + 한 회사 %g%% 상한**"
        "(넘치는 몫은 나머지에 비례 재배분)이고, 분기 중에는 표류를 그대로 둔다. "
        "금융업은 점수 대상에서 빼고, 같은 회사의 두 종목은 한 자리로 묶는다. "
        "리밸런스 거래에 왕복 25bp 를 물린다." % CAP)

# 오늘까지 사전등록·측정으로 확인된 «설계를 바꾸면 드는 비용»
COSTS = [
    ("종목을 빼면(최대 −N)", -0.80, "QGMAX", "기각"),
    ("신규 편입을 1개월 미루면", -0.26, "QGDELAY", "기각"),
    ("분기 대신 매월 리밸런스하면", -0.97, "qg_reb", "측정만"),
    ("한 계열 상한을 60%로 걸면", -1.64, "qg_max", "측정만"),
]


def main():
    # 🚨 상한 판을 카드의 정본 계열로 쓴다. 20% 원본은 아래 prev_design 에 남긴다.
    F, extra = qg_cap.series(CAP)
    P20 = fund_monthly()                        # 원본(20%) — 대조용
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
        "cap_pct": CAP,
        # 🚨 이 카드가 어느 상한 판인지, 그리고 이전 판이 무엇이었는지 나란히 둔다.
        #   없으면 «+8.16%p» 를 기억하는 사람이 이 카드를 보고 수가 줄었다고만 읽는다.
        "prev_design": {
            "cap_pct": PREV_CAP,
            "excess_y_pp": float(P20.mean() * 1200),
            "ir": float(P20.mean() * 1200 / (P20.std(ddof=1) * np.sqrt(12) * 100)),
            "t": float(P20.mean() / (P20.std(ddof=1) / np.sqrt(len(P20)))),
            "why": "사용자 결정 2026-09-21 — «20%는 너무 커. 10%로 하자». "
                   "사전등록 §4 의 상한 메뉴 안의 선택이고 «고른 뒤에는 바꾸지 않는다». "
                   "⚠ 등록서의 전제는 법규·약관이었고 이번 사유는 위험 선호다.",
            "traded": "집중 ↓(상위 3사 46.1%→29.6%) · 초과 −3.11%p · IR 0.99→0.65 · "
                      "t 3.44→2.27. ⚠ 추적오차는 8.26→7.77 로 거의 안 줄었다 — "
                      "«상한을 조여도 지수에서 벌어지는 폭은 줄지 않는다»(등록서 §4).",
        },
        "concentration": {"top3_pct": extra["top3_pct"], "turn_y_pct": extra["turn_y_pct"]},
        # ⚠ 아래 넷은 **20% 판에서 잰 값**이다. 상한을 바꿨다고 다시 재지 않았다.
        "costs_basis_cap_pct": PREV_CAP,
        "costs": [{"what": a, "pp_per_year": b, "src": c, "verdict": d} for a, b, c, d in COSTS],
        "limits": [
            "이 랩의 규칙들과 **잣대가 다르다**(펀드는 TR, 규칙은 PR 대비). 한 표에 섞지 말 것.",
            "초과의 섹터·종목 분해는 **폐기**했다 — 재구성 지수가 생존편향 덩어리다"
            "(AUDIT-2026-09-20-SHARES2 §5).",
            "시점정확 다리가 따로 없다. 바스켓 자체가 그때그때 편입명단에서 골라졌다면 "
            "생존편향이 없지만, 그것은 바스켓을 만든 쪽의 기록으로만 확인된다.",
            # 🚨 2026-09-21 — Novy-Marx (2025) 의 경고를 그대로 옮긴다. 이 한계는
            #   «아직 안 갈렸다» 이지 «틀렸다» 가 아니다. 가르려면 별도 등록이 필요하다.
            "🚨 **t 가 잡음 문턱 언저리로 내려왔다.** 랩의 다중검정 귀무분포에서 "
            "«잡음만으로 나오는 최고 t» 의 중앙값이 **2.267** 인데 이 판의 t 가 그 근처다"
            "(%g%% 판은 3.44 였다). 사전등록 §4 는 10%% 도 뒤바꾸기 검정을 통과한다고 "
            "적었지만(+1.06), **«지수를 이긴다» 가 더 약해진 것은 사실이다.** "
            "확정된 것은 «점수가 무작위가 아니다» 쪽이다." % PREV_CAP,
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
        # ⚠ regime_table 은 **20% 판 계열**로 구워졌다. 상한 판으로 다시 굽지 않았다.
        card["regime_basis_cap_pct"] = PREV_CAP
        card["regime_note"] = ("🚨 이 15칸은 **이전 설계(20% 상한) 계열**로 잰 것이다. "
                               "build/regime_table.py 가 fund_fit.fund_monthly() 를 읽기 "
                               "때문이다. 국면 «방향» 은 상한과 대체로 무관하겠지만 "
                               "**그것을 확인하지는 않았다** — 크기를 인용하지 말 것.")
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

    # 🚨 6팩터를 잰 **뒤에** 그 수로 한계를 적는다. 상수로 박아 두면 상한을 바꿨을 때
    #   본문은 10%% 판인데 인용된 수는 20%% 판인 모순이 생긴다(실제로 한 번 생겼다).
    f6 = card.get("factor6") or {}
    L = f6.get("loadings") or {}
    if L:
        def _bt(k):
            v = L.get(k) or {}
            return v.get("b"), v.get("t")
        hb, ht = _bt("hml"); rb, rt = _bt("rmw"); cb, ct = _bt("cma")
        card["limits"].append(
            "🚨 **«우량» 축이 수익성 하나로 환원될 수 있다.** Novy-Marx (2025) 는 "
            "ROE·이익안정성·저레버리지가 **수익성을 통제하면 유의성을 잃는다**고 "
            "보고한다(4팩터 알파 월 48bp · t 6.96). 이 판(%g%% 상한)의 6팩터에서도 "
            "RMW %+.3f(t %.2f) · CMA %+.3f(t %.2f) 로 둘 다 약한 반면 HML 은 "
            "**%+.3f(t %.2f)** 다 — 회귀가 «우량» 보다 **«성장»** 을 크게 본다. "
            "**알파가 우량에서 오는지 성장에서 오는지 이 카드로는 안 갈린다.**"
            % (CAP, rb, rt, cb, ct, hb, ht))
        a_t = f6.get("alpha_t")
        if a_t is not None and abs(a_t) < 2.0:
            card["limits"].append(
                "🚨 **6팩터 알파가 유의하지 않다 — 월 %+.3f%% (t %.2f).** "
                "%g%% 상한 판에서는 월 +0.403%% (t 2.41) 이었다. 상한을 조이면서 "
                "**«팩터로 설명 안 되는 몫» 이 통계적으로 사라졌다.** 남은 초과의 "
                "상당 부분이 성장·모멘텀 적재로 설명된다는 뜻이고, 그것은 "
                "**싸게 살 수 있는 노출**이다. 이 사실을 성적표와 함께 읽을 것."
                % (f6.get("alpha_m_pct"), a_t, PREV_CAP))

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
