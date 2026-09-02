# -*- coding: utf-8 -*-
"""build/dollarcarry.py — C14 달러 캐리 타이밍(LRV 2014) → data/_dollarcarry.json

규약: build/PREREG-2026-09-02-DOLLARCARRY.md (계산 전 커밋 92554b22b).

  AFD_t = mean_i(외화 3개월 인터뱅크) − 미국 3개월 인터뱅크  (그 달 값)
  AFD>0 → 다음 달 바스켓 롱·달러 숏 / AFD<0 → 반대. 밴드 없음(논문에 없다).
  rx_i,t+1 = (1 + i*_i,t/12) × (S_i,t+1/S_i,t) − (1 + i_US,t/12),  S = 달러/외화

🚨 **부호 관례가 급소다.** yfinance 티커가 두 갈래로 갈리는데 뒤집어도 성적은 멀쩡히
  나온다. 그래서 자동 검사를 넣었다(등록 §3 F4) — 통과 못 하면 계산을 버린다.

🚨 **얼린 측정이다.** 입력이 yfinance FX + FRED OECD 라 저장소에 없다. 산출물도 밑줄
  접두로 두고 커밋하지 않는다(secrev_panel.py 와 같은 사유). 자동 재굽기 금지.

    python build/dollarcarry.py
"""
from __future__ import annotations
import csv
import io
import json
import math
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_dollarcarry.json")     # 밑줄 = 로컬 전용(커밋 금지)
UA = {"User-Agent": "Mozilla/5.0"}

# ── 등록 §1 의 상수 — 결과를 보고 만지지 않는다 ─────────────────────────────
# 카드가 적은 G10 열 통화. 순서는 카드 그대로.
CCY = ["EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "SEK", "NOK", "DKK", "NZD"]
FRED_CC = {"EUR": "EZ", "JPY": "JP", "GBP": "GB", "AUD": "AU", "CAD": "CA",
           "CHF": "CH", "SEK": "SE", "NOK": "NO", "DKK": "DK", "NZD": "NZ",
           "USD": "US"}
# 🚨 **열 통화 모두 `XXXUSD=X`(달러/외화)로 받는다 — 역수를 취하지 않는다.**
#   등록 §1 은 여섯 통화를 `JPY=X` 꼴로 받아 역수를 취한다고 적었는데, 그러면 부호를
#   뒤집을 자리가 여섯 곳 생긴다. 실측으로 `XXXUSD=X` 가 열 통화 다 있고 이력도 역수판과
#   **하루도 다르지 않아**(둘 다 공통 시작 2006-05-16) 역수를 쓸 이유가 없었다.
#   ⚠ 등록이 정한 것은 «S = 달러/외화» 라는 **양**이지 티커가 아니다. 같은 양을 더 안전한
#     경로로 받는 것이라 규칙은 안 바뀐다. 그래도 바꿨다는 사실을 결과 문서에 적는다.
DIRECT = {c: "%sUSD=X" % c for c in CCY}
# 방향 증명용 짝 — `XXXUSD=X × XXX=X ≡ 1` 이어야 한다(F4).
RECIP = {c: "%s=X" % c for c in CCY}
COST_RT = 0.0010        # 스위칭 왕복 10bp — 등록 §3 F3 의 상단값
SPLIT = "2011-01"       # 논문 발표 이후 구간의 시작 — 등록 §3-1


def fred(sid):
    u = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=1990-01-01" % sid
    raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                 timeout=60).read().decode()
    out = {}
    for r in list(csv.reader(io.StringIO(raw)))[1:]:
        if len(r) > 1 and r[1] not in (".", ""):
            try:
                out[r[0][:7]] = float(r[1])
            except ValueError:
                pass
    return out


def load_spot():
    """통화 → {YYYY-MM: 그 달 마지막 거래일의 달러/외화}. 역수 대상은 여기서 뒤집는다."""
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    tick = list(DIRECT.values()) + list(RECIP.values())
    df = yf.download(tick, start="2005-01-01", progress=False,
                     auto_adjust=False, threads=True)["Close"]

    # ── 등록 §3 F4 — 방향 자동 검사 ─────────────────────────────────────
    # 🚨 크기로는 못 가른다. 처음에 «달러/외화는 1 근처» 로 짰다가 USDCAD(1.25)·
    #   USDCHF(0.97)에서 그대로 걸렸다 — 두 통화는 달러와 값이 비슷해 어느 방향이든
    #   1 근처다. 크기가 아니라 **항등식**으로 증명한다:
    #        XXXUSD=X × XXX=X ≡ 1
    #   실측(2024~ 중앙값)으로 열 통화 다 정확히 1.0000 이다. 이 곱이 1 에서 벗어나면
    #   그 통화는 내가 생각한 방향이 아니므로 계산을 버린다.
    bad = []
    for c in CCY:
        a = df[DIRECT[c]].dropna()
        b = df[RECIP[c]].dropna()
        if not len(a) or not len(b):
            bad.append("%s — 계열이 비었다(%s · %s)" % (c, DIRECT[c], RECIP[c]))
            continue
        prod = float(a.median()) * float(b.median())
        if abs(prod - 1.0) > 0.02:
            bad.append("%s — %s × %s = %.4f (1 이어야 한다). 방향이 내 가정과 다르다"
                       % (c, DIRECT[c], RECIP[c], prod))
    # 엔은 달러/외화가 0.01 미만이어야 한다(1엔 ≈ 0.0065달러) — 방향을 한 번 더 못박는다.
    _jpy = float(df[DIRECT["JPY"]].dropna().median())
    if not (_jpy < 0.02):
        bad.append("JPY — %s 중앙 %.5f. 달러/외화면 0.01 근처여야 한다" % (DIRECT["JPY"], _jpy))
    if bad:
        raise SystemExit("🚨 방향 검사 실패(등록 §3 F4) — 계산을 버린다:\n  "
                         + "\n  ".join(bad))

    out = {}
    for c in CCY:
        s = df[DIRECT[c]].dropna()
        by = {}
        for d, v in s.items():
            v = float(v)
            if v > 0:
                by[d.strftime("%Y-%m")] = v
        out[c] = by      # 같은 달은 뒤 값이 덮으므로 그 달 **마지막** 거래일이 남는다
    return out, dict(DIRECT)


def mdd(rets):
    p = pk = 1.0
    d = 0.0
    for x in rets:
        p *= 1 + x
        pk = max(pk, p)
        d = min(d, p / pk - 1)
    return d * 100


def stats(rets, per=12):
    n = len(rets)
    m = sum(rets) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / (n - 1)) if n > 1 else 0.0
    p = 1.0
    for x in rets:
        p *= 1 + x
    return {"n": n,
            "cagr": round((p ** (per / n) - 1) * 100, 2),
            "vol": round(sd * math.sqrt(per) * 100, 2),
            "sharpe": round((m * per) / (sd * math.sqrt(per)), 3) if sd else None,
            "t": round(m / (sd / math.sqrt(n)), 2) if sd else None,
            "mdd": round(mdd(rets), 2),
            "hit": round(100 * sum(1 for x in rets if x > 0) / n, 1)}


def main():
    print("금리 — FRED OECD 3개월 인터뱅크 11개 계열")
    R = {}
    for c, cc in FRED_CC.items():
        R[c] = fred("IR3TIB01%sM156N" % cc)
        ks = sorted(R[c])
        print("  %-4s %-18s %s ~ %s (%d)"
              % (c, "IR3TIB01%sM156N" % cc, ks[0], ks[-1], len(ks)))

    print("환율 — yfinance 10 계열")
    S, TK = load_spot()
    print("  방향 검사 통과(등록 §3 F4) — 항등식 XXXUSD=X × XXX=X ≡ 1, 열 통화 %d (역수 %d)"
          % (len(DIRECT), 0))

    rate_m = sorted(set.intersection(*[set(v) for v in R.values()]))
    spot_m = sorted(set.intersection(*[set(v) for v in S.values()]))
    months = [m for m in rate_m if m in spot_m]
    print("금리 공통 %d개월 · 환율 공통 %d개월 → 교집합 %d개월 (%s ~ %s)"
          % (len(rate_m), len(spot_m), len(months), months[0], months[-1]))

    rows = []
    for k in range(len(months) - 1):
        t, t1 = months[k], months[k + 1]
        afd = sum(R[c][t] for c in CCY) / len(CCY) - R["USD"][t]
        rx = {}
        for c in CCY:
            rx[c] = ((1 + R[c][t] / 100 / 12) * (S[c][t1] / S[c][t])
                     - (1 + R["USD"][t] / 100 / 12))
        bask = sum(rx.values()) / len(rx)
        bask9 = sum(v for c, v in rx.items() if c != "DKK") / 9      # F5 — DKK 제외
        sig = 1.0 if afd > 0 else -1.0
        rows.append({"t": t, "hold": t1, "afd": round(afd, 4), "sig": sig,
                     "bask": bask, "bask9": bask9,
                     "strat": sig * bask, "strat9": sig * bask9,
                     "rf": R["USD"][t] / 100 / 12})

    def pick(lo, hi):
        return [r for r in rows
                if (lo is None or r["t"] >= lo) and (hi is None or r["t"] <= hi)]

    def series(key, lo=None, hi=None, cost=False):
        out, prev = [], None
        for r in rows:
            if lo is not None and r["t"] < lo:
                prev = r["sig"]
                continue
            if hi is not None and r["t"] > hi:
                continue
            v = r[key]
            if cost and prev is not None and r["sig"] != prev:
                v -= COST_RT            # 방향이 바뀐 달에만 왕복비용
            prev = r["sig"]
            out.append(v)
        return out

    def block(lo=None, hi=None):
        sub = pick(lo, hi)
        sw = sum(1 for k in range(1, len(rows))
                 if rows[k]["sig"] != rows[k - 1]["sig"]
                 and (lo is None or rows[k]["t"] >= lo)
                 and (hi is None or rows[k]["t"] <= hi))
        return {"전략(AFD 타이밍)": stats(series("strat", lo, hi)),
                "전략 · 비용 10bp": stats(series("strat", lo, hi, cost=True)),
                "정적 롱 바스켓": stats(series("bask", lo, hi)),
                "전략 · DKK 제외 9통화": stats(series("strat9", lo, hi)),
                "정적 롱 · DKK 제외": stats(series("bask9", lo, hi)),
                "무위험(미 3M)": stats(series("rf", lo, hi)),
                "_sw": sw, "_n": len(sub),
                "_first": sub[0]["hold"], "_last": sub[-1]["hold"],
                "_long_usd_pct": round(100 * sum(1 for r in sub if r["sig"] < 0)
                                       / max(1, len(sub)), 1)}

    full = block()
    pre = block(None, "2010-12")
    post = block(SPLIT, None)
    lab_lo = "%d-%s" % (int(months[-1][:4]) - 10, months[-1][5:7])
    lab10 = block(lab_lo, None)

    def show(name, b):
        print()
        print("── %s · %s~%s · %d개월 · 스위칭 %d회 · 달러 롱이던 달 %.0f%% ──"
              % (name, b["_first"], b["_last"], b["_n"], b["_sw"], b["_long_usd_pct"]))
        print("   %-24s %8s %8s %8s %7s %8s %7s"
              % ("", "CAGR", "변동성", "샤프", "t", "MDD", "적중"))
        for k, v in b.items():
            if k.startswith("_"):
                continue
            print("   %-24s %7.2f%% %7.2f%% %8s %7s %7.2f%% %6.1f%%"
                  % (k, v["cagr"], v["vol"], v["sharpe"], v["t"], v["mdd"], v["hit"]))

    print("\n" + "=" * 80)
    print("C14 달러 캐리 — 등록 PREREG-2026-09-02-DOLLARCARRY.md (계산 전 커밋 92554b22b)")
    print("=" * 80)
    show("주 판정 구간", full)
    show("논문 표본과 겹침 ~2010-12", pre)
    show("논문 발표 이후 %s~ (완전 표본외)" % SPLIT, post)
    show("랩 10년판(보조 진단 — 판정을 안 바꾼다)", lab10)

    # 신호 자체의 예측력 — AFD_t 대 bask_{t+1}
    xs = [r["afd"] for r in rows]
    ys = [r["bask"] for r in rows]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / sxx
    a = my - b * mx
    res = [ys[i] - a - b * xs[i] for i in range(n)]
    s2 = sum(z * z for z in res) / (n - 2)
    tb = b / math.sqrt(s2 / sxx)
    r2 = 1 - sum(z * z for z in res) / sum((y - my) ** 2 for y in ys)
    print()
    print("신호 예측력 — bask_{t+1} = a + b·AFD_t :  b = %+.5f · t = %.2f · R² = %.4f"
          % (b, tb, r2))
    print("   (논문 주장대로면 b > 0 — AFD 가 클수록 다음 달 바스켓이 오른다)")

    doc = {"note": ("C14 달러 캐리 타이밍(LRV 2014). 규약 build/PREREG-2026-09-02-DOLLARCARRY.md. "
                    "🚨 얼린 측정이다 — 입력(yfinance FX · FRED OECD)이 저장소에 없어 러너가 "
                    "재생산할 수 없다. 자동 재굽기 금지."),
           "prereg": "92554b22b", "ccy": CCY, "tickers": TK,
           "rate_series": {c: "IR3TIB01%sM156N" % cc for c, cc in FRED_CC.items()},
           "cost_rt": COST_RT, "window": [rows[0]["hold"], rows[-1]["hold"]],
           "blocks": {"full": full, "pre2011": pre, "post2011": post, "lab10": lab10},
           "signal_reg": {"beta": b, "t": tb, "r2": r2},
           "rows": rows}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
