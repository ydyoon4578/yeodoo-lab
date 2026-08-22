# -*- coding: utf-8 -*-
"""build/refresh_fedwatch.py — 연방기금 선물이 말하는 «인상·인하 확률» → data/fedwatch.json

무엇을 만드나. CME FedWatch 와 같은 것을 같은 산식으로 만든다:
  ① 30일 연방기금 선물(ZQ) 월물 가격 → 월별 내재 평균 실효금리(= 100 − 가격)
  ② 회의별 «직후» 기대 금리
  ③ 회의를 거치며 갈라지는 목표범위 확률(조건부 회의 확률)

왜 이걸로 바꿨나(2026-08-22 사용자 결정). 종전 rates.html 은 금리 민감도 회귀·급등일
분석이었는데 «별 도움이 안 된다» 는 판단이었다. 대신 시장이 **지금 무엇을 가격에 넣고
있는가**를 보여주는 쪽이 낫다 — 그게 이 표다.

🚨 이 랩의 규약대로, 산식은 **검산되지 않으면 안 나간다.** GOLD 에 CME 가 공표한 표를
   박아 두고 매 실행마다 대조한다(같은 선물 가격 → 같은 확률). 어긋나면 멈춘다.
   시제품 실측(2026-08-22 · 선물 13개월): 8회의 40여 칸 최대 오차 **1.33%p**.
   ⚠ 0 이 아닌 이유는 입력 반올림이다 — CME 표는 소수 1자리, 선물 가격은 0.0025 눈금.
     그래서 허용치를 1.6%p 로 둔다. 이 수를 **결과를 보고 늘리지 않는다.**

산식의 함정 둘(둘 다 처음에 밟았다):
  · 시작 금리를 목표범위 중앙(3.625)으로 잡으면 안 된다. **회의가 없는 첫 달의 선물이
    말하는 값**(3.63)이 앵커다. 중앙을 쓰면 첫 회의 확률이 42.8% 로 나온다(정답 39.9%).
  · 회의가 월말에 붙은 달(10/28 → 남은 3일)에서 그 달 식으로 역산하면 오차가 10배로
    증폭돼 뒤쪽 회의가 −4% 같은 값으로 터진다. **다음 달에 회의가 없으면 그 달 값을
    직접 읽는다** — 그게 곧 그 회의 직후 금리다.

자료(둘 다 무료·자동):
  · 선물: yfinance 의 ZQ 월물(ZQ{월코드}{연2자리}.CBT). 실측으로 CME 정산가와 일치했다
    (2026-08-22: ZQU26 96.325 · ZQZ26 96.14 — 사용자가 CME 에서 가져온 값과 같다).
  · 회의 일정: data/events.json 의 fomc (build/refresh_events.py 가 관리).

  python build/refresh_fedwatch.py
"""
from __future__ import annotations
import calendar
import datetime as dt
import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "fedwatch.json")

STEP = 0.25                 # 목표범위 폭
N_MONTHS = 14               # 앞으로 몇 달치 월물을 받나
TOL = 1.6                   # 골든 대조 허용치(%p) — 위 주석 참조. 결과 보고 늘리지 않는다.
MCODE = "FGHJKMNQUVXZ"      # 1월~12월 선물 월코드

# 🚨 골든 — CME FedWatch 가 공표한 표(2026-08-22 · 사용자 제공). 같은 선물 가격에서
#   이 확률이 재현되지 않으면 산식이 틀린 것이다. 가격도 함께 박아 둔다(입력이 같아야
#   출력을 견줄 수 있다).
GOLD_PX = {"2026-08": 96.3700, "2026-09": 96.3250, "2026-10": 96.2650, "2026-11": 96.2150,
           "2026-12": 96.1400, "2027-01": 96.1100, "2027-02": 96.0650, "2027-03": 96.0300,
           "2027-04": 95.9950, "2027-05": 95.9650, "2027-06": 95.9400, "2027-07": 95.9300,
           "2027-08": 95.9250}
GOLD_MEET = ["2026-09-16", "2026-10-28", "2026-12-09", "2027-01-27", "2027-03-17",
             "2027-04-28", "2027-06-09", "2027-07-28"]
GOLD_P = {
    "2026-09-16": {350: 60.1, 375: 39.9},
    "2026-10-28": {350: 46.8, 375: 44.3, 400: 8.8},
    "2026-12-09": {350: 28.4, 375: 45.3, 400: 22.8, 425: 3.5},
    "2027-01-27": {350: 22.5, 375: 41.8, 400: 27.5, 425: 7.5, 450: 0.7},
    "2027-03-17": {350: 16.4, 375: 36.6, 400: 31.4, 425: 12.9, 450: 2.5, 475: 0.2},
    "2027-04-28": {350: 14.3, 375: 34.0, 400: 32.0, 425: 15.3, 450: 3.9, 475: 0.5},
    "2027-06-09": {350: 12.3, 375: 31.3, 400: 32.3, 425: 17.6, 450: 5.4, 475: 1.0, 500: 0.1},
    "2027-07-28": {350: 12.1, 375: 30.9, 400: 32.3, 425: 17.9, 450: 5.7, 475: 1.1, 500: 0.1},
}


def ndays(ym):
    return calendar.monthrange(int(ym[:4]), int(ym[5:]))[1]


def solve(px, meets):
    """월별 선물가격 + 회의일 → (앵커금리, [(회의, 직후금리, 방법)…]).

    ⚠ 회의가 없는 달의 선물은 그 달 내내 유지되는 금리를 그대로 말한다 — 그것을 정본으로
      삼고, 회의가 있는 달만 식을 푼다. 그래야 월말 회의에서 오차가 안 터진다.
    """
    months = sorted(px)
    mset = {m[:7]: m for m in meets}
    if months[0][:7] in mset:
        raise SystemExit("첫 달에 회의가 있다 — 앵커로 쓸 «회의 없는 달» 이 없다")
    imp = {m: round(100 - px[m], 6) for m in months}
    r0 = imp[months[0]]
    out, r_cur = [], r0
    for i, ym in enumerate(months):
        mt = mset.get(ym)
        if not mt:
            r_cur = imp[ym]
            continue
        nxt = months[i + 1] if i + 1 < len(months) else None
        if nxt and nxt[:7] not in mset:
            r_end, how = imp[nxt], "다음 달 직접"
        else:
            d, n = int(mt[8:10]), ndays(ym)
            if n - d < 5:
                # 남은 날이 너무 적으면 역산이 불안정하다 — 그 회의는 싣지 않는다.
                # (억지로 풀면 뒤쪽 회의까지 통째로 망가진다 — 시제품에서 −4% 가 나왔다.)
                print("  ⚠ %s 는 월말(남은 %d일)이라 역산이 불안정 — 여기서 끊는다" % (mt, n - d))
                break
            r_end, how = (n * imp[ym] - d * r_cur) / (n - d), "월내 역산"
        out.append((mt, r_end, how))
        r_cur = r_end
    return r0, out


def tree(r0, path):
    """회의별 직후 금리 → 회의마다의 목표범위 확률 분포.

    각 회의에서 기대금리의 변화 Δ 를 25bp 로 나눈 값이 «한 칸 움직일 확률» 이고,
    나머지는 제자리다. 그것을 회의마다 합성(convolve)한다 — CME 의 조건부 회의 확률과
    같은 구성이다(시제품에서 40여 칸을 1.33%p 안에서 재현).
    ⚠ |Δ| 가 25bp 를 넘으면 한 회의에 두 칸 이상 움직이는 것인데, 그때는 확률을 1 로
      묶고 남은 몫을 다음 칸으로 넘긴다(50bp 인상/인하를 그렇게 표현한다).
    """
    lo0 = STEP * int(round(r0 / STEP - 0.5))      # 지금 목표범위의 하한
    dist, prev, rows = {0: 1.0}, r0, []
    for mt, r, _how in path:
        d = (r - prev) / STEP
        step = 1 if d >= 0 else -1
        rem = abs(d)
        while rem > 1e-9:
            p = min(1.0, rem)
            nd = {}
            for k, v in dist.items():
                nd[k] = nd.get(k, 0.0) + v * (1 - p)
                nd[k + step] = nd.get(k + step, 0.0) + v * p
            dist = {k: v for k, v in nd.items() if v > 1e-7}
            rem -= p
        prev = r
        rows.append({"d": mt, "rate": round(r, 4),
                     "p": {int(round((lo0 + k * STEP) * 100)): round(v * 100, 1)
                           for k, v in sorted(dist.items()) if v * 100 >= 0.05}})
    return lo0, rows


def check_gold():
    """골든 대조 — 같은 입력에서 CME 표가 재현되는가. 안 되면 아무것도 안 쓴다."""
    r0, path = solve(GOLD_PX, GOLD_MEET)
    _lo, rows = tree(r0, path)
    mx, worst = 0.0, None
    for row in rows:
        g = GOLD_P.get(row["d"])
        if not g:
            continue
        for lo, want in g.items():
            got = row["p"].get(lo, 0.0)
            if abs(got - want) > mx:
                mx, worst = abs(got - want), (row["d"], lo, want, got)
    if mx > TOL:
        raise SystemExit("🚨 골든 대조 실패 — 최대 오차 %.2f%%p (%s %d-%d: CME %.1f vs 계산 %.1f). "
                         "허용치 %.1f%%p. 산식이 바뀌었거나 틀렸다 — 허용치를 늘려 넘기지 말 것."
                         % ((mx,) + worst[:2] + (worst[1] + 25,) + worst[2:] + (TOL,)))
    print("골든 대조 통과 — CME 표 대비 최대 오차 %.2f%%p (허용 %.1f)" % (mx, TOL))
    return mx


def fetch_px():
    """ZQ 월물 정산가. 못 받은 달은 그냥 빠진다(억지로 채우지 않는다)."""
    import yfinance as yf
    today = dt.date.today()
    px, miss, asof = {}, [], [""]
    y, m = today.year, today.month
    for _ in range(N_MONTHS):
        sym = "ZQ%s%02d.CBT" % (MCODE[m - 1], y % 100)
        ym = "%04d-%02d" % (y, m)
        try:
            h = yf.Ticker(sym).history(period="10d")
            v = float(h["Close"].dropna().iloc[-1]) if len(h) else None
        except Exception:
            v = None
        if v and 90 < v < 101:
            px[ym] = round(v, 4)
            try:
                d0 = str(h.index[-1].date())
                if d0 > asof[0]:
                    asof[0] = d0
            except Exception:
                pass
        else:
            miss.append(ym)
        m += 1
        if m > 12:
            m = 1; y += 1
    return px, miss, (asof[0] or today.isoformat())


def main() -> int:
    check_gold()

    ev = json.load(io.open(os.path.join(DATA, "events.json"), encoding="utf-8"))
    meets = sorted(f["d"] for f in (ev.get("fomc") or []) if f.get("d"))
    px, miss, px_asof = fetch_px()
    if len(px) < 6:
        raise SystemExit("선물 월물을 %d개밖에 못 받았다 — 갱신 중단(이전본 유지)" % len(px))
    if miss:
        print("  못 받은 월물 %d개: %s" % (len(miss), ", ".join(miss)))
    # 앵커가 되려면 첫 달에 회의가 없어야 한다 — 있으면 그 달을 버리고 다음 달부터.
    months = sorted(px)
    mset = {m[:7] for m in meets}
    while months and months[0][:7] in mset:
        px.pop(months[0]); months = sorted(px)
    fut = [m for m in meets if m[:7] in {x[:7] for x in months} and m >= months[0]]

    r0, path = solve(px, fut)
    lo0, rows = tree(r0, path)
    print("앵커 %s = %.4f%% · 현재 목표범위 %d-%d · 회의 %d개"
          % (months[0], r0, round(lo0 * 100), round(lo0 * 100) + 25, len(rows)))
    for row in rows:
        top = max(row["p"].items(), key=lambda kv: kv[1])
        print("  %s  기대 %.3f%%  최빈 %d-%d %.1f%%" % (row["d"], row["rate"], top[0], top[0] + 25, top[1]))

    doc = {
        "note": "연방기금 선물이 말하는 목표범위 확률(CME FedWatch 와 같은 산식). "
                "선물 = yfinance ZQ 월물 · 회의 일정 = data/events.json.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # 🚨 as_of 는 **자료 기준일**이지 마지막 월물이 아니다. 처음에 max(months) 를 넣었다가
        #   화면이 «2027-09 기준» 이라고 말했다 — 1년 뒤 날짜다. 선물 종가의 날짜를 쓴다.
        "as_of": px_asof,
        "anchor": {"month": months[0], "rate": round(r0, 4),
                   "lo": int(round(lo0 * 100)), "hi": int(round(lo0 * 100)) + 25},
        "futures": [{"m": m, "px": px[m], "imp": round(100 - px[m], 4)} for m in months],
        "meetings": [{"d": mt, "rate": round(r, 4), "how": how} for mt, r, how in path],
        "rows": rows,
        "gold_err": round(check_gold(), 2),
        "limits": [
            "🚨 확률이 아니라 **가격에서 뽑아낸 확률**이다. 시장이 그렇게 될 것이라는 뜻이 "
            "아니라 지금 선물이 그 값에 거래되고 있다는 뜻이다 — 이 랩은 이 확률이 "
            "맞았는지 검증한 적이 없다.",
            "⚠ 한 회의에 25bp 씩만 움직인다고 본다. 50bp 는 두 칸 이동으로 표현되지만 "
            "«한 번에 50bp» 와 «두 번 25bp» 를 이 표는 구별하지 못한다.",
            "⚠ 선물은 **월평균 실효금리**를 담는다. 목표범위 안에서 실효금리가 어디에 "
            "앉는지(보통 중앙 근처)는 시기에 따라 달라지고, 그 차이가 확률로 새어 든다.",
            "⚠ CME 공표값과 소수점 차이가 난다(실측 최대 %.2f%%p). 입력 반올림 탓이다 — "
            "정확한 값이 필요하면 CME 원문을 볼 것." % TOL,
        ],
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s (%.1fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
