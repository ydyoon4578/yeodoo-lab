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
   ⑤ 못 하는 것 · 알려진 한계

🚨 2026-09-21 — **6팩터 회귀를 카드에서 걷어냈다**(사용자 결정).
   *"왜 자꾸 이 전략에 6팩터를 꼽사리 끼는거야"* → *"아예 빼"*
   걷어낸 이유 셋. 전부 «틀렸다» 가 아니라 «이 카드에서 제 몫보다 크게 말했다» 다:
   ① **잣대가 어긋난다.** 좌변이 S&P 500 대비 **액티브 수익**인데 우변은 롱숏 팩터다.
     그래서 절편은 통상적 의미의 알파가 아니라 «틸트로 설명 안 되는 액티브 몫» 이다.
     그것을 «알파» 라고 적으면 읽는 사람이 다른 것을 본다.
   ② **R² 가 0.22 였다.** 분산의 78%가 설명 안 되는 회귀의 적재값으로
     «이 전략의 정체» 를 말하는 것은 과한 읽기다.
   ③ 🚨 **내가 증거를 부풀렸다.** 축 분해(수익성 단독 t 1.91 · 성장 단독 t 2.24)와
     HML 적재(−0.18)를 «두 독립적인 증거» 라고 썼는데 **같은 사실을 두 번 본 것**이다.
     ROE + 기대성장으로 상위 30 을 고르면 성장주 쪽에 서는 것은 **설계의 기계적 결과**다.
   ⚠ 이 전략을 설명하는 직접 증거는 따로 있다 — **축 분해 · 상한 메뉴 · 걸어가며 고르기 ·
     국면표.** 그 넷으로 결론이 다 서고, 6팩터를 빼도 아무 문장이 바뀌지 않는다.
   ⚠ 되살리려면: ff_daily.json 을 읽어 절편·적재를 재는 코드였고 git 이력에 있다.
     되살릴 때는 **잣대가 어긋난다는 사실을 카드에 같이 적을 것.**
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
CAP = 20.0
PREV_CAP = 10.0
# 🚨 2026-09-21 **되돌림** — 같은 날 20% → 10% 로 내렸다가 20% 로 돌아왔다.
#   ⚠ 되돌린 사유가 «성적이 더 좋아서» 면 그것은 사후 조정이다. 그래서 사유를 적는다:
#   **«상한을 조이면 위험이 준다» 는 전제가 틀렸다는 것이 확인됐다.**
#     10년 창으로 다시 재니 TE 8.66% → 8.21%(−5%) 인데 초과는 +8.85 → +5.04%p(−43%) 다.
#     MDD 도 −11.01% → −10.68% 로 사실상 같다. **위험은 거의 안 줄고 수익만 줄었다.**
#     내릴 때 내가 드린 표는 146개월짜리(TE 8.26→7.77)였고 10년 창에서는 그마저 더 작다.
#     **전제가 틀렸다는 발견이지 성적 추종이 아니다.**
#   ⚠ 그래도 **판단을 하루에 두 번 바꾼 것은 사실**이다. 사전등록 §4 는
#     «고른 뒤에는 바꾸지 않는다» 이고, 이 되돌림은 그 규약의 **예외**다. 그 사실을 남긴다.
#   ⚠ `build/qg_size.py` 의 CAP = 10.0 은 **안 바꾼다** — 얼린 사전등록 측정이고
#     결과문서(PREREG-2026-09-21-QGSIZE-RESULT)가 인용한 수가 10% 판이기 때문이다.

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
# 🚨 2026-09-21 — 네 줄이 **서로 다른 창에서 잰 값**인데 한 표에 나란히 있었다.
#   각 줄에 창·상한을 붙이고, 다시 잴 수 있는 것은 현행 판(20% · 10년)으로 다시 쟀다.
#   ⚠ 상한은 넷 다 **20%** 에서 쟀다 — 각 결과문서의 «확정안 재현 +8.16%p · IR 0.987»
#     검산이 그 증거다. **창만 다르다**(146개월 vs 지금 카드의 120개월).
#   (what, pp_per_year, src, verdict, basis, remeasured)
COSTS = [
    ("종목을 빼면(복권형 MAX5 배제)", -0.80, "QGMAX", "기각",
     "20% 상한 · 146개월(얼림)", False),
    ("신규 편입을 1개월 미루면", -0.26, "QGDELAY", "기각",
     "20% 상한 · 146개월(얼림)", False),
    ("분기 대신 매월 리밸런스하면", None, "qg_costs", "측정만",
     "20% 상한 · 10년(다시 잼)", True),
    ("한 계열 상한을 60%로 걸면", -1.64, "qg_max", "측정만",
     "20% 상한 · 146개월(얼림)", False),
]


def costs_remeasured():
    """build/qg_costs.py 가 다시 잰 값 — 비용 있음/없음 두 판."""
    try:
        return json.load(io.open(os.path.join(DATA, "_qg_costs.json"), encoding="utf-8"))
    except Exception:
        return None


def _costs_rows():
    """다시 잰 것은 새 값으로, 못 잰 것은 얼린 값으로. **어느 쪽인지 줄마다 적는다.**"""
    R = costs_remeasured() or {}
    rows = []
    for what, pp, src, verdict, basis, re_ in COSTS:
        row = {"what": what, "src": src, "verdict": verdict,
               "basis": basis, "remeasured": re_}
        if re_ and R.get("monthly_decomp"):
            d = R["monthly_decomp"]
            row["pp_per_year"] = d["total"]
            row["pp_per_year_nocost"] = d["design"]
            row["note"] = (
                "🚨 비용을 갈라 보면 **설계 효과 %+.2f%%p + 거래비용 %+.2f%%p** 다. "
                "회전이 연 %.0f%% → %.0f%% 로 느는데 손실의 대부분은 거래가 아니라 "
                "**신호가 나빠지는 쪽**이다 — 한 달마다 다시 고르면 6개월 평활이 "
                "잡아 주던 잡음을 도로 집어넣는다."
                % (d["design"], d["trading"],
                   R["runs"]["비용 25bp"]["quarterly"]["turn"],
                   R["runs"]["비용 25bp"]["monthly"]["turn"]))
        else:
            row["pp_per_year"] = pp
            row["note"] = "⚠ 이 클론에 입력이 없어 **다시 재지 못했다.** 얼린 값이다."
        rows.append(row)
    return rows


def cap_menu():
    """상한 메뉴(사전등록 §4) 를 확정 잣대로 재진술한 표 — build/qg_cap.py 가 굽는다."""
    try:
        m = json.load(io.open(os.path.join(DATA, "_qg_cap.json"), encoding="utf-8"))
    except Exception:
        return {"error": "data/_qg_cap.json 이 없다 — python build/qg_cap.py 를 돌릴 것"}
    return {"note": m.get("note"), "anchor_recon_gap_pp": m.get("recon_gap_pp"),
            "window": m.get("window"),
            "rows": [{"cap_pct": float(k), **v} for k, v in
                     sorted(m.get("caps", {}).items(), key=lambda x: -float(x[0]))]}


def main():
    # 🚨 상한 판을 카드의 정본 계열로 쓴다. 20% 원본은 아래 prev_design 에 남긴다.
    F, extra = qg_cap.series(CAP)
    # 🚨 «이전 설계» 계열은 PREV_CAP 판이어야 한다. 상한을 되돌리면서 이 줄이
    #   fund_monthly()(=원본 20%) 로 남아 있어 **prev 가 현행과 같은 판**이 됐었다.
    PPREV = qg_cap.series(PREV_CAP)[0]
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
            "excess_y_pp": float(PPREV.mean() * 1200),
            "ir": float(PPREV.mean() * 1200 / (PPREV.std(ddof=1) * np.sqrt(12) * 100)),
            "t": float(PPREV.mean() / (PPREV.std(ddof=1) / np.sqrt(len(PPREV)))),
            "why": "🚨 2026-09-21 하루에 두 번 움직였다. 20%→10%(«20%는 너무 커»)로 내렸다가 "
                   "20% 로 되돌렸다. **되돌린 사유는 성적이 아니라 전제가 틀렸다는 것이다** — "
                   "«상한을 조이면 위험이 준다» 를 10년 창으로 확인하니 TE 8.66→8.21%(−5%) · "
                   "MDD −11.01→−10.68% 로 위험은 거의 그대로인데 초과만 +8.85→+5.04%p(−43%) "
                   "줄었다. ⚠ 하루에 두 번 바꾼 것 자체는 사전등록 §4(«고른 뒤에는 바꾸지 "
                   "않는다»)의 예외이고, 그 사실을 여기 남긴다.",
            "traded": "10%로 내리면 — 얻는 것: 상위 3사 46.1%→29.6%. 치르는 것: 10년 창에서 "
                      "초과 −3.81%p · IR 1.02→0.61 · **t 3.23→1.94(2 아래)**. "
                      "⚠ 그런데 TE 는 8.66→8.21 로 5%만 줄고 MDD 는 −11.01→−10.68 로 "
                      "사실상 같다 — **집중도만 줄고 위험은 안 줄었다.**",
        },
        "concentration": {"top3_pct": extra["top3_pct"], "turn_y_pct": extra["turn_y_pct"]},
        # 🚨 고른 메뉴를 **카드가 들고 있는다.** 「왜 10% 인가」는 옆 칸들을 봐야 답이 된다.
        #   그리고 재 놓고 안 실으면 잰 적 없는 것이다(audit_unbuilt 의 규약).
        "cap_menu": cap_menu(),
        # ⚠ 아래 넷은 **20% 판에서 잰 값**이다. 상한을 바꿨다고 다시 재지 않았다.
        "costs_basis_cap_pct": PREV_CAP,
        "costs": _costs_rows(),
        "limits": [
            "이 랩의 규칙들과 **잣대가 다르다**(펀드는 TR, 규칙은 PR 대비). 한 표에 섞지 말 것.",
            "초과의 섹터·종목 분해는 **폐기**했다 — 재구성 지수가 생존편향 덩어리다"
            "(AUDIT-2026-09-20-SHARES2 §5).",
            "시점정확 다리가 따로 없다. 바스켓 자체가 그때그때 편입명단에서 골라졌다면 "
            "생존편향이 없지만, 그것은 바스켓을 만든 쪽의 기록으로만 확인된다.",
            "🚨 **t 가 잡음 문턱 언저리로 내려왔다.** 랩의 다중검정 귀무분포에서 "
            "«잡음만으로 나오는 최고 t» 의 중앙값이 **2.267** 인데 이 판의 t 가 그 근처다"
            "(%g%% 판은 3.44 였다). 사전등록 §4 는 10%% 도 뒤바꾸기 검정을 통과한다고 "
            "적었지만(+1.06), **«지수를 이긴다» 가 더 약해진 것은 사실이다.** "
            "확정된 것은 «점수가 무작위가 아니다» 쪽이다." % PREV_CAP,
            # 🚨 이 줄은 **직접 측정**으로만 적는다. 종전에는 같은 말을 6팩터 적재로
            #   한 번 더 해서 «두 독립적인 증거» 처럼 보이게 했는데, 그것은 같은 사실을
            #   두 번 본 것이었다(머리말 ③). 회귀를 걷어내면서 이 줄도 직접 증거로 고쳤다.
            "🚨 **«우량» 보다 «성장» 이 일한다.** 같은 엔진에서 축만 갈아 끼운 실측 — "
            "**기대성장 단독 +6.96%p(IR 0.72 · t 2.24)** vs **수익성 단독 +3.65%p"
            "(IR 0.53 · t 1.91)**. 수익성은 **혼자서는 유의하지 않다.** "
            "둘을 합치면 +8.63%p 로 둘 다보다 나으므로 두 축이 서로 다른 것을 잡고는 있다. "
            "⚠ 문헌도 같은 쪽을 경고한다 — Novy-Marx (2025) 는 수익성을 통제하면 "
            "ROE·이익안정성·저레버리지가 유의성을 잃는다고 보고한다. 다만 이 펀드에서 "
            "약한 쪽은 **수익성** 이고 남는 쪽은 **기대성장** 이라 방향이 반대다. "
            "«아직 안 갈렸다» 이지 «틀렸다» 가 아니고, 가르려면 별도 등록이 필요하다. "
            "⚠ 위 수치는 **옛 잣대**(같은 종목 지수 대비)라 축 사이의 상대 관계로만 읽을 것. "
            "출처는 정리_우량성장선별.md 「두 다리가 각각 얼마나 일하나」.",
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

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(card, ensure_ascii=False, indent=1, default=float) + "\n")

    print("=" * 72)
    print("  우량성장선별 30 — 전략 카드")
    print("=" * 72)
    print("  잣대   %s" % card["bench"])
    print("  창     %s ~ %s (%d개월)" % (card["window"]["start"], card["window"]["end"], n))
    print("  초과   월 %+.3f%% · 연 %+.2f%%p · TE %.2f%% · t %.2f · IR %.2f · 승률 %.1f%%"
          % (mu_m, mu_y, sd_y, t, ir, win))
    print("  집중   상위 3사 %.1f%% · 연 회전 %.1f%%"
          % (card["concentration"]["top3_pct"], card["concentration"]["turn_y_pct"]))
    print("\n  바꾸면 드는 비용 (오늘까지 잰 것)")
    for r in card["costs"]:
        v = r.get("pp_per_year")
        ex_ = ("" if r.get("pp_per_year_nocost") is None
               else "  (무비용 %+.2f)" % r["pp_per_year_nocost"])
        print("     %-28s %s  [%s]%s"
              % (r["what"], ("%+6.2f%%p/년" % v) if v is not None else "   —   ",
                 r["basis"], ex_))
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
