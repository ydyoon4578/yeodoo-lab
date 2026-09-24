# -*- coding: utf-8 -*-
"""build/eg_best_pdf.py — EG30(금융 판정 시점정확) 펀드 리포트 → 저장소 밖 C:/Project/fund_reports/

자료: data/_eg_best.json 의 EG_BASE 결과(PREREG-2026-09-24-EGBEST) 하나. 양식은 build/fund_report.py(공용 · 사용자 원칙
C:/Project/fund_reports/펀드전략_작성원칙.md) — 근본 이유 · 성과 · 위험 · 급락/급등 · 요약 · 방법론 · 부록(최근 매매 · 한계).

  python build/eg_best_pdf.py
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fund_report as FR               # noqa: E402

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "data", "_eg_best.json")
OUTDIR = os.environ.get("FUND_REPORT_DIR", r"C:\Project\fund_reports")
DATE = "2026-09-24"
EG_DEF = ("다음 해 투자증가율 예측값(Eg) — 시장가치÷자산(토빈 q) · 현금 기준 영업이익÷자산 · ROE 변화 셋에 과거 120개월 회귀계수 평균을 곱해 더한 값"
          " · 재무는 분기말 90일 뒤부터")


def meta_for(res):
    yl = res["yearly"]
    lost = [y for y, v in yl.items() if v["ex"] <= 0]
    crash = [e for e in res["episodes"] if e["kind"] == "급락"]
    return {
        "title": "S&P500 기대성장(Eg) 상위 30",
        "sub_extra": " · 금융 판정 시점정확",
        "reasons": [
            ("기전 — 투자 기반 자산가격", "현재 투자와 기대 수익성이 같다면, 앞으로 투자를 더 늘릴 것으로 예측되는 회사일수록 기대수익이 높다 — "
             "투자 기반 자산가격(q-이론)의 예측이다(Hou·Mo·Xue·Zhang 2021, <i>Review of Finance</i>). 기업은 새 투자의 한계 가치가 비용을 넘을 때 투자를 늘리므로, "
             "다음 해 투자 증가는 시장가치(토빈 q) · 현금 영업수익성(투자 여력) · ROE 개선(수익성 모멘텀)으로 미리 잡힌다. Eg 는 그 셋을 한 예측치로 합친 것이다."),
            ("증거", "원문 발표 뒤 공개 자료에서도 대형주 고Eg − 저Eg 가 월 +0.48%%(2006~2025 · t 2.34)로 살아 있고, 이 랩의 시점정확 검정(편출 종목 포함 · 금융 제외)에서 "
             "월 +0.67%%(t 2.44). 이 펀드 틀(바스켓 10%%)에서는 연 %s · IR %s · t %s." % (FR.pct(res["all"]["ann_ex"]), FR.num(res["all"]["ir"]), FR.num(res["all"]["t"]))),
            ("왜 대형 지수 펀드에 맞나", "S&amp;P500 ∪ NASDAQ100 대형주 안에서도 작동하고(대형주 중앙 이상에서 검증된 드문 신호), 분기에 한 번만 교체해 비용이 작다 "
             "(연 편도 NAV 대비 %s)." % FR.pct(res["nav_turn_oneway"] * 100, sign=False)),
            ("알아둘 성격", "Eg 상위는 수익성 높은 대형 성장주에 몰린다 — 그 몫(시총가중 지수와 월 상관 0.75~0.80)을 걷어 내도 월 +0.25%% 가 남지만, "
             "성장주가 약한 해와 급락장에서는 지수에 진다(진 해 %s · 급락 %d구간 중 %d구간 패). 이 약점은 초과수익과 한 몸이다(부록 B)."
             % (" · ".join(lost), len(crash), sum(e["ex"] <= 0 for e in crash))),
        ],
        "select": "Eg 상위 30개 회사",
        "weight": "바스켓 안은 시가총액 비례 · 한 회사 최대 20% (넘친 몫은 나머지에 비례 재배분)",
        "reb": "바스켓은 분기(3·6·9·12월 말) 교체 → 다음 3개월 보유 · 바스켓 비중은 매월 말 NAV 10%로 맞춤",
        "risk": "공매도 · 파생 · 차입 없음 · 바스켓 안 한 회사 최대 20% (NAV의 2%)",
        "evidence": "사전등록 PREREG-2026-09-23-EG(고Eg − 저Eg 월 +0.67%% · t 2.44) · PREREG-2026-09-24-EGBEST(펀드 틀 · 금융 판정 시점정확 · IR %s · t %s)"
                    % (FR.num(res["all"]["ir"]), FR.num(res["all"]["t"])),
        "universe": "그 월말 S&P500 ∪ NASDAQ100 구성종목(시점정확 · 편출 종목 포함) · 같은 회사의 두 종목은 하나로 · 금융은 Eg 가 없어 빠진다"
                    "(금융 판정은 그때의 GICS — 2023-03 전 결제 처리 회사는 비금융 · 2016 부동산 분리 전 리츠는 금융)",
        "steps": [("Eg", EG_DEF, "점수"), ("선정", "Eg 상위 30개 회사", "30개")],
        "limits": [
            "<b>백테스트다.</b> 120개월 · IR 표준오차 약 0.32 — 전체 IR %s 의 95%% 구간은 대략 %s ~ %s." % (FR.num(res["all"]["ir"]), FR.num(res["all"]["ir"] - 0.63), FR.num(res["all"]["ir"] + 0.63)),
            "<b>생존 편향.</b> 편출 종목 중 가격 자료가 없는 회사가 빠진다 — 2016-08 형성 때 명단 회사 524 중 가격이 선 회사 443. 초기일수록 비고, 빠진 쪽이 주로 인수합병으로 사라진 회사다.",
            "<b>금융 판정.</b> 월말 위키 S&amp;P500 표(과거 리비전)의 GICS 로 가른다 — 위키 편집 지연이 있다(부동산 분리가 표에 2개월 늦게 보인다). 표에 한 번도 없던 회사는 오늘 분류로 메운다. FIS 는 재무 자료(연간 영업현금흐름)가 FY2022 부터라 창 내내 빠진다.",
            "<b>시가총액은 배당조정 종가 × 주식수.</b> 과거 시총이 그 뒤 배당만큼 작게 잡혀 2016~2018 비중이 약 5% 흔들린다.",
            "<b>재무는 최신 제출본.</b> 뒤에 공시된 재작성이 과거 값에 들어간다(예: MSFT FY2017 ASC 606).",
            "<b>배당.</b> 바스켓은 배당 포함 · 벤치는 가격지수 — 초과의 일부(바스켓 배당률 × 10%, 연 약 0.1%p)는 배당이다.",
            "<b>집중.</b> 상위 3종목이 바스켓의 %s(NAV 의 %s) — 한 회사 20%% 상한에 붙어 있다. 대형 기술주 한두 개가 초과를 좌우한다."
            % (FR.pct(res["holdings"]["top3"], sign=False), FR.pct(res["holdings"]["top3"] * 0.1, sign=False)),
            "<b>하락장.</b> 성장주 쏠림과 바스켓 베타(약 1.2) 때문에 S&amp;P500 이 내린 39개월에 펀드가 평균 −0.06%p 뒤졌다(이긴 달 44%). "
            "업종 안 선별·업종 폭 · 바스켓 베타 상한 · 발행사 한도로 이를 막는 판을 사전등록해 검정했지만(PREREG-2026-09-24-EG30PLUS · 기각), "
            "같은 초과를 내주고 바스켓을 덜 드는 것보다 방어 효율이 낮았다 — 이 약점은 초과수익과 한 몸이다. 하락 방어가 더 중요하면 바스켓 비중을 줄이는 쪽이 싸다.",
        ],
    }


def main() -> int:
    J = json.load(io.open(SRC, encoding="utf-8"))
    res = J["results"]["EG_BASE"]
    os.makedirs(os.path.join(OUTDIR, "old"), exist_ok=True)
    pdf = os.path.join(OUTDIR, "펀드전략_EG30_%s.pdf" % DATE)
    FR.render(res, meta_for(res), DATE, pdf, os.path.join(OUTDIR, "old", "EG30_src.html"))
    print("→", pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
