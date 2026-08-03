# -*- coding: utf-8 -*-
"""build/refresh_holdings.py — '현재 포트폴리오 구성' 생성 (클라우드 자체완결·무료 데이터만)
================================================================================
⚠ 데이터 정책: 이 파일은 **yfinance(무료 공개 가격)만** 사용한다. 사내 DB·라이선스 데이터
  (FactSet 추정치·SPG 팩터) 파생 보유(챔피언·단일팩터 top10·팩터모멘텀)는 공개하지 않는다 —
  라이선스 파생 데이터 재배포 + 배포 전략 IP 노출. 여기에 전략을 추가할 때 이 정책을 지킬 것.

무료 가격만으로 재현 가능한 전략의 최신 리밸런스 구성:
  · 크로스에셋 RP: 12 ETF 60일 역변동성 + 위험자산 12M 추세게이트 + vol타겟 10%(0.3~2.5x)
규칙은 랩 정본(combined_portfolio_deploy.rp_sleeve · strategy_backtests_gen)과 동일.
가격 소스만 yfinance라 사내 정본과 비중이 소수점에서 다를 수 있다(방법론 동일).
출력: data/strategy_holdings.json — explorer.html이 '현재 포트폴리오 구성' 표로 렌더.

⚠ 전략 키는 explorer.html D 배열의 "n"과 **완전히 같아야** 한다. validate_site.py가
  이 조인을 검사하고, 어긋나면 화면에 조용히 안 뜨므로 실패로 막는다. 전략을 추가할 때는
  explorer.html에 먼저 항목이 있는지 확인할 것.
  · 섹터 RP(11 SPDR 역변동성)는 explorer에 대응 항목이 없어 뺐다. 있는 것은 '섹터 모멘텀
    로테이션(Top 4)'으로 규칙이 다른 전략이다 — 이름만 맞춰 붙이면 안 된다.
  · 변동성 관리(NDX σ타겟 15%)도 뺐다. 이름이 비슷한 '동적 변동성 타깃팅'이 explorer 에
    있었지만 목표변동성 수치가 명시돼 있지 않아 같은 전략이라 단정할 수 없었고, 그 항목은
    2026-07-30 에 위험감축 계열을 정리하면서 삭제됐다 — 이제 대응 항목이 아예 없다.
  둘 다 백테스트·판정 기록을 갖춘 뒤 explorer에 올리고 여기에 되살릴 것.
"""
from __future__ import annotations
import os, json
import numpy as np, pandas as pd
import yfinance as yf
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "strategy_holdings.json")
ANN = 252

CORE = ["SPY", "QQQ", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "UUP", "HYG", "LQD", "VNQ"]
RISKY = {"SPY", "QQQ", "EFA", "EEM", "DBC", "VNQ"}
ETF_NAMES = {
    "SPY": "SPDR S&P 500 (미국 대형주)", "QQQ": "Invesco QQQ (NASDAQ 100)",
    "EFA": "iShares MSCI EAFE (선진국 ex-US)", "EEM": "iShares MSCI EM (신흥국)",
    "TLT": "iShares 20+Y 미국 장기국채", "IEF": "iShares 7-10Y 미국 중기국채",
    "GLD": "SPDR Gold (금)", "DBC": "Invesco DB Commodity (원자재)",
    "UUP": "Invesco 달러인덱스", "HYG": "iShares 하이일드 회사채",
    "LQD": "iShares 투자등급 회사채", "VNQ": "Vanguard 미국 리츠",
}


def fetch_close(tickers, start="2019-01-01"):
    df = yf.download(tickers, start=start, auto_adjust=True, progress=False)["Close"]
    if isinstance(df, pd.Series): df = df.to_frame(tickers[0])
    df = df.dropna(how="all")
    miss = [t for t in tickers if t not in df.columns or df[t].dropna().empty]
    if miss:
        raise SystemExit(f"yfinance 가격 결측: {miss} — 갱신 중단(이전본 유지)")
    return df


def complete_months(monthly_index, last_px_date):
    """마지막 거래일이 지난(완료된) 월말 라벨만 — 부분월 리밸 방지(하우스 규약)."""
    return [d for d in monthly_index if (d + pd.offsets.MonthEnd(0)) <= last_px_date]


def main():
    S = {}

    # ── 크로스에셋 RP (정본 rp_sleeve와 동일 규칙·가격만 yfinance) ──
    print("크로스에셋 RP…", flush=True)
    px = fetch_close(CORE)[CORE]
    px = px.reindex(pd.bdate_range(px.index.min(), px.index.max())).ffill().dropna(how="all")
    r = px.pct_change(); pxm = px.resample("ME").last(); last = px.index.max()
    rebals = complete_months(pxm.index, last)
    vol60 = r.rolling(60).std().resample("ME").last(); tr = pxm / pxm.shift(12) - 1
    d0 = rebals[-1]
    iv = (1 / vol60.loc[d0]).dropna(); g = tr.loc[d0].reindex(iv.index)
    keep = iv[(g > 0) | (~iv.index.isin(RISKY))]
    w = (keep / keep.sum()).reindex(CORE).fillna(0.0)
    # vol타겟 레버(정본과 동일): 최신 리밸 비중을 ffill 적용한 포트 수익의 30일 실현변동성
    W = {}
    for d in rebals:
        iv_ = (1 / vol60.loc[d]).dropna(); g_ = tr.loc[d].reindex(iv_.index)
        k_ = iv_[(g_ > 0) | (~iv_.index.isin(RISKY))]
        if len(k_): W[d] = k_ / k_.sum()
    Wdf = pd.DataFrame(W).T.reindex(columns=px.columns).fillna(0.0).sort_index()
    wd = Wdf.reindex(r.index, method="ffill").shift(1).fillna(0.0)
    port = (wd * r).sum(axis=1)
    lev = (0.10 / (port.rolling(30).std() * np.sqrt(ANN))).clip(0.3, 2.5)
    excluded = {t: f"12M 추세 {tr.loc[d0, t]*100:+.1f}% ≤ 0 → 추세게이트 제외(위험자산)"
                for t in CORE if t in RISKY and w[t] == 0}
    # 키 = explorer.html D 배열의 "n" 그대로(조인 검사 대상 — 한 글자도 다르면 화면에서 사라진다)
    S["크로스에셋 리스크패리티 (Cross-Asset Risk Parity · 12자산)"] = {
        "as_of": str(d0.date()), "kind": "assets",
        "note": "주식·채권·금·원자재 등 12개 자산을 '많이 흔들리는 자산은 적게, 덜 흔들리는 자산은 많이' 담습니다. "
                "최근 1년간 내리막인 위험자산은 제외하고, 전체 변동성이 연 10%가 되도록 투자 비율을 조절합니다. 매월 말 재계산.",
        "positions": sorted([{"t": t, "name": ETF_NAMES[t], "w": round(float(w[t]), 4)} for t in CORE],
                            key=lambda x: -x["w"]),
        "extra": {"vol타겟_레버리지": round(float(lev.dropna().iloc[-1]), 2), "목표변동성": "10%",
                  "추세게이트_제외": excluded if excluded else "없음(전 위험자산 추세 양호)"},
    }

    out = {"generated": pd.Timestamp.utcnow().strftime("%Y-%m-%d"),
           "note": "무료 공개 데이터(yfinance)로 재현 가능한 전략만 보유 구성을 공개합니다. "
                   "라이선스 데이터 파생 전략(챔피언·단일팩터 top10·팩터모멘텀)의 보유는 비공개.",
           "strategies": S}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {OUT} ({os.path.getsize(OUT)//1024}KB)")

    # 자기검증
    chk = json.load(open(OUT, encoding="utf-8"))
    errs = []
    for nm, st in chk["strategies"].items():
        for k in ("as_of", "kind", "note", "positions"):
            if k not in st: errs.append(f"{nm}: {k} 누락")
        ws = sum(p["w"] for p in st["positions"])
        if abs(ws - 1.0) > 0.01: errs.append(f"{nm}: 비중합 {ws:.4f}")
    if len(chk["strategies"]) != 1: errs.append(f"전략 수 {len(chk['strategies'])} ≠ 1")
    if errs:
        raise SystemExit("자기검증 실패: " + "; ".join(errs))
    print("자기검증 통과 ✓")
    for nm, st in chk["strategies"].items():
        top3 = ", ".join(f"{p['t']} {p['w']*100:.1f}%" for p in st["positions"][:3])
        print(f"  {nm[:30]:<32} as_of {st['as_of']}  top3: {top3}")


if __name__ == "__main__":
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "포트폴리오 구성")
