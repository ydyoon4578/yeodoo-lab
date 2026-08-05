# -*- coding: utf-8 -*-
"""build/refresh_assets.py — 멀티에셋 패널(ETF·지수 + FRED 거시)을 data/assets.json 으로.

왜 만드는가.
  아카이브의 '못 돌린 것 38개' 중 상당수는 사실 **ETF 가격 몇 개만 있으면 되는 것**이었다.
  못 돌린 진짜 이유는 데이터가 세상에 없어서가 아니라, 이 저장소가 종목 패널만 들고 있었기
  때문이다. 그래서 자산 단위 패널을 따로 만든다 — 그러면 '없어서 못 한다'가 '돌려봤다'가 된다.

무료·무인증 경로만 쓴다.
  · 가격  : yfinance (일봉 종가·시가 — 시가는 오버나이트 계열에 필요하다)
  · 거시  : FRED fredgraph.csv (**API 키 불필요**). 키 경로는 계정 사고 이력이 있어 피한다.

한계는 여기 적어 결과와 함께 나간다.
  · ICE BofA 신용스프레드(BAMLH0A0HYM2 등)는 공개 CSV가 최근 3년만 준다(라이선스).
    장기 신용 국면이 필요한 규칙은 HYG/LQD 가격비를 프록시로 쓰고 그 사실을 명시한다.
  · ETF는 상장일 이후만 존재한다(DBMF 2019·KMLM 2020·VXX/VXZ 2018 재상장). 백테스트 구간이
    상품 나이에 묶이는 것은 데이터 문제가 아니라 **그 전략의 실제 제약**이다.

  python build/refresh_assets.py
"""
from __future__ import annotations
import csv, io, json, os, sys, time, urllib.request

import pandas as pd
import yfinance as yf
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "assets.json")
START = "2006-01-01"
UA = {"User-Agent": "yeodoo-lab globalkbam@gmail.com"}

# 티커 → (분류, 설명). 분류는 화면에서 묶어 보여주기 위한 것.
TICK = {
    "SPY": ("주식", "S&P 500"), "QQQ": ("주식", "NASDAQ 100"), "IWM": ("주식", "러셀2000"),
    # 다우 30 — 홈의 지수 줄에 세우려고 더했다(사용자 요청 2026-08-03). 가격가중이라
    # 나머지 셋(시총가중)과 성격이 다르지만, 사람들이 '시장'을 말할 때 여전히 부르는 이름이다.
    "DIA": ("주식", "다우존스 30"),
    "EFA": ("주식", "선진국 除미국"), "EEM": ("주식", "신흥국"), "VEU": ("주식", "미국 외 전세계"),
    "TLT": ("채권", "장기국채 20년+"), "IEF": ("채권", "중기국채 7-10년"),
    "SHY": ("채권", "단기국채 1-3년"), "AGG": ("채권", "미국 종합채"), "BND": ("채권", "미국 종합채(뱅가드)"),
    "LQD": ("채권", "투자등급 회사채"), "HYG": ("채권", "하이일드"), "TIP": ("채권", "물가연동채"),
    "EMB": ("채권", "신흥국 국채"),
    "GLD": ("실물", "금"), "SLV": ("실물", "은"), "DBC": ("실물", "원자재 바스켓"),
    "USO": ("실물", "WTI 원유"), "UNG": ("실물", "천연가스"), "VNQ": ("실물", "미국 리츠"),
    "VIXY": ("변동성", "VIX 단기선물"), "VXZ": ("변동성", "VIX 중기선물"),
    # 🚨 2026-08-06 추가 — 통화 축이 이 패널에 통째로 비어 있었다. 서로 독립인 두 기각문
    #   (hrp-allocation · min-variance-lw)이 **같은 것**을 지목했는데도 검정한 적이 없다:
    #   "성과의 정체가 배분 알고리즘이 아니라 UUP(달러) 평균 24.9~30.2% 배분이며,
    #    UUP 를 빼면 ΔSharpe 가 +0.057→−0.136 / +0.125→−0.094 로 **부호가 반전**한다."
    #   그 달러를 살 수 있는 티커가 패널에 없어서 그 축을 직접 잴 수 없었다.
    "UUP": ("통화", "달러 강세(DXY 롱)"), "UDN": ("통화", "달러 약세(DXY 숏)"),
    "VXX": ("변동성", "VIX 단기선물(iPath)"), "SVXY": ("변동성", "숏 VIX"),
    "MNA": ("이벤트", "합병차익 ETF"),
    "DBMF": ("대체", "매니지드 퓨처스"), "KMLM": ("대체", "매니지드 퓨처스(KFA)"),
    "BTC-USD": ("대체", "비트코인"),
    "MTUM": ("팩터", "모멘텀"), "VLUE": ("팩터", "밸류"), "QUAL": ("팩터", "퀄리티"),
    "USMV": ("팩터", "저변동성"), "SIZE": ("팩터", "소형"),
    # 스타일 축 보강(2026-07-27) — 위 iShares 5종은 MSCI 팩터라 **성장·배당·고베타·동일가중**
    #   축이 원천적으로 안 나온다. 같은 배치에 얹으므로 새 호출 경로는 없다.
    #   ⚠ 'S&P 스타일'과 'MSCI 팩터'는 산식이 다른 별개 계열이라 카테고리를 나눠 둔다.
    "RPG": ("스타일", "성장(S&P Pure Growth)"), "SDY": ("스타일", "배당성장"),
    "SPHB": ("스타일", "고베타"), "RSP": ("스타일", "동일가중 S&P 500"),
    # 가치 축을 S&P 로 맞춘다(사용자 결정 2026-07-28). 홈 스타일표의 '가치'가 VLUE(MSCI USA
    #   Enhanced Value)였는데 옆줄 '성장'은 S&P 계열이라 두 줄의 산식 계보가 어긋나 있었다.
    #   VLUE 는 macro·regime 의 'MSCI 팩터 5종' 패널이 계속 쓰므로 빼지 않고 그대로 둔다.
    "IVE": ("스타일", "가치(S&P 500 Value)"),
    "XLK": ("섹터", "기술"), "XLF": ("섹터", "금융"), "XLE": ("섹터", "에너지"),
    "XLV": ("섹터", "헬스케어"), "XLI": ("섹터", "산업재"), "XLY": ("섹터", "경기소비"),
    "XLP": ("섹터", "필수소비"), "XLU": ("섹터", "유틸리티"), "XLB": ("섹터", "소재"),
    "XLRE": ("섹터", "부동산"), "XLC": ("섹터", "커뮤니케이션"),
    "^VIX": ("지수", "VIX"), "^VIX3M": ("지수", "VIX 3개월"), "^VIX9D": ("지수", "VIX 9일"),
    "^GSPC": ("지수", "S&P 500 지수"), "^NDX": ("지수", "NASDAQ 100 지수"),
}
# 시가가 필요한 것만 따로 — 오버나이트 드리프트 계열(종가매수·시가매도)에 쓴다.
NEED_OPEN = ("SPY", "QQQ", "^GSPC", "^NDX", "IWM")
# 캐리를 잴 대상 — 분배금이 곧 캐리인 자산들. 금(GLD)은 분배가 없어 캐리 0이 정답이다.
CARRY_TICK = ("SPY", "EFA", "EEM", "IWM", "TLT", "IEF", "SHY", "LQD", "HYG", "EMB",
              "TIP", "AGG", "VNQ", "GLD", "DBC", "SLV")

FRED = {
    "DFII10": "10년 실질금리(TIPS)", "T10YIE": "10년 기대인플레",
    "DGS10": "10년 국채", "DGS2": "2년 국채", "T10Y2Y": "10-2 기간스프레드",
    # 수익률곡선을 '점 두 개'가 아니라 곡선으로 그리려면 만기가 더 필요하다(2026-07-27 추가).
    #   기존엔 2년·10년뿐이라 커브 형상도, 기간별 bp 변화도 낼 수 없었다. 셋 다 키 불필요 공개 CSV다.
    "DGS3MO": "3개월 국채", "DGS5": "5년 국채", "DGS30": "30년 국채",
    "VIXCLS": "VIX(종가)", "CPIAUCSL": "CPI(월)", "UNRATE": "실업률(월)",
    "USREC": "NBER 침체(월)", "DTWEXBGS": "달러지수", "DCOILWTICO": "WTI",
    "BAMLH0A0HYM2": "하이일드 OAS", "BAMLC0A0CM": "투자등급 OAS",
    # 🚨 2026-08-06 추가 — 경기순환 섹터 로테이션(A7) 재현에 쓴다.
    #   FEDFUNDS: Conover·Jensen·Johnson·Mercer(2008)의 '통화조건'(완화/긴축) 판정용.
    #     원논문은 연준 **재할인율** 변경 방향을 쓰는데 그 계열은 1990년대 이후 정책수단이
    #     아니게 됐다 — 같은 뜻의 현대 수단인 연방기금금리로 판정한다(사전등록에 적는다).
    #   INDPRO: Fidelity 4국면의 성장 축. ISM(NAPM)은 FRED 에서 404 다(유료 계열).
    #     A7 원문이 성장 동인을 "ISM·산업생산·GDP 추세"로 적었으므로 산업생산은
    #     **대체가 아니라 원문이 지목한 것**이다.
    "FEDFUNDS": "연방기금금리(월)", "INDPRO": "산업생산(월)",
}


def fred(sid: str):
    u = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=1990-01-01" % sid
    raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode()
    out = {}
    for r in list(csv.reader(io.StringIO(raw)))[1:]:
        if len(r) > 1 and r[1] not in (".", ""):
            try:
                out[r[0]] = float(r[1])
            except ValueError:
                pass
    return out


EXTRA = {}     # FRED 밖 공개 계열(연준 EBP 등)


def prev_tickers():
    """직전 빌드의 assets.json 에 있던 티커. '있다가 사라진 것'을 가려내는 기준선이다."""
    try:
        return set((json.load(io.open(OUT, encoding="utf-8")).get("px") or {}).keys())
    except Exception:
        return set()


def main() -> int:
    print("가격 %d종목 내려받는 중…" % len(TICK))
    df = yf.download(list(TICK), start=START, end=None, auto_adjust=True,
                     progress=False, threads=True)
    close = df["Close"]
    # ── 배치에서 흘린 티커를 개별로 다시 받는다 ────────────────────────────
    # yfinance 의 다중 티커 다운로드는 응답 일부를 무작위로 흘린다(실측 2026-07-27: IWM 1종).
    # 예전에는 그걸 "❌ 응답 없음" 한 줄 찍고 조용히 빼고 진행했다. 그 결과 하류의
    # market_board.py 완전성 게이트가 죽었고, 같은 잡의 **13F 재수집 결과까지 통째로
    # 폐기**됐다(커밋 단계가 스킵되므로). 값비싼 단계 앞에서 개별 재시도로 메운다.
    _fixed_open = {}          # 개별 재수집으로 되살린 시가 — 아래 opens 에 얹는다
    _want = [t for t in TICK if t not in close.columns or close[t].notna().sum() < 100]
    for t in _want:
        for _k in range(2):
            try:
                _d = yf.download(t, start=START, auto_adjust=True, progress=False, threads=False)
                _s = _d["Close"]
                if hasattr(_s, "columns"):
                    _s = _s[_s.columns[0]]
                if _s.notna().sum() >= 100:
                    close[t] = _s
                    # 🚨 2026-08-05 — 종전에는 종가만 되살리고 시가는 **재수집 이전의 원본 df**
                    #   에서 뽑았다(아래 opens = df["Open"]). 그래서 배치가 SPY/QQQ 를 짧게
                    #   흘리면 종가는 복구되고 시가만 빈 채로 통과했고, 오버나이트 계열
                    #   전략이 '수익률 0%' 곡선을 게시했다. 같은 응답에서 함께 되살린다.
                    try:
                        _o = _d["Open"]
                        if hasattr(_o, "columns"):
                            _o = _o[_o.columns[0]]
                        _fixed_open[t] = _o
                    except Exception:
                        pass
                    print("  ↻ %s 개별 재시도 성공(%d일)" % (t, int(_s.notna().sum())))
                    break
            except Exception:
                pass
            time.sleep(1.0 * (_k + 1))
        else:
            print("  ❌ %s 재시도 2회 실패" % t)
    opens = df["Open"]
    for _t, _o in _fixed_open.items():
        opens[_t] = _o

    # ── 종가 결측일 복구(60분봉) ──────────────────────────────────────────────
    # 야후는 일봉 집계만 깨지고 분봉은 멀쩡할 때가 있다(실측 2026-08-03: 전 종목 일봉의
    # 종가·고가·저가가 NaN 이고 시가·거래량만 남았는데 60분봉은 온전했다).
    # 이 파일은 그 경우 안전한 쪽으로 동작한다 — 아래 격자가 'SPY 종가 있는 날'만 쓰므로 그날이
    # 통째로 빠진다. 문제는 **이미 발표한 날이 사라진다**는 것이다. 08-03 을 담아 배포한 뒤
    # 다음 실행이 같은 결측을 만나면 패널 한가운데 구멍이 생긴다(이 잡은 전 구간을 매번 다시 받는다).
    # 되살릴 수 있으면 되살린다 — build/refresh_stocks.py 의 _recover_intraday 와 같은 방법이고
    # 검증 기록도 그쪽에 있다(깨지기 전 저장본과 14종 대조, 최대 괴리 0.0188%).
    # ⚠ 분봉은 최근 구간만 제공되므로 최근 7행만 본다. 정상일에는 _miss 가 비어 비용이 0이다.
    _miss = [d for d in close.index[-7:] if pd.isna(close["SPY"].get(d))]
    if _miss:
        print("  [종가결측] 일봉 종가 없는 최근 거래일 %d개 — 60분봉으로 복구 시도: %s"
              % (len(_miss), ", ".join(str(pd.Timestamp(d).date()) for d in _miss)))
        try:
            _h = yf.download(list(TICK), period="7d", interval="60m", auto_adjust=True,
                             progress=False, threads=True, group_by="ticker")
        except Exception as _e:
            _h = None
            print("  [종가결측] 분봉 수집 실패 — 그날은 격자에서 빠진다:", str(_e)[:70])
        if _h is not None and len(_h):
            _n = 0
            for _d in _miss:
                _dd = pd.Timestamp(_d).date()
                for _t in TICK:
                    try:
                        _s = _h[_t] if getattr(_h.columns, "nlevels", 1) > 1 else _h
                        _sub = _s[[x.date() == _dd for x in _s.index]].dropna(subset=["Close"])
                        if len(_sub) < 2:
                            continue
                        # 세션이 끝났다는 증거 — 12:30 ET 이후(13:00 조기폐장은 통과, 장중은 거른다).
                        _lt = _sub.index[-1]
                        if _lt.hour * 60 + _lt.minute < 12 * 60 + 30:
                            continue
                        if _t in close.columns and pd.isna(close.loc[_d, _t]):
                            close.loc[_d, _t] = float(_sub["Close"].iloc[-1]); _n += 1
                        if _t in opens.columns and pd.isna(opens.loc[_d, _t]):
                            opens.loc[_d, _t] = float(_sub["Open"].iloc[0])
                    except Exception:
                        continue
            print("  [종가결측] 60분봉 복구 %d칸" % _n)
            for _d in _miss:
                # SPY 를 못 되살리면 그날은 어차피 격자에 못 든다 — 조용히 넘어가지 않고 적는다.
                if pd.isna(close["SPY"].get(_d)):
                    print("  [종가결측] %s 는 SPY 복구 실패 — 그날을 버린다"
                          % str(pd.Timestamp(_d).date()))

    # ⚠ 격자는 **미국 거래일(SPY가 거래된 날)** 로 맞춘다. BTC-USD가 주말에도 거래되는 탓에
    #   그냥 두면 비거래일 1,350행이 섞여 들어와, 주식 규칙의 '20일'이 실제로는 14영업일이 된다.
    if "SPY" not in close.columns:
        print("❌ SPY가 없어 거래일 격자를 만들 수 없다"); return 1
    grid = close.index[close["SPY"].notna()]
    close = close.loc[grid]
    opens = opens.loc[grid]
    dates = [d.strftime("%Y-%m-%d") for d in close.index]

    px, op, meta = {}, {}, {}
    for t in TICK:
        if t not in close.columns:
            print("  ❌ %s 응답 없음" % t)
            continue
        s = close[t]
        if s.notna().sum() < 100:
            print("  ❌ %s 유효일 %d — 제외" % (t, int(s.notna().sum())))
            continue
        px[t] = [None if x != x else round(float(x), 4) for x in s.tolist()]
        v = s.dropna()
        meta[t] = {"cat": TICK[t][0], "desc": TICK[t][1],
                   "start": str(v.index[0].date()), "end": str(v.index[-1].date()),
                   "n": int(len(v))}
        if t in NEED_OPEN and t in opens.columns:
            op[t] = [None if x != x else round(float(x), 4) for x in opens[t].tolist()]

    # ── 있다가 사라진 티커는 여기서 멈춘다 ──────────────────────────────────
    # 왜 여기인가. 이 잡은 뒤에 13F 재수집·백테스트 재실행 같은 값비싼 단계를 줄줄이 달고 있고,
    # 마지막에 한 번만 커밋한다. 결손을 하류(market_board 완전성 게이트)에서 잡으면 그때는
    # 이미 앞 단계 산출물이 다 만들어진 뒤인데 커밋 단계가 스킵돼 **전부 폐기**된다
    # (실측 2026-07-27: IWM 1종이 빠져 같은 잡의 13F 재수집 결과가 통째로 버려졌다).
    # 그러니 값이 사라진 것을 안 순간, 아직 아무것도 낭비하지 않았을 때 멈춘다.
    #
    # '처음부터 없던 것'과 '있다가 사라진 것'은 다르다. 신규 상장·상장폐지로 원래 못 받는
    # 티커까지 막으면 패널을 늘릴 수 없으므로, 직전 빌드에 있었던 것만 대상으로 한다.
    # 🚨 2026-08-05 — 이 가드가 종가(px)만 봤다. 시가는 검사 대상이 아니라, 시가만 사라진
    #   경우가 그대로 통과했다. 오버나이트 계열은 시가가 없으면 '수익률 0%' 가 된다 —
    #   빈 것과 0인 것이 구별되지 않는 가장 나쁜 형태다.
    _op_thin = sorted(t for t in prev_tickers()
                      if t in op and sum(1 for x in op[t] if x is not None) < 100)
    if _op_thin:
        print("❌ 직전 빌드에 있던 티커의 시가가 100일 미만으로 얇다: %s" % ", ".join(_op_thin))
        print("   시가가 비면 오버나이트 계열이 '수익률 0%' 곡선을 낸다 — 중단한다.")
        return 1
    _gone = sorted(prev_tickers() - set(px))
    if _gone:
        print("❌ 직전 빌드에 있던 티커가 사라졌다: %s" % ", ".join(_gone))
        print("   개별 재시도까지 실패했다. 부분 패널을 쓰면 하류 지표가 조용히 달라지므로 중단한다.")
        print("   (일시적 응답 실패면 다시 돌리면 된다. 정말 뺄 티커면 TICK에서 지울 것.)")
        return 1

    # 초과채권프리미엄(EBP) — Gilchrist-Zakrajšek. 연준이 공개 CSV로 낸다(월간, 무인증).
    # FRED에는 없어서 '구할 수 없는 데이터'로 분류돼 있었는데, 실제로는 열린다.
    try:
        u = "https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv"
        raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
        rdr = list(csv.DictReader(io.StringIO(raw)))
        ebp = {}
        gz = {}
        for r in rdr:
            d = (r.get("date") or "").strip()
            if not d:
                continue
            try:
                ebp[d] = float(r["ebp"]); gz[d] = float(r["gz_spread"])
            except (KeyError, ValueError):
                pass
        if ebp:
            EXTRA["EBP"] = (ebp, "초과채권프리미엄(연준 GZ)")
            EXTRA["GZ_SPREAD"] = (gz, "GZ 신용스프레드(연준)")
            print("  %-14s %s ~ %s (%d)" % ("EBP", min(ebp), max(ebp), len(ebp)))
    except Exception as e:
        print("  ❌ EBP %s" % e)

    # ── 분배금 ── 크로스에셋 캐리의 재료. ETF를 그냥 들고 있을 때 가격 변동과 무관하게
    # 들어오는 현금이 캐리다. 조정 종가만으로는 이걸 분리할 수 없어 따로 받는다.
    print("분배금 내려받는 중…")
    div = {}
    for t in CARRY_TICK:
        try:
            d = yf.Ticker(t).dividends
        except Exception as e:
            print("  ❌ %s %s" % (t, e)); continue
        if d is None or len(d) == 0:
            div[t] = {}          # 분배 없음(예: GLD) — '못 받았다'와 구분해 빈 dict로 남긴다
            continue
        div[t] = {str(k.date()): round(float(v), 6) for k, v in d.items()
                  if str(k.date()) >= "2005-01-01"}
    print("  %d종목 (분배 있는 것 %d)" % (len(div), sum(1 for v in div.values() if v)))

    print("거시 %d계열 내려받는 중…" % len(FRED))
    mac, mmeta = {}, {}
    for k, (d, label) in EXTRA.items():
        ks = sorted(d)
        mac[k] = d
        mmeta[k] = {"label": label, "start": ks[0], "end": ks[-1], "n": len(ks)}
    for sid, label in FRED.items():
        try:
            d = fred(sid)
        except Exception as e:
            print("  ❌ %s %s" % (sid, e)); continue
        if not d:
            print("  ❌ %s 빈 응답" % sid); continue
        ks = sorted(d)
        mac[sid] = d
        mmeta[sid] = {"label": label, "start": ks[0], "end": ks[-1], "n": len(ks)}
        print("  %-14s %s ~ %s (%d)" % (sid, ks[0], ks[-1], len(ks)))

    doc = {
        "note": "멀티에셋 패널. 가격은 yfinance(배당·분할 조정 종가), 거시는 FRED 공개 CSV(키 불필요). "
                "아카이브의 '못 돌린 것'을 실제로 돌려보기 위한 입력이다.",
        "as_of": dates[-1], "start": dates[0], "n_days": len(dates),
        "dates": dates, "px": px, "open": op, "meta": meta, "div": div,
        "macro": mac, "macro_meta": mmeta,
        "limits": [
            "ICE BofA 신용스프레드(BAMLH0A0HYM2·BAMLC0A0CM)는 공개 CSV가 최근 3년만 준다(라이선스). "
            "장기 신용 국면이 필요한 규칙은 HYG/LQD 가격비를 프록시로 쓰고 그 사실을 함께 적는다.",
            "ETF는 상장일 이후만 존재한다(VXX·VXZ 2018 재상장 · DBMF 2019 · KMLM 2020). "
            "구간이 짧은 것은 데이터 결손이 아니라 그 상품의 실제 나이다.",
            "전부 조정 종가다. 배당 재투자를 가정하므로 실제 세후 수익과는 다르다.",
        ],
    }
    # ⚠ 한 줄짜리 3.5MB로 쓰면 주간 갱신마다 git이 **파일 전체를 새 블롭으로** 저장한다
    #   (한 줄이라 델타 압축이 안 먹는다). 연 52회면 이력만 180MB다. 그래서 티커/계열마다
    #   줄을 나눈다 — 꼬리 며칠만 바뀌면 바뀐 줄도 그만큼이라 이력이 얇게 쌓인다.
    def dump(o_):
        return json.dumps(o_, ensure_ascii=False, separators=(",", ":"))
    parts = []
    for k, v in doc.items():
        if k in ("px", "open", "macro", "div"):
            inner = ",\n".join(' %s:%s' % (dump(kk), dump(vv)) for kk, vv in v.items())
            parts.append('%s:{\n%s\n}' % (dump(k), inner))
        else:
            parts.append('%s:%s' % (dump(k), dump(v)))
    io.open(OUT, "w", encoding="utf-8").write("{\n" + ",\n".join(parts) + "\n}\n")
    print("\n자산 %d · 거시 %d · %s ~ %s (%d거래일) · %.1fMB"
          % (len(px), len(mac), dates[0], dates[-1], len(dates),
             os.path.getsize(OUT) / 1e6))
    return 0


if __name__ == "__main__":
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "자산 패널")
