# -*- coding: utf-8 -*-
"""홈 전용 초소형 요약(data/home_reco.json) — **홈이 읽는 유일한 대형 데이터 대체물**.

홈은 stocks.json(raw 691KB · gz 199KB)·rotation_pool.json·strategy_backtests.json 을 절대 fetch하지
않는다. 대신 빌드가 필요한 값만 여기에 구워 1~2KB로 만든다.

담는 것
  ① 스윙 타점 상위 8+8 — 확정/잠정 지위 포함
  ② 확정·잠정 **카운트** — '오늘 표시된 16건이 전부 잠정'인데 카드가 "확정 스윙 타점"을 내세우는
     불일치가 실제로 있었다. 숫자를 함께 실어 화면이 스스로 드러내게 한다.
"""
from __future__ import annotations
import io, json, os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

# GICS 영문 섹터는 홈의 좁은 행에서 잘린다 — 짧은 한글로(stocks.html의 SECKO와 같은 표기)
SECKO = {"Information Technology": "IT", "Health Care": "헬스케어", "Financials": "금융",
         "Consumer Discretionary": "경기소비", "Consumer Staples": "필수소비", "Industrials": "산업재",
         "Communication Services": "커뮤니케이션", "Energy": "에너지", "Utilities": "유틸리티",
         "Real Estate": "부동산", "Materials": "소재"}
WIN = 10          # 최근 N거래일 내 타점만 홈에 노출
TOP = 8


def _lastmk(s, key):
    a = s.get(key) or []
    return a[-1] if a else -1


def _reco(stocks, dates, conf_key, prov_key):
    """확정(conf)·잠정(prov) 중 최신 타점을 취한다. prov가 더 최신이면 아직 이동 가능."""
    N = len(dates)
    c = []
    for s in stocks:
        mc, mp = _lastmk(s, conf_key), _lastmk(s, prov_key)
        m = max(mc, mp)
        if m < 0 or (N - 1 - m) > WIN:
            continue
        c.append((m, mp > mc, s))
    c.sort(key=lambda x: -x[0])
    rows = [{"t": s["t"], "name": (s.get("name") or "")[:16], "dt": dates[m][5:], "ago": N - 1 - m,
             "sec": SECKO.get(s.get("sector") or "", (s.get("sector") or "")[:6]),
             **({"prov": 1} if pv else {})} for m, pv, s in c[:TOP]]
    n_prov = sum(1 for _, pv, _ in c if pv)
    return rows, len(c), len(c) - n_prov, n_prov      # 목록 · 전체 · 확정 · 잠정


# SIC 대분류(2자리) 한글 이름. **4자리가 아니라 2자리로 묶는 이유** —
#   실측(2026-08-02, 유니버스 518종): 4자리는 183그룹인데 83그룹이 1종목이고, 5종 이상인
#   그룹이 24개뿐이라 커버가 240/518(46%)이다. '산업 평균'이 종목 하나인 줄이 절반을 넘는다.
#   3자리는 132그룹·커버 330(64%), 2자리는 54그룹인데 5종 이상이 27개로 가장 많고
#   커버가 450/518(87%)이다. 그룹 수는 4자리와 비슷한데 통계가 서는 유일한 자릿수다.
# ⚠ 이름은 SIC 공식 대분류 제목을 옮긴 것이다. data/industry.json 은 4자리 설명만 들고
#   있어(2자리 제목이 없다) 여기 적는다 — 없는 코드는 'SIC nn' 으로 나간다(조용히 빠지지 않게).
SIC2 = {
    "01": "농업", "10": "금속광업", "13": "석유·가스 채굴", "14": "비금속 광물",
    "15": "건축 시공", "16": "토목 건설", "17": "전문 건설", "20": "식품", "21": "담배",
    "23": "의류 제조", "26": "제지", "27": "인쇄·출판", "28": "화학·제약", "29": "정유",
    "30": "고무·플라스틱", "31": "가죽", "32": "요업·시멘트", "33": "1차 금속",
    "34": "금속 가공", "35": "기계·컴퓨터장비", "36": "전자·전기장비", "37": "운송장비",
    "38": "계측·의료기기", "39": "기타 제조", "40": "철도", "42": "화물운송·창고",
    "44": "해운", "45": "항공운송", "47": "운송 서비스", "48": "통신",
    "49": "전기·가스·수도", "50": "도매(내구재)", "51": "도매(비내구재)",
    "52": "소매(건자재)", "53": "소매(종합)", "54": "소매(식품)", "55": "소매(자동차·주유)",
    "56": "소매(의류)", "57": "소매(가구·가전)", "58": "외식", "59": "소매(기타)",
    "60": "은행", "61": "여신금융", "62": "증권·자산운용", "63": "보험", "64": "보험중개",
    "65": "부동산", "67": "리츠·지주", "70": "호텔·숙박", "73": "사업서비스(SW·IT)",
    "78": "영화·영상", "79": "레저·엔터", "80": "의료서비스", "87": "엔지니어링·컨설팅",
}
IND_MIN = 5        # 이보다 적은 그룹은 '산업 평균'이라 부를 수 없다 — 종목 몇 개의 평균이다
# ⚠ 기간 규칙은 build/market_board.py 의 HOR 와 **같아야 한다.** 홈에서 섹터 카드 바로
#   아래에 산업 카드가 붙으므로, 두 카드의 '1개월'이 다른 날을 가리키면 나란히 못 읽는다.
#   그쪽은 달력일 차감 후 그 날짜 이하의 마지막 관측을 쓴다(_base_dates + _at) — 같은 규칙이다.
IND_HOR = [("1M", 30), ("3M", 91)]


def _industry(stocks, dates, root):
    """SIC 대분류별 동일가중 수익률 + 200일선 위 비율.

    섹터(11개)와 종목(518개) 사이가 홈에서 비어 있었다(사용자 요청 2026-08-02
    "산업 단위로 더 쪼개줘"). 섹터 카드와 같은 형태로 한 단 아래를 본다.

    가격은 data/sd/*.json 에서 읽는다(518파일 · 실측 1.1초). stocks.json 에는 가격이 없고,
    홈이 그 원본을 받을 수는 없으므로 여기서 정수 몇 개로 접어 넣는다 — 이 파일의 취지다.
    """
    ind_p = os.path.join(root, "data", "industry.json")
    if not os.path.exists(ind_p):
        return []
    co = (json.load(io.open(ind_p, encoding="utf-8")) or {}).get("co") or {}
    if not co:
        return []
    # 기간별 기준 인덱스 — market_board 와 같은 규칙(달력일 차감 → 그 이하 마지막 거래일)
    import datetime as _dt
    d0 = _dt.date.fromisoformat(dates[-1])
    base = {}
    for k, nd in IND_HOR:
        tgt = (d0 - _dt.timedelta(days=nd)).isoformat()
        ks = [i for i, d in enumerate(dates) if d <= tgt]
        base[k] = ks[-1] if ks else None

    grp = {}
    for s in stocks:
        code = ((co.get(s["t"]) or [None])[0] or "")[:2]
        if not code:
            continue                              # SIC 미부여 — 조용히 섞지 않고 뺀다
        g = grp.setdefault(code, {"ts": [], "above": 0, "n_ma200": 0})
        g["ts"].append(s["t"])
        if not s.get("part"):
            g["n_ma200"] += 1
            if "200일이탈" not in (s.get("flags") or []):
                g["above"] += 1

    # 가격은 **종목당 한 번만** 읽는다. 기간마다 다시 열면 518파일 × 구간수가 되고,
    # 정작 쓰는 것은 파일마다 값 세 개(기준 둘 + 최신 하나)뿐이다.
    keep = [t for code, g in grp.items() if len(g["ts"]) >= IND_MIN for t in g["ts"]]
    PX = {}
    for t in keep:
        p = os.path.join(root, "data", "sd", "%s.json" % t)
        if not os.path.exists(p):
            continue
        try:
            px = json.load(io.open(p, encoding="utf-8")).get("pxd") or []
        except Exception:
            continue
        if len(px) == len(dates):
            PX[t] = px

    out = []
    for code, g in grp.items():
        if len(g["ts"]) < IND_MIN:
            continue
        r = {}
        for k, _nd in IND_HOR:
            i0, vs = base[k], []
            if i0 is not None:
                for t in g["ts"]:
                    px = PX.get(t)
                    if not px:
                        continue
                    a, b = px[i0], px[-1]
                    if a and b and a > 0:
                        vs.append(b / a - 1.0)
            # 동일가중 평균. 절반 넘게 못 구하면 그 칸은 비운다 — 몇 종목의 평균을
            # 산업 수익률이라 부르지 않는다.
            r[k] = round(sum(vs) / len(vs) * 100, 2) if len(vs) >= max(3, len(g["ts"]) // 2) else None
        out.append({"sic": code, "n": len(g["ts"]), "nm": SIC2.get(code, "SIC " + code),
                    "above": g["above"], "n_ma200": g["n_ma200"], "r": r})
    out.sort(key=lambda x: -(x["r"].get("1M") if x["r"].get("1M") is not None else -1e9))
    return out


def _breadth(stocks):
    """③ 시장 폭 — 지수가 아니라 '몇 종목이 어느 상태인가'.

    홈에 폭 카드를 세우려면 flags/timing 분포가 필요한데, 그것 때문에 홈이 stocks.json
    raw 691KB(gz 199KB)를 받게 하면 이 파일의 존재 이유가 사라진다. 정수 몇 개만 여기서 세어 싣는다(+0.3KB).
    """
    fl, tm = {}, {}
    for s in stocks:
        for f in (s.get("flags") or []):
            fl[f] = fl.get(f, 0) + 1
        t = s.get("timing")
        if t:
            tm[t] = tm.get(t, 0) + 1
    n = len(stocks)

    # 200일선 위 비율의 분모는 **200일선이 산출되는 종목**이어야 한다.
    # part(부분 편입 — 상장 200거래일 미만, refresh_stocks.py:579)는 200일선이 없어서
    # '200일이탈' 플래그가 붙지 않을 뿐인데, 여집합으로 세면 그대로 '위'로 잡혀 비율이 부푼다.
    # 오늘 기준 4종목(Q·FDXF·HONA·SPCX) 차이지만 신규 상장이 몰리면 커진다.
    full = [s for s in stocks if not s.get("part")]
    below_full = sum(1 for s in full if "200일이탈" in (s.get("flags") or []))
    # ── 섹터별 폭 ── 전체 한 숫자로는 '어디가 강한가'를 못 본다(사용자 요청 2026-08-02
    #   "시장을 좀 더 세분화해서 보고싶어"). 같은 분모 규칙(part 제외)을 섹터 안에서 다시 적용한다.
    # ⚠ 키를 **섹터 ETF 티커**로 둔다. 홈이 market_board.json 의 sector 행과 짝지어 그리는데,
    #   한글 이름으로 키를 잡으면 그쪽 표기가 바뀌는 날 조인이 조용히 끊긴다. 티커는 안 바뀐다.
    #   market.html 도 같은 폭을 stocks.json 에서 직접 세지만(그 화면은 원본을 받는다) 분모
    #   규칙이 같아야 두 화면의 숫자가 일치한다 — 여기서 규칙을 바꾸면 그쪽도 볼 것.
    SEC_ETF = {"Information Technology": "XLK", "Financials": "XLF", "Health Care": "XLV",
               "Consumer Discretionary": "XLY", "Communication Services": "XLC",
               "Industrials": "XLI", "Consumer Staples": "XLP", "Energy": "XLE",
               "Utilities": "XLU", "Real Estate": "XLRE", "Materials": "XLB"}
    sec = {}
    for s in full:
        tk = SEC_ETF.get(s.get("sector") or "")
        if not tk:
            continue                              # 미분류는 섹터 카드에 세지 않는다
        d = sec.setdefault(tk, {"n": 0, "above": 0})
        d["n"] += 1
        if "200일이탈" not in (s.get("flags") or []):
            d["above"] += 1
    return {
        "n": n,
        "n_ma200": len(full),                     # 200일선이 산출되는 종목 수(비율의 분모)
        "n_partial": n - len(full),               # 이력이 짧아 판정 불가
        "above200": len(full) - below_full,
        "sector": sec,                            # {섹터ETF: {n, above}} — 홈 폭 카드가 쪼개 그린다
        "flags": dict(sorted(fl.items(), key=lambda kv: -kv[1])),
        "timing": tm,
    }


def build(stocks, dates, as_of, root):
    buy, nb, nb_c, nb_p = _reco(stocks, dates, "bms", "bmw")
    sell, ns, ns_c, ns_p = _reco(stocks, dates, "sms", "smw")
    return {
        "as_of": as_of, "win": WIN,
        "buy": buy, "sell": sell, "nbuy": nb, "nsell": ns,
        "buy_conf": nb_c, "buy_prov": nb_p, "sell_conf": ns_c, "sell_prov": ns_p,
        "breadth": _breadth(stocks),
        # 섹터(11)와 종목(518) 사이 — SIC 대분류. 홈 산업 카드가 읽는다.
        "industry": _industry(stocks, dates, root),
    }


def write(stocks, dates, as_of, root):
    """실패를 삼키지 않는다 — 홈의 핵심 모듈이라 조용히 빈 채로 배포되면 안 된다."""
    doc = build(stocks, dates, as_of, root)
    if not doc["buy"] and not doc["sell"]:
        raise SystemExit("home_reco: 최근 타점이 하나도 없다 — 마커 산출이 깨졌는지 확인")
    p = os.path.join(root, "data", "home_reco.json")
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return p, doc


if __name__ == "__main__":
    R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    d = json.load(io.open(os.path.join(R, "data", "stocks.json"), encoding="utf-8"))
    p, doc = write(d["stocks"], d["pxd_dates"], d["as_of"], R)
    print(f"→ {os.path.basename(p)} ({os.path.getsize(p)//1024 or 1}KB) "
          f"매수 {doc['nbuy']}(확정 {doc['buy_conf']}·잠정 {doc['buy_prov']}) · "
          f"매도 {doc['nsell']}(확정 {doc['sell_conf']}·잠정 {doc['sell_prov']})")
