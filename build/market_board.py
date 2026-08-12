# -*- coding: utf-8 -*-
"""build/market_board.py — 다기간 성과 보드(섹터·스타일·금리·크레딧) → data/market_board.json

【왜 만드는가】
사이트에는 '지금 무엇이 가고 있나'를 다기간으로 보여주는 화면이 없었다.
  · 섹터  : sector.html은 **종목 브레드스**(200일선 위 비율)와 **레짐 조건부 과거 월평균**만 있다.
            정작 섹터 ETF가 최근 1주·1개월·1년에 얼마나 갔는지는 어디에도 없었다.
  · 스타일 : macro/regime의 팩터 표는 전부 '같은 국면이었던 달의 과거 평균'이다. 현재 성과가 아니다.
  · 금리  : regime의 금리 카드는 레벨 + **직전 관측 대비**만 보여준다. 기간별 bp 변화도,
            만기를 늘어놓은 커브 형상도 없었다(2년·10년 두 점뿐이었다).

【데이터】
전부 data/assets.json 하나에서 나온다 — 이미 커밋돼 있는 일별 패널(2006~, 50종 + FRED 18계열)이라
**추가 API 호출이 0회**다. 새 잡도, 새 키도 필요 없다.
곡선용 만기(3M·5Y·30Y)만 refresh_assets.py의 FRED 목록에 더했다(키 불필요 공개 CSV).

【규약】
· 숫자는 여기서 굽고 화면은 읽기만 한다(사이트 공통 규약).
· RSI는 **Wilder 평활**(α=1/n). 단순평균으로 계산하면 같은 지표가 값이 갈린다
  (검증: 섹터 11종에서 Wilder 평균오차 0.3 vs 단순 7.5).
· 금리는 %가 아니라 **bp**로 낸다 — 수익률과 같은 칸에 %로 적으면 뜻이 섞인다.
· 이 보드는 **상태 표시**다. '무엇을 사라'가 아니다. 특히 이 랩은 팩터 모멘텀을
  '자기 유니버스 대비 구별 불가'로 기각했으므로, 최근 잘 나간 스타일을 추천으로 읽히게 두면 자기모순이다.
  화면 문구는 그 선을 지킬 것.

  python build/market_board.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SRC = os.path.join(ROOT, "data", "assets.json")
OUT = os.path.join(ROOT, "data", "market_board.json")

# 기간 축 — 달력일 기준으로 잡고 '그 이하 마지막 거래일'을 쓴다(휴장 보정)
# 1D 는 달력 1일을 빼고 그 이하의 마지막 거래일을 찾는다 — 월요일이면 금요일이 잡힌다
# (_idx_on_or_before 가 처리한다). 즉 항상 '직전 거래일 대비'다.
# ⚠ 3Y·5Y 는 **누적**이다(연율 아님). 옆 칸들과 같은 뜻이어야 한 줄로 읽힌다 —
#   여기서만 연율로 바꾸면 같은 행의 1D~1Y 와 성격이 갈린다. 화면 각주가 그렇게 적는다.
# ⚠ 자료가 그만큼 없는 계열은 그 칸이 빈다(_idx_on_or_before 가 None 을 준다). 0 으로
#   채우지 않는다 — 없는 것을 지어내면 짧은 계열이 '수익 0'으로 보인다.
# ⚠ 5Y 는 걷었다(2026-08-12 사용자 요청 — 홈 표에서 5년 열을 빼고 그 자리에 12mf PER 을
#   넣었다). 여기서도 안 재는 이유는 화면이 안 쓰는 칸을 자료가 계속 나르지 않게 하려는 것이다.
HOR = [("1D", 1), ("1W", 7), ("1M", 30), ("3M", 91), ("6M", 181), ("12M", 365),
       ("3Y", 1095)]

SECTOR = [("XLK", "IT"), ("XLF", "금융"), ("XLV", "헬스케어"), ("XLY", "경기소비"),
          ("XLC", "커뮤니케이션"), ("XLI", "산업재"), ("XLP", "필수소비"), ("XLE", "에너지"),
          ("XLU", "유틸리티"), ("XLRE", "부동산"), ("XLB", "소재")]
# 지수 — 홈에 스타일표를 얹으면서 '무엇 대비인가'를 맨 위에 둘 자리가 필요해졌다(2026-07-28).
# STYLE 에 QQQ 를 끼워 넣지 않고 따로 두는 이유 — 그러면 macro.html 의 스타일표에 지수 행이
# 하나 더 생겨 '스타일 11종'이라던 그 화면의 셈이 조용히 달라진다. 축이 다르면 목록도 나눈다.
# 지수 줄. 다우(DIA)와 러셀2000(IWM)을 더했다(사용자 요청 2026-08-03) —
# '시장'을 말할 때 쓰이는 네 이름을 한자리에 둔다.
# ⚠ 다우는 **가격가중**이라 나머지 셋(시총가중)과 성격이 다르다. 같은 열에 서지만
#   같은 잣대는 아니고, 그 사실은 화면 툴팁이 말한다(index.html 의 IXNOTE).
# ⚠ IWM 은 style 목록에도 있다. 거기서는 ST_SKIP 이 걸러 왔고 지금도 그대로다 —
#   같은 티커가 한 표에 두 번 서지 않게.
INDEX = [("SPY", "S&P 500"), ("QQQ", "나스닥 100"),
         ("DIA", "다우존스 30"), ("IWM", "러셀 2000")]
# 스타일 — assets 패널에 있는 팩터 ETF. SPY는 '기준선'으로 같이 낸다(초과를 눈으로 재게).
#   가치는 IVE(iShares S&P 500 Value)다. 전에는 VLUE(MSCI USA Enhanced Value)였는데 옆줄
#   성장이 S&P 계열(RPG)이라 두 줄의 계보가 어긋나 있었다 — 가치를 S&P 로 맞췄다
#   (사용자 결정 2026-07-28). 이 표의 '가치' 행을 펼치면 나오는 구성종목도 index.html 의
#   ST_KEY 에서 val(MSCI) → spval(S&P U.S. Style) 로 함께 옮겼다.
# 🚨 2026-08-13 사용자 결정 — **8종으로 줄였다.** 종전 16종은 같은 축이 둘씩 겹쳐 있었다
#   (모멘텀 MTUM/SPMO · 성장 RPG/IVW · 저변동 USMV/SPLV · 고배당 VYM/SCHD).
#   겹치는 쌍에서는 **순자산이 큰 쪽**을 남겼다(실측 2026-08-13):
#     SPMO 21.0B > MTUM 25.3B ← ⚠ 이 쌍만 반대다. 사용자가 SPMO 를 택했다 —
#          초과수익 상관이 +0.629 로 낮고(둘이 실제로 다른 축이다) 보수도 0.13 < 0.15 다.
#     IVW 73.8B > RPG 2.0B · SPLV 7.2B > USMV 23.6B(사용자 선택) · SCHD 104.2B > VYM 99.2B
#   뺀 것: VYM·MTUM·USMV·PKW·RPG·RPV·SPHB·SIZE.
#     ⚠ SPHB 1.0B · SIZE 0.4B 는 순자산이 아주 작아 호가·청산 위험이 실제로 있던 줄이다.
# ⚠ 이름에서 (S&P) 를 뗀다 — 같은 축의 짝이 사라져 구별할 이유가 없어졌다.
#   SCHD 는 '고배당+질' 이었는데 VYM(고배당)이 빠졌으므로 그냥 '고배당' 이다.
# ⚠ SPY·IWM 은 남긴다. 화면이 그 둘을 스타일 묶음에서 빼 지수 줄로 올리고(ST_SKIP),
#   macro.html 전체 표는 러셀2000 줄로 쓴다 — 여기서 빼면 그 화면이 조용히 한 줄 잃는다.
STYLE = [("SPMO", "모멘텀"), ("IVW", "성장"), ("IVE", "가치"), ("QUAL", "퀄리티"),
         ("SPLV", "저변동"), ("SCHD", "고배당"), ("SDY", "배당성장"), ("RSP", "동일가중"),
         ("IWM", "소형(러셀2000)"), ("SPY", "S&P 500 (기준선)")]
MIN_52 = 252     # 52주 고점은 1년치가 있어야 낸다 — 신규 상장이 짧은 이력으로 가짜 값을 내지 않게
CREDIT = [("LQD", "투자등급 회사채"), ("HYG", "하이일드"), ("EMB", "신흥국 국채"),
          ("TIP", "물가연동국채")]
TENOR = [("DGS3MO", "3개월"), ("DGS2", "2년"), ("DGS5", "5년"), ("DGS10", "10년"), ("DGS30", "30년")]


def _base_dates(last: str):
    """기간별 기준일(달력일 차감) + YTD(전년말)."""
    d0 = dt.date.fromisoformat(last)
    out = {k: (d0 - dt.timedelta(days=n)).isoformat() for k, n in HOR}
    out["YTD"] = f"{d0.year - 1}-12-31"
    return out


def _idx_on_or_before(dates, target):
    lo, hi = 0, len(dates) - 1
    if dates[0] > target:
        return None
    while lo < hi:
        m = (lo + hi + 1) // 2
        if dates[m] <= target:
            lo = m
        else:
            hi = m - 1
    return lo


def _rsi_wilder(s, n=14):
    """Wilder 평활 RSI. 사이트 안에서 산식이 갈리지 않게 여기 한 곳에만 둔다."""
    s = [v for v in s if v is not None]
    if len(s) < n + 1:
        return None
    ch = [s[i] - s[i - 1] for i in range(1, len(s))]
    ag = sum(max(c, 0) for c in ch[:n]) / n
    al = sum(max(-c, 0) for c in ch[:n]) / n
    for c in ch[n:]:
        ag = (ag * (n - 1) + max(c, 0)) / n
        al = (al * (n - 1) + max(-c, 0)) / n
    if al == 0:
        return 100.0
    return round(100 - 100 / (1 + ag / al), 1)


def _price_row(px, dates, bidx, tkr, label):
    s = px.get(tkr)
    if not s:
        return None
    cur = s[-1]
    if cur is None:
        return None
    r = {}
    for k, i in bidx.items():
        a = s[i] if i is not None else None
        r[k] = None if (a is None or a == 0) else round((cur / a - 1) * 100, 2)
    # 52주 고점은 1년치가 찼을 때만 낸다. 상장 6개월짜리에 '고점 대비 −2%'를 찍으면
    #   숫자는 나오는데 뜻이 없다(신규 ETF가 늘 고점 근처로 보인다).
    win = [v for v in s[-MIN_52:] if v is not None]
    return {"t": tkr, "n": label, "r": r,
            # 🚨 2026-08-12 — px 를 싣는다. 홈 표에 「주가」 열이 있고 열 설명이 "섹터·지수·
            #   스타일 ETF 행만 값이 있다"고 **주장**하는데, 이 파일이 px 를 아예 안 내보내
            #   전 줄이 '·' 였다. 열이 하는 말과 열이 보이는 것이 정반대였다.
            #   cur 은 위에서 이미 구해 놓은 값이다 — 새로 계산하는 것이 없다.
            # ⚠ data/assets.json 의 px 는 배당조정 종가다. 열 설명의 '(배당조정)'과 맞다 —
            #   원주가로 바꾸려면 열 설명도 같이 고칠 것.
            "px": round(cur, 2),
            "off52": (round((cur / max(win) - 1) * 100, 1) if len(win) >= MIN_52 else None),
            "rsi": _rsi_wilder(s),
            "n_obs": len([v for v in s if v is not None])}


def _at(series: dict, target: str):
    ks = [k for k in series if k <= target and series[k] is not None]
    return series[max(ks)] if ks else None


def _rate_row(macro, last, bases, sid, label):
    s = macro.get(sid)
    if not s:
        return None
    cur = _at(s, last)
    if cur is None:
        return None
    r = {}
    for k, d in bases.items():
        b = _at(s, d)
        r[k] = None if b is None else round((cur - b) * 100)   # bp
    return {"t": sid, "n": label, "lv": round(cur, 2), "bp": r}


def build() -> dict:
    A = json.load(io.open(SRC, encoding="utf-8"))
    dates, px, macro, last = A["dates"], A["px"], A.get("macro") or {}, A["as_of"]
    bases = _base_dates(last)
    bidx = {k: _idx_on_or_before(dates, d) for k, d in bases.items()}

    def rows(spec, what):
        out = [x for x in (_price_row(px, dates, bidx, t, n) for t, n in spec) if x]
        # 완전성 게이트 — yfinance 부분응답으로 한 줄이 사라져도 표는 멀쩡해 보인다.
        #   조용히 빠지느니 갱신을 세운다(refresh_stocks의 필드 게이트와 같은 결).
        miss = sorted({t for t, _ in spec} - {x["t"] for x in out})
        if miss:
            raise SystemExit(f"[market_board] {what} 결손 {miss} — 자산 패널에 그 계열이 없다. "
                             "갱신 중단(이전본 유지). refresh_assets.py의 TICK을 확인할 것")
        return out

    tenors = [x for x in (_rate_row(macro, last, bases, s, n) for s, n in TENOR) if x]
    t_miss = sorted({s for s, _ in TENOR} - {x["t"] for x in tenors})
    if t_miss:
        raise SystemExit(f"[market_board] 만기 결손 {t_miss} — 커브가 반쪽이 된다. "
                         "refresh_assets.py의 FRED 목록을 확인할 것")
    # ⚠ 금리는 패널 기준일보다 하루 늦다(FRED 국채는 T-1 게시). 최상단 as_of를 그대로 쓰면
    #   '없는 날의 금리'를 주장하게 된다 — 블록 자체의 기준일을 따로 싣는다.
    rates_asof = max((max((d for d, v in (macro.get(s) or {}).items()
                           if v is not None and d <= last), default="")
                      for s, _ in TENOR), default="") or None
    by = {x["t"]: x["lv"] for x in tenors}
    curve = {}
    if "DGS10" in by and "DGS2" in by:
        curve["s10_2"] = round((by["DGS10"] - by["DGS2"]) * 100)
    if "DGS10" in by and "DGS3MO" in by:
        curve["s10_3m"] = round((by["DGS10"] - by["DGS3MO"]) * 100)

    return {
        "note": "다기간 성과 보드 — data/assets.json 하나에서 계산한다(추가 API 호출 없음). "
                "수익률은 %, 금리는 bp. RSI는 Wilder(14). 52H는 최근 252거래일 고점 대비. "
                "상태 표시일 뿐 매수 신호가 아니다.",
        "as_of": last,
        "basis": {"horizons": list(bases), "base_dates": {k: dates[v] if v is not None else None
                                                          for k, v in bidx.items()},
                  "rsi": "Wilder(14)", "off52": "최근 252거래일 종가 고점 대비 %"},
        "index": rows(INDEX, "지수"),
        "sector": rows(SECTOR, "섹터"),
        "style": rows(STYLE, "스타일"),
        "credit": rows(CREDIT, "크레딧"),
        "rates": {"as_of": rates_asof, "tenor": tenors, "curve": curve or None},
    }


if __name__ == "__main__":
    doc = build()
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    n = {k: len(doc[k]) for k in ("index", "sector", "style", "credit")}
    print(f"→ {OUT}")
    print(f"  기준일 {doc['as_of']} · 지수 {n['index']} · 섹터 {n['sector']} · 스타일 {n['style']} · "
          f"크레딧 {n['credit']} · 만기 {len(doc['rates']['tenor'])}")
    print("  기준일자: " + " · ".join(f"{k} {v}" for k, v in doc["basis"]["base_dates"].items()))
