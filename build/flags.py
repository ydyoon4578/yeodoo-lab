# -*- coding: utf-8 -*-
"""build/flags.py — 극단 플래그 감시 → data/_flags.json

출처. 사용자 제공 「시장 국면 모니터」(KBAM globalpassive · 2026-07-09) ④ 「리스크
모니터링 — 극단 플래그 감시」의 설계를 이 랩으로 옮긴다. 트리거 조건은 그 문서의
값을 그대로 쓴다(내가 고르면 그것부터가 자유도다).

🚨 **적중률은 베끼지 않고 여기서 다시 잰다.** 그 문서의 「10년: 1개월 평균 SPX +2.0%
   (승률 73%)」 같은 수는 그쪽 유니버스·창의 것이다. 이 랩은 창도 자료도 다르므로
   같은 정의로 **내 자료에서** 재고, 두 수가 다르면 다른 대로 싣는다.

🚨 **이것은 매매 규칙이 아니라 감시판이다.** 이 랩은 국면 조건부 규칙을 12번 시도해
   11번 기각했다. 플래그가 켜졌다고 사는 것이 아니라 «지금 무엇이 극단인가» 를 보는 것이다.
   그 문서도 같은 말을 한다 — 「숏은 10년 검증상 전부 무효, 하락 베팅 아님」.

⚠ 그 문서의 16개 중 이 랩에 자료가 없는 다섯은 **뺀다. 지어 채우지 않는다.**
   VIX 백워데이션(VIX3M 없음) · VVIX · 풋콜 극단 · F&G 극단 · 챔피언 보유 동조성.
⚠ 선견 금지 — 플래그는 날 t 의 종가까지로 판정하고, 성과는 t 다음 거래일부터 21일이다.

  python build/flags.py
"""
from __future__ import annotations
import io, json, os, statistics as st, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_flags.json")
FWD = 21          # 사후 1개월(거래일)


def J(n):
    return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))


def sma(v, i, n):
    w = [x for x in v[max(0, i - n + 1):i + 1] if x is not None]
    return sum(w) / len(w) if len(w) >= n // 2 else None


def ema_series(v, n):
    k, out, e = 2.0 / (n + 1), [], None
    for x in v:
        if x is None:
            out.append(e); continue
        e = x if e is None else (x - e) * k + e
        out.append(e)
    return out


def rsi_series(v, n):
    """Wilder 평활 RSI — 전 구간을 한 번에 낸다.

    🚨 처음에 «최근 n봉 단순평균» 으로 짰다가 잡았다. n=14 에서는 차이가 작지만
      **n=2 에서는 치명적**이다 — 차분이 둘뿐이라 둘 다 오르면 100, 둘 다 내리면 0 이
      되어 값이 양 끝에 몰린다. 실측: RSI(2)<5 가 21.6%, <10 이 23.7% 로 그 사이에
      2.1%p 밖에 없었다(정상 분포라면 훨씬 넓다). 사실상 «최근 2일 다 내렸나» 를
      재는 이진 지표였고, Connors 의 RSI(2) 와 다른 것이 된다.
    ⚠ Wilder 평활 = alpha 1/n 의 지수평활이다(단순 n봉 평균이 아니다).
    """
    out = [None] * len(v)
    g = l = None
    seed_g, seed_l, cnt = 0.0, 0.0, 0
    for i in range(1, len(v)):
        if v[i] is None or v[i - 1] is None:
            out[i] = out[i - 1]
            continue
        ch = v[i] - v[i - 1]
        up, dn = max(ch, 0.0), max(-ch, 0.0)
        if g is None:
            seed_g += up; seed_l += dn; cnt += 1
            if cnt < n:
                continue
            g, l = seed_g / n, seed_l / n
        else:
            g = (g * (n - 1) + up) / n
            l = (l * (n - 1) + dn) / n
        out[i] = 100.0 if l == 0 else (0.0 if g == 0 else 100 - 100 / (1 + g / l))
    return out


def pctb(v, i, n=20, k=2.0):
    w = [x for x in v[max(0, i - n + 1):i + 1] if x is not None]
    if len(w) < n:
        return None
    m, s = sum(w) / len(w), st.pstdev(w)
    return (v[i] - (m - k * s)) / (2 * k * s) if s > 0 else None


def tema(v, n):
    e1 = ema_series(v, n)
    e2 = ema_series(e1, n)
    e3 = ema_series(e2, n)
    return [None if (a is None or b is None or c is None) else 3 * a - 3 * b + c
            for a, b, c in zip(e1, e2, e3)]


def macd_hist(v):
    e12, e26 = ema_series(v, 12), ema_series(v, 26)
    line = [None if (a is None or b is None) else a - b for a, b in zip(e12, e26)]
    sig = ema_series(line, 9)
    return line, [None if (a is None or b is None) else a - b for a, b in zip(line, sig)]


def td_buy_setup(v, i):
    """Demark TD 매수셋업 — 종가 < 4봉 전 종가가 연속 몇 번인가(최대 9)."""
    c = 0
    for t in range(i, max(4, i - 12), -1):
        if v[t] is None or v[t - 4] is None:
            break
        if v[t] < v[t - 4]:
            c += 1
        else:
            break
    return min(c, 9)


def main() -> int:
    B = J("bench_px.json")
    d, PX = B["dates"], B["series"]["spx"]["px"]
    n = len(d)
    A = J("assets.json")
    mac = A.get("macro") or {}
    VIX = mac.get("VIXCLS") or {}
    BAA = mac.get("BAA10Y") or {}

    def mv(s, i):
        for t in range(i, max(0, i - 7), -1):
            v = s.get(d[t])
            if v is not None:
                return v
        return None

    ma50 = [sma(PX, i, 50) for i in range(n)]
    ma200 = [sma(PX, i, 200) for i in range(n)]
    t20 = tema(PX, 20)
    mline, mh = macd_hist(PX)
    R2, R14 = rsi_series(PX, 2), rsi_series(PX, 14)

    # BAA 1년 z — 그 문서의 「BAA z」와 같은 정의(1년 평균 대비)
    def baa_z(i):
        w = [mv(BAA, t) for t in range(max(0, i - 252), i + 1)]
        w = [x for x in w if x is not None]
        cur = mv(BAA, i)
        if cur is None or len(w) < 120:
            return None
        s = st.pstdev(w)
        return (cur - sum(w) / len(w)) / s if s > 0 else None

    # ── 플래그 정의 — 트리거는 사용자 제공 문서의 값 그대로 ─────────────
    def f_vix(i):
        v, p = mv(VIX, i), mv(VIX, i - 1)
        if v is None:
            return None, None
        ch = (v / p - 1) * 100 if p else 0
        s = "ON" if (v >= 35 or ch >= 30) else ("주의" if (v >= 25 or ch >= 15) else "OFF")
        return s, "VIX %.1f · 1d %+.0f%%" % (v, ch)

    def f_rsi2(i):
        r, m2 = R2[i], ma200[i]
        if r is None or m2 is None:
            return None, None
        above = PX[i] > m2
        s = "ON" if (r < 10 and above) else ("주의" if r < 20 else "OFF")
        return s, "RSI(2) %.0f · %s" % (r, "종가>MA200" if above else "종가<MA200")

    def f_rsi14(i):
        r = R14[i]
        if r is None:
            return None, None
        return ("ON" if r < 30 else "주의" if r < 35 else "OFF"), "RSI(14) %.0f" % r

    def f_bb(i):
        b = pctb(PX, i)
        if b is None:
            return None, None
        return ("ON" if b < 0 else "주의" if b < 0.05 else "OFF"), "%%B %.2f" % b

    def f_cross(i):
        if i < 3 or t20[i] is None or ma50[i] is None:
            return None, None
        gold = dead = False
        for k in range(0, 3):
            a, b = t20[i - k], ma50[i - k]
            pa, pb = t20[i - k - 1], ma50[i - k - 1]
            if None in (a, b, pa, pb):
                continue
            if pa <= pb and a > b:
                gold = True
            if pa >= pb and a < b:
                dead = True
        s = "ON" if gold else ("주의" if dead else "OFF")
        return s, "%s" % ("정배열" if t20[i] > ma50[i] else "역배열")

    def f_td(i):
        c = td_buy_setup(PX, i)
        return ("ON" if c >= 9 else "주의" if c >= 7 else "OFF"), "매수셋업 %d/9" % c

    def f_credit(i):
        z = baa_z(i)
        if z is None:
            return None, None
        return ("ON" if z > 1.5 else "주의" if z > 0.8 else "OFF"), "BAA z %+.2f" % z

    def f_macd0(i):
        if i < 3 or mline[i] is None:
            return None, None
        up = any(mline[i - k] is not None and mline[i - k - 1] is not None
                 and mline[i - k - 1] <= 0 < mline[i - k] for k in range(3))
        return ("ON" if up else "OFF"), "MACD %s" % ("0선 위" if mline[i] > 0 else "0선 아래")

    def f_hot(i):
        r, b = R14[i], pctb(PX, i)
        if r is None or b is None:
            return None, None
        hi_r, hi_b = r >= 70, b > 1
        s = "ON" if (hi_r and hi_b) else ("주의" if (hi_r or hi_b) else "OFF")
        return s, "RSI %.0f · %%B %.2f" % (r, b)

    FLAGS = [
        ("vix_spike", "VIX 스파이크", f_vix, "주의 25 또는 1d+15% · ON 35 또는 +30%",
         "패닉 급등 → 역발상 매수 검토"),
        ("rsi2", "RSI-2 과매도", f_rsi2, "주의 <20 · ON <10 (&종가>MA200)",
         "단기 과매도 반등"),
        ("rsi14", "RSI-14 과매도", f_rsi14, "주의 <35 · ON <30", "깊은 투매 역발상"),
        ("bb_low", "볼린저 하단 이탈", f_bb, "주의 %B<0.05 · ON <0", "급락 역발상"),
        ("cross", "TEMA20/SMA50 교차", f_cross, "ON=골든 3일 내 · 주의=데드 3일 내",
         "추세 재시동"),
        ("td9", "Demark TD Setup", f_td, "주의 매수셋업 7~8 · ON 9", "하락 소진 변곡"),
        ("credit", "신용 스프레드 경계", f_credit, "주의 z>0.8 · ON z>1.5",
         "신용 스트레스 → 위험회피 선행"),
        ("macd0", "MACD 0선 상향", f_macd0, "ON=0선 상향 3일 내", "추세 회복"),
        ("hot", "과열·차익실현", f_hot, "주의 RSI>=70 또는 %B>1 · ON 동시",
         "신규 추격 자제 (숏 아님)"),
    ]

    # ── 지금 상태 + 과거 적중률 ─────────────────────────────────────────
    base = []
    for i in range(200, n - FWD):
        if PX[i] and PX[i + FWD]:
            base.append((PX[i + FWD] / PX[i] - 1) * 100)
    base_mean = st.mean(base)
    base_win = sum(1 for x in base if x > 0) / len(base) * 100

    rows = []
    for key, ko, fn, trig, use in FLAGS:
        st_now, val_now = fn(n - 1)
        hits = {"ON": [], "주의": []}
        for i in range(200, n - FWD):
            s, _v = fn(i)
            if s in hits and PX[i] and PX[i + FWD]:
                hits[s].append((PX[i + FWD] / PX[i] - 1) * 100)
        rec = {"key": key, "ko": ko, "trigger": trig, "use": use,
               "now": st_now or "—", "value": val_now or "—"}
        for s in ("ON", "주의"):
            v = hits[s]
            rec[s] = ({"n": len(v), "fwd_mean": st.mean(v),
                       "win": sum(1 for x in v if x > 0) / len(v) * 100,
                       "lift": st.mean(v) - base_mean} if len(v) >= 20 else
                      {"n": len(v), "fwd_mean": None, "win": None, "lift": None})
        rows.append(rec)

    doc = {"note": "극단 플래그 감시 — 설계 출처는 사용자 제공 KBAM 시장 국면 모니터 "
                   "(2026-07-09) ④. 트리거는 그 문서 값 그대로, **적중률은 랩 자료로 다시 쟀다**. "
                   "매매 규칙이 아니라 감시판이다.",
           "as_of": d[-1], "spx": PX[-1], "fwd_days": FWD,
           "base": {"n": len(base), "fwd_mean": base_mean, "win": base_win},
           "dropped": ["VIX 백워데이션(VIX3M 없음)", "VVIX", "풋콜 극단", "F&G 극단",
                       "챔피언 보유 동조성"],
           "flags": rows}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    on = sum(1 for r in rows if r["now"] == "ON")
    warn = sum(1 for r in rows if r["now"] == "주의")
    print("기준 %s · S&P %.0f · 플래그 %d개 (ON %d · 주의 %d)"
          % (d[-1], PX[-1], len(rows), on, warn))
    print("기준선 — 아무 날이나 사면 1개월 %+.2f%% · 승률 %.0f%% (n=%d)"
          % (base_mean, base_win, len(base)))
    print("\n %-18s %-5s %-22s %8s %7s %8s %6s"
          % ("플래그", "상태", "현재값", "ON 1개월", "승률", "기준선차", "횟수"))
    for r in rows:
        o = r["ON"]
        print(" %-18s %-5s %-22s %8s %7s %8s %6d"
              % (r["ko"][:18], r["now"], (r["value"] or "")[:22],
                 "—" if o["fwd_mean"] is None else "%+.2f%%" % o["fwd_mean"],
                 "—" if o["win"] is None else "%.0f%%" % o["win"],
                 "—" if o["lift"] is None else "%+.2f%%p" % o["lift"], o["n"]))
    print("\n뺀 것(자료 없음): %s" % " · ".join(doc["dropped"]))
    print("→ %s" % os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
