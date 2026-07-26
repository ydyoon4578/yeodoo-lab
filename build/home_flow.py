# -*- coding: utf-8 -*-
"""build/home_flow.py — 홈 전용 슬림 묶음 → data/home_flow.json

왜 필요한가. 홈에 공시·수급·신호·캘린더를 붙이면서 원본 파일을 그대로 받게 했더니
홈 한 번 여는 데 639KB가 됐다. 정작 쓰는 건 몇 줄뿐이다 —
  filings.json 226KB에서 8줄 · signal_lab.json 125KB에서 10줄 · guru.json 69KB에서 8줄.

이 저장소엔 이미 같은 문제를 푼 선례가 있다(home_reco.json — 홈이 stocks.json 392KB를
받지 않게 하려고 만든 슬림 파일). 같은 방식으로 홈이 볼 것만 추려 담는다.

⚠ 여기 담긴 값은 전부 **원본에서 계산한 것**이지 따로 만든 수치가 아니다. 원본이 바뀌면
   이 파일도 다시 구워야 하므로, 원본을 만드는 워크플로마다 이 스크립트를 이어 붙인다.

  python build/home_flow.py
"""
from __future__ import annotations
import datetime as dt
import io, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "home_flow.json")
N_ROW = 8          # 각 칸에 보일 줄 수
CAL_DAYS = 33      # 캘린더가 그리는 4주 + 여유.
# 홈이 그리는 창은 '기준일이 낀 주의 월요일부터 4주'다. 기준일이 금요일이면 그 월요일이
# 기준일-4일이므로 마지막 칸은 기준일+23일까지 간다. 여기에 주말·공휴일 이월을 더해 33일을
# 잡는다 — 창보다 짧게 잡으면 마지막 주가 통째로 비는데, 화면에는 '그날 일정이 없다'로 보인다.


def load(fn):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    doc = {"note": "홈 전용 슬림 묶음. 원본(filings·insider·guru·signal_lab·earnings)에서 "
                   "홈이 실제로 그리는 줄만 추렸다 — 홈이 원본 639KB를 받지 않게 하려는 것이다. "
                   "수치는 전부 원본에서 온 것이고 여기서 새로 만들지 않는다.",
           "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

    # ── 주요 8-K ── major 항목만. 전체를 흘리면 홈이 공시 피드가 된다.
    f = load("filings.json") or {}
    feed = f.get("feed") or []
    maj = set(f.get("major") or [])
    items = f.get("items") or {}
    cik = f.get("cik") or {}
    rows = [x for x in feed if maj & set(x.get("it") or [])]
    rows.sort(key=lambda x: x.get("d") or "", reverse=True)
    doc["filings"] = {
        "as_of": f.get("as_of"), "doc_base": f.get("doc_base"),
        "rows": [{"t": x["t"], "d": x.get("d"),
                  "lab": next((items.get(c, c) for c in (x.get("it") or []) if c in maj), ""),
                  "u": ("%s%s/%s/%s" % (f.get("doc_base") or "", cik.get(x["t"]), x.get("a"), x.get("p"))
                        if cik.get(x["t"]) and x.get("a") and x.get("p") else None)}
                 for x in rows[:N_ROW]],
    }

    # ── 내부자 ── 장내매수(P) > 장내매도(S)인 종목. 보상 제도 결과(A·M·F)는 원본에서 이미 뺐다.
    ins = load("insider.json") or {}
    by_t = ins.get("by_t") or {}
    ib = sorted(((t, v[0], v[1]) for t, v in by_t.items() if len(v) > 1 and v[0] > v[1]),
                key=lambda z: -(z[1] - z[2]))
    doc["insider"] = {"as_of": ins.get("as_of"),
                      "rows": [{"t": t, "b": b, "s": s_} for t, b, s_ in ib[:N_ROW]]}

    # ── 거장 공통 보유 ──
    g = load("guru.json") or {}
    doc["guru"] = {"as_of": g.get("as_of"),
                   "rows": [{"t": x["t"], "nm": x.get("nm") or x["t"], "n": x.get("n")}
                            for x in (g.get("overlap") or [])[:N_ROW]]}

    # ── 오늘 지표 신호 ──
    sl = load("signal_lab.json") or {}
    td = ((sl.get("consensus") or {}).get("today") or {})
    doc["signal"] = {"dt": td.get("dt"),
                     "top": [{"t": x["t"], "n": x.get("n") or x["t"], "v": x.get("v")}
                             for x in (td.get("top") or [])[:4]],
                     "bot": [{"t": x["t"], "n": x.get("n") or x["t"], "v": x.get("v")}
                             for x in (td.get("bot") or [])[:4]]}

    # ── 캘린더용 실적 ── 3주 창만. 원본은 90일치라 홈이 다 받을 이유가 없다.
    e = load("earnings.json") or {}
    base = e.get("as_of")
    # 시가총액 — 캘린더를 큰 회사부터 보여주려면 필요하다. stocks.json의 fund.mc(억 달러).
    # 없는 종목은 0으로 두고 뒤로 보낸다(작다고 단정하지 않고, 순서만 뒤로).
    MC = {}
    _st = load("stocks.json") or {}
    for _x in (_st.get("stocks") or []):
        _v = (_x.get("fund") or {}).get("mc")
        if isinstance(_v, (int, float)):
            MC[_x["t"]] = float(_v)
    up = []
    if base:
        d0 = dt.date.fromisoformat(base) - dt.timedelta(days=7)   # 지난 주도 그린다
        d1 = dt.date.fromisoformat(base) + dt.timedelta(days=CAL_DAYS)
        for x in (e.get("upcoming") or []) + (e.get("recent") or []):
            try:
                dd = dt.date.fromisoformat(x["dt"])
            except Exception:
                continue
            if d0 <= dd <= d1:
                up.append({"t": x["t"], "n": x.get("n") or x["t"], "dt": x["dt"],
                           "hour": x.get("hour") or "", "mc": round(MC.get(x["t"], 0.0))})
    # 날짜별로 묶되 그 안에서는 **시가총액 큰 순**. 하루에 수십 종목이 뜨는 날이 있어
    # 알파벳 순으로 두면 큰 회사가 '+37' 뒤에 숨는다.
    up.sort(key=lambda z: (z["dt"], -z["mc"], z["t"]))
    doc["earnings"] = {"as_of": base, "n_all": len(e.get("upcoming") or []), "rows": up}

    # ── 캘린더용 경제지표 ── **주요 지표만**.
    # FRED 릴리스에는 'H.15 Selected Interest Rates'·'ICE BofA Indices'·'CBOE Market Statistics'처럼
    # 매 영업일 갱신되는 **시장 데이터 피드**가 섞여 있다. 그런 건 '발표 일정'이 아니라 상시 수치이고,
    # 개수로만 보면 상위 4개가 전체의 80%를 먹어 정작 CPI·고용보고서를 가린다.
    # 그래서 '정해진 날 나오고 시장이 반응하는 거시 지표'만 남긴다. 전체 목록은 calendar.html에 그대로 있다.
    MAJOR = {
        "Employment Situation": "고용보고서",
        "Consumer Price Index": "소비자물가(CPI)",
        "Producer Price Index": "생산자물가(PPI)",
        "Personal Income and Outlays": "개인소득·지출(PCE)",
        "Advance Monthly Sales for Retail and Food Services": "소매판매",
        "Gross Domestic Product": "GDP",
        "Job Openings and Labor Turnover Survey": "구인·이직(JOLTS)",
        "Unemployment Insurance Weekly Claims Report": "주간 실업수당 청구",
        "New Residential Construction": "주택착공·허가",
        "G.17 Industrial Production and Capacity Utilization": "산업생산",
        "S&P Cotality Case-Shiller Home Price Indices": "주택가격(케이스실러)",
        "Surveys of Consumers": "소비자심리(미시간대)",
        "Chicago Fed National Activity Index": "시카고연준 경기지수",
        "Sahm Rule Recession Indicator": "삼의 법칙(침체 신호)",
        "Existing Home Sales": "기존주택 판매",
        "New Home Sales": "신규주택 판매",
        "Advance Economic Indicators": "선행 경제지표",
    }
    c = load("calendar.json") or {}
    rels = c.get("releases") or {}
    mac = []
    if base:
        d0 = dt.date.fromisoformat(base) - dt.timedelta(days=7)
        d1 = dt.date.fromisoformat(base) + dt.timedelta(days=CAL_DAYS)
        seen_k = set()
        for x in (c.get("dates") or []):
            try:
                dd = dt.date.fromisoformat(x["d"])
            except Exception:
                continue
            if not (d0 <= dd <= d1):
                continue
            nm = (rels.get(str(x.get("rid"))) or {}).get("name") or ""
            ko = MAJOR.get(nm)
            if not ko:
                continue
            k = (x["d"], ko)
            if k in seen_k:
                continue
            seen_k.add(k)
            mac.append({"d": x["d"], "n": ko})
    mac.sort(key=lambda z: (z["d"], z["n"]))
    doc["macro"] = {"as_of": c.get("as_of"), "n_all": len(c.get("dates") or []), "rows": mac}

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    src = sum(os.path.getsize(os.path.join(DATA, x)) for x in
              ("filings.json", "insider.json", "guru.json", "signal_lab.json", "earnings.json")
              if os.path.exists(os.path.join(DATA, x)))
    _nomc = sum(1 for z in up if not z["mc"])
    if _nomc:
        print("  ⚠ 시총 없는 종목 %d건 — 그날 목록 뒤로 밀린다(유니버스 밖이거나 fund 결측)" % _nomc)
    print("  주요 경제지표 %d건(전체 %d건에서 추림 — 나머지는 상시 시장 데이터 피드)"
          % (len(mac), len(c.get("dates") or [])))
    print("홈 슬림 묶음 — 공시 %d · 내부자 %d · 거장 %d · 신호 %d · 실적 %d줄 · %.0fKB (원본 %.0fKB)"
          % (len(doc["filings"]["rows"]), len(doc["insider"]["rows"]), len(doc["guru"]["rows"]),
             len(doc["signal"]["top"]) + len(doc["signal"]["bot"]), len(up),
             os.path.getsize(OUT) / 1024, src / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
