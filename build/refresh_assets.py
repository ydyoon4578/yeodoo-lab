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
import csv, io, json, os, sys, urllib.request

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
    "SPY": ("주식", "S&P500"), "QQQ": ("주식", "나스닥100"), "IWM": ("주식", "러셀2000"),
    "EFA": ("주식", "선진국 除미국"), "EEM": ("주식", "신흥국"), "VEU": ("주식", "미국 외 전세계"),
    "TLT": ("채권", "장기국채 20년+"), "IEF": ("채권", "중기국채 7-10년"),
    "SHY": ("채권", "단기국채 1-3년"), "AGG": ("채권", "미국 종합채"), "BND": ("채권", "미국 종합채(뱅가드)"),
    "LQD": ("채권", "투자등급 회사채"), "HYG": ("채권", "하이일드"), "TIP": ("채권", "물가연동채"),
    "EMB": ("채권", "신흥국 국채"),
    "GLD": ("실물", "금"), "SLV": ("실물", "은"), "DBC": ("실물", "원자재 바스켓"),
    "USO": ("실물", "WTI 원유"), "UNG": ("실물", "천연가스"), "VNQ": ("실물", "미국 리츠"),
    "VIXY": ("변동성", "VIX 단기선물"), "VXZ": ("변동성", "VIX 중기선물"),
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
    "SPHB": ("스타일", "고베타"), "RSP": ("스타일", "동일가중 S&P500"),
    "XLK": ("섹터", "기술"), "XLF": ("섹터", "금융"), "XLE": ("섹터", "에너지"),
    "XLV": ("섹터", "헬스케어"), "XLI": ("섹터", "산업재"), "XLY": ("섹터", "경기소비"),
    "XLP": ("섹터", "필수소비"), "XLU": ("섹터", "유틸리티"), "XLB": ("섹터", "소재"),
    "XLRE": ("섹터", "부동산"), "XLC": ("섹터", "커뮤니케이션"),
    "^VIX": ("지수", "VIX"), "^VIX3M": ("지수", "VIX 3개월"), "^VIX9D": ("지수", "VIX 9일"),
    "^GSPC": ("지수", "S&P500 지수"), "^NDX": ("지수", "나스닥100 지수"),
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


def main() -> int:
    print("가격 %d종목 내려받는 중…" % len(TICK))
    df = yf.download(list(TICK), start=START, end=None, auto_adjust=True,
                     progress=False, threads=True)
    close = df["Close"]
    opens = df["Open"]
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
    raise SystemExit(main())
