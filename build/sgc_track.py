# -*- coding: utf-8 -*-
"""build/sgc_track.py — S&P 500 성장 전환 전략을 **매 거래일** 추적한다.

전략은 월말에 판단하고 다음 거래일 종가에 체결한다(전략 저장소 README 2절). 그 사이에는
보유를 그대로 둔다. 그래서 일간 추적은 «마지막 체결일 종가의 보유를 오늘 종가로 평가» 다.

  펀드 NAV_t = (1 − Σw_i)·TR_t/TR_0 + Σ w_i · P_i,t / P_i,0
     w_i  = 체결 직후 NAV 대비 종목 비중(data/sgc/inputs.json hold_nav)
     지수 몫 = 90% + 체결하지 않은 선별 몫(S&P 500 TR 로 센다)
     P    = 수정 종가(data/sd/{T}.json · 배당 · 분할 조정) · TR = ^SP500TR

신호는 «오늘 월말이라면» 미리보기다 — 확정은 월말 종가다.
  금리: DFII10 오늘 − 직전 월말 ≥ +0.10%p
  추세: S&P 500 TR 오늘 < (직전 11개 월말 + 오늘) 평균

  python build/sgc_track.py        → data/sgc_track.json
"""
from __future__ import annotations
import datetime as dt
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SGC = os.path.join(DATA, "sgc")
OUT = os.path.join(DATA, "sgc_track.json")
RATE_TH = 0.10


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def update_tr(tr: dict) -> str:
    """^SP500TR 를 yfinance 로 이어 붙인다. 실패하면 SPY 수정 종가 수익률로 잇는다."""
    last = tr["dates"][-1]
    src = "^SP500TR"
    add = {}
    try:
        import yfinance as yf
        start = (dt.date.fromisoformat(last) - dt.timedelta(days=10)).isoformat()
        df = yf.download("^SP500TR", start=start, progress=False, auto_adjust=False)
        col = df["Close"]
        if hasattr(col, "columns"):
            col = col.iloc[:, 0]
        for d, v in col.dropna().items():
            add[d.strftime("%Y-%m-%d")] = float(v)
    except Exception as e:                                       # noqa: BLE001
        print(f"⚠ ^SP500TR 받기 실패({e}) — SPY 수정 종가로 잇는다")
    if add and last in add:
        # 겹치는 날로 수준을 맞춘다(같은 지수라 비율 ≈ 1)
        k = tr["px"][-1] / add[last]
        for d in sorted(add):
            if d > last:
                tr["dates"].append(d); tr["px"].append(round(add[d] * k, 4))
    else:
        a = load(os.path.join(DATA, "assets.json"))
        ds, px = a["dates"], a["px"]["SPY"]
        if last in ds:
            i0 = ds.index(last)
            base = tr["px"][-1]
            for i in range(i0 + 1, len(ds)):
                if px[i] and px[i0]:
                    tr["dates"].append(ds[i]); tr["px"].append(round(base * px[i] / px[i0], 4))
            if tr["dates"][-1] != last:
                src = "SPY 수정 종가로 이은 ^SP500TR"
    return src


def month_ends(dates):
    out = []
    for i, d in enumerate(dates):
        if i + 1 == len(dates) or dates[i + 1][:7] != d[:7]:
            out.append(i)
    return out


def main() -> int:
    inp = load(os.path.join(SGC, "inputs.json"))
    trp = os.path.join(SGC, "sp500tr_daily.json")
    tr = load(trp)
    tr_src = update_tr(tr)
    with open(trp, "w", encoding="utf-8") as f:
        json.dump(tr, f, separators=(",", ":"))

    stk = load(os.path.join(DATA, "stocks.json"))
    pdates = stk["pxd_dates"]
    ex = inp["exec_date"]
    if ex not in pdates:
        sys.exit(f"체결일 {ex} 이 가격 격자에 없다")
    i0 = pdates.index(ex)
    trmap = dict(zip(tr["dates"], tr["px"]))
    days = [d for d in pdates[i0:] if d in trmap]
    tr0 = trmap[ex]

    hold = inp["hold_nav"]
    px, miss = {}, []
    for t in hold:
        p = os.path.join(DATA, "sd", t.replace(".", "-") + ".json")
        if not os.path.exists(p):
            p = os.path.join(DATA, "sd", t + ".json")
        if not os.path.exists(p):
            miss.append(t); continue
        s = load(p)["pxd"]
        if len(s) != len(pdates):
            s = [None] * (len(pdates) - len(s)) + s
        px[t] = s
    w_idx = 1.0 - sum(hold[t] for t in px)                        # 못 찾은 종목 몫은 지수로

    series = []
    last_px = {}
    for d in days:
        i = pdates.index(d)
        b = trmap[d] / tr0
        nav = w_idx * b
        for t, s in px.items():
            v = s[i] if s[i] is not None else last_px.get(t, s[i0])
            last_px[t] = v
            nav += hold[t] * v / s[i0]
        series.append({"d": d, "fund": round(nav, 6), "bench": round(b, 6)})

    meta = {x["t"]: x for x in stk["stocks"]}
    di = pdates.index(days[-1])
    rows = []
    for t, w in sorted(hold.items(), key=lambda kv: -kv[1]):
        nm = dict(inp["names"].get(t, {}))
        if nm.get("name", t) == t and t in meta:                # 목표에서 빠지고 보유만 남은 이름
            nm.update(name=meta[t].get("name", t), sector=meta[t].get("sector", ""))
        r = None
        if t in px and px[t][i0]:
            v = px[t][di] if px[t][di] is not None else last_px.get(t)
            r = v / px[t][i0] - 1
        prev_r = None
        if t in px and len(days) > 1:
            j = pdates.index(days[-2])
            if px[t][j]:
                prev_r = (px[t][di] or px[t][j]) / px[t][j] - 1
        rows.append({"t": t, "name": nm.get("name", t), "sector": nm.get("sector", ""),
                     "books": nm.get("books", []), "w0": w,
                     "w_now": (w * (1 + r) / series[-1]["fund"]) if r is not None else None,
                     "ret": r, "ret_1d": prev_r,
                     "contrib": w * r if r is not None else None})

    # ── 신호 미리보기 ──
    rt = load(os.path.join(DATA, "rates.json"))
    rd = rt["dates"]; rs = rt["series"]["DFII10"]
    pairs = [(d, v) for d, v in zip(rd, rs) if v is not None]
    r_last_d, r_last = pairs[-1]
    cur_m = r_last_d[:7]
    prev_me = [p for p in pairs if p[0][:7] < cur_m]
    r_base_d, r_base = prev_me[-1]
    r_chg = r_last - r_base
    me = month_ends(tr["dates"])
    t_last_d = tr["dates"][-1]
    done = [i for i in me if tr["dates"][i][:7] < t_last_d[:7]][-11:]
    vals = [tr["px"][i] for i in done] + [tr["px"][-1]]
    ma = sum(vals) / len(vals)
    rate_on = r_chg >= RATE_TH - 1e-12
    trend_on = tr["px"][-1] < ma
    v_share = 0.5 * rate_on * (1 + trend_on)

    f, b = series[-1]["fund"], series[-1]["bench"]
    out = {
        "note": "build/sgc_track.py 생성. 마지막 체결일 종가의 실제 보유를 매 거래일 종가로 평가한다. 백테스트 숫자가 아니라 표본 밖 추적이다.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": days[-1],
        "bench_src": tr_src,
        "decision_date": inp["decision_date"], "exec_date": ex,
        "next_decision_month": inp.get("next_decision_month"),
        "shares": inp["shares"], "shares_prev": inp["shares_prev"],
        "states": inp["states"],
        "book_nm": inp["book_nm"], "n_target": inp["n_target"],
        "w_index": w_idx, "w_sleeve": 1 - w_idx, "n_hold": len(px), "missing": miss,
        "since": {"fund": f - 1, "bench": b - 1, "excess": f - b},
        "day": ({"fund": f / series[-2]["fund"] - 1, "bench": b / series[-2]["bench"] - 1}
                if len(series) > 1 else None),
        "series": series,
        "holdings": rows,
        "preview": {
            "rate": {"date": r_last_d, "value": r_last, "base_date": r_base_d, "base": r_base,
                     "change": r_chg, "threshold": RATE_TH, "on": rate_on},
            "trend": {"date": t_last_d, "px": tr["px"][-1], "ma": ma, "n": len(vals),
                      "gap_pct": (tr["px"][-1] / ma - 1) * 100, "on": trend_on},
            "shares": {"E": 1 - v_share, "V": v_share},
        },
        "backtest": inp["backtest"],
        "src_repo": inp["src_repo"], "src_files": inp["src_files"],
    }
    with open(OUT, "w", encoding="utf-8") as fo:
        json.dump(out, fo, ensure_ascii=False, separators=(",", ":"))
    print(f"{days[-1]} · 체결 {ex} 이후 전략 {100*(f-1):+.2f}% · TR {100*(b-1):+.2f}% · 초과 {100*(f-b):+.2f}%p · 보유 {len(px)}종 (없음 {miss})")
    print(f"미리보기: 금리 {r_chg:+.2f}%p {'켜짐' if rate_on else '꺼짐'} · 추세 {(tr['px'][-1]/ma-1)*100:+.2f}% {'켜짐' if trend_on else '꺼짐'} · 가치주 몫 {v_share:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
