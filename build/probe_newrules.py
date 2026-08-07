# -*- coding: utf-8 -*-
"""신규 후보 5종의 **실현가능성만** 잰다 — 성과는 재지 않는다.

🚨 이 스크립트는 성과를 절대 내지 않는다. 성과를 보고 후보·창·부호를 고르면 그건 검정이
  아니다(이 랩의 사전등록 규약). 여기서 답하는 것은 딱 셋이다:

    ① 그 신호를 **계산할 수 있는가** — 필요한 태그가 있는가
    ② 매 월말 **후보가 몇 종인가** — XSEC_MIN_POOL(30) 을 넘는가.
       못 넘으면 그 달은 '고른 것'이 아니라 '있는 것 전부'라 순위가 아무 일도 안 한다.
    ③ **언제부터** 쓸 수 있는가 — 창 길이와 태그 시작이 정하는 실효 시작일

  ②·③ 을 미리 안 재면 사전등록에 "표본 2010~"이라 적어 놓고 실제로는 2019년부터
  도는 규칙을 등록하게 된다. 이 저장소가 x-agrow 에서 실제로 겪은 사고다
  (후보 2~5종인데 start=2017-08 로 보고됐다).

후보(전부 논문 원식 · 출처는 PREREG 문서에 적는다):
  ① x-fscore  Piotroski F-Score          Piotroski 2000, JAR 38(Suppl)
  ② x-debtiss 순부채발행 회피            Spiess·Affleck-Graves 1999, JFE 54 / JKP 'Debt Issuance'
  ③ x-noa     순영업자산 회피            Hirshleifer·Hou·Teoh·Zhang 2004, JAE 38
  ④ x-illiq   Amihud 비유동성            Amihud 2002, JFM 5
  ⑤ x-indmom  산업 모멘텀                Moskowitz·Grinblatt 1999, JF 54
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import tech_backtest as T


def _pct(series, dt, back_days):
    """dt 시점 값과 그보다 back_days 앞선 시점 값을 함께 준다(둘 다 공시지연 반영)."""
    a = T.asof_fund(series, dt)
    b = T.asof_fund(series, T._shift(dt, -back_days))
    return a, b


def main():
    dates, px, vlm, hi, lo, meta, rf = T.load()
    FU = T.load_fund()
    me = T.month_ends(dates)
    R = T.daily_rets(px)
    tickers = sorted(px.keys())
    print("일봉 %d일 · 종목 %d종 · 월말 %d회 (%s ~ %s)"
          % (len(dates), len(tickers), len(me), dates[0], dates[-1]))
    print("후보 문턱 XSEC_MIN_POOL = %d\n" % T.XSEC_MIN_POOL)

    rows = {k: [] for k in ("x-fscore", "x-debtiss", "x-noa", "x-illiq", "x-indmom")}
    SEC = {t: (meta.get(t) or {}).get("sector") or "" for t in tickers}

    for mi in me:
        i = mi + 1
        if i >= len(dates):
            break
        dt = dates[mi]
        n = {k: 0 for k in rows}
        secs = {}
        for t in tickers:
            f = FU.get(t) or {}
            P = px[t]
            p0 = P[mi]

            # ── ① F-Score — 9신호 전부 계산 가능한 종목만 센다 ──────────────
            # 하나라도 못 내면 점수가 0~9 척도가 아니게 되어 다른 종목과 비교 불가다.
            ni, ni0 = _pct(f.get("ni_a") or f.get("ni"), dt, 365)
            cf = T.ttm2(f.get("cfo"), f.get("cfo_a"), dt)
            at, at0 = _pct(f.get("asset"), dt, 365)
            db, db0 = _pct(f.get("debt"), dt, 365)
            ca, ca0 = _pct(f.get("ca"), dt, 365)
            cl, cl0 = _pct(f.get("cl"), dt, 365)
            sh, sh0 = _pct(f.get("sh"), dt, 365)
            rv = T.ttm2(f.get("rev"), f.get("rev_a"), dt)
            rv0 = T.ttm2(f.get("rev"), f.get("rev_a"), T._shift(dt, -365))
            gp = T.ttm2(f.get("gp"), f.get("gp_a"), dt)
            gp0 = T.ttm2(f.get("gp"), f.get("gp_a"), T._shift(dt, -365))
            ni_t = T.ttm2(f.get("ni"), f.get("ni_a"), dt)
            ni_t0 = T.ttm2(f.get("ni"), f.get("ni_a"), T._shift(dt, -365))
            ok_f = all(x is not None for x in
                       (ni_t, ni_t0, cf, at, at0, db, db0, ca, ca0, cl, cl0,
                        sh, sh0, rv, rv0, gp, gp0)) and at0 and at and cl and cl0 and rv and rv0
            if ok_f:
                n["x-fscore"] += 1

            # ── ② 순부채발행 — 총부채 1년 증가율 ────────────────────────────
            if db is not None and db0 is not None and db0 > 0:
                n["x-debtiss"] += 1

            # ── ③ 순영업자산 — (부채 + 자본 − 현금) ÷ 직전 총자산 ───────────
            eq = T.asof_fund(f.get("eq"), dt)
            cs = T.asof_fund(f.get("cash"), dt)
            if all(x is not None for x in (db, eq, cs, at0)) and at0 > 0:
                n["x-noa"] += 1

            # ── ④ Amihud 비유동성 — |수익률| ÷ 거래대금, 252일 평균 ─────────
            V = vlm.get(t)
            if V is not None and mi >= 252:
                cn = 0
                for k in range(mi - 251, mi + 1):
                    r, v, p = R[t][k], V[k], P[k]
                    if r is not None and v and p and v > 0 and p > 0:
                        cn += 1
                if cn >= 200:              # 유효일 200/252 이상만 — 결측이 많으면 평균이 의미 없다
                    n["x-illiq"] += 1

            # ── ⑤ 산업 모멘텀 — 섹터가 붙어 있고 6개월 수익률이 계산되는 종목 ──
            s = SEC.get(t)
            r6 = T.ret(P, mi, 126)
            if s and r6 is not None:
                secs.setdefault(s, []).append(r6)
                n["x-indmom"] += 1

        for k in rows:
            rows[k].append((dt, n[k], len(secs)))

    print("%-10s %-12s %-12s %-9s %-9s" % ("규칙", "첫 유효월", "후보<30 달수", "후보 중앙", "마지막 후보"))
    print("-" * 60)
    for k, v in rows.items():
        ok = [(d, c) for d, c, _s in v if c >= T.XSEC_MIN_POOL]
        thin = sum(1 for _d, c, _s in v if 0 < c < T.XSEC_MIN_POOL)
        cs = sorted(c for _d, c, _s in v if c > 0)
        med = cs[len(cs) // 2] if cs else 0
        print("%-10s %-12s %-12s %-9d %-9d" %
              (k, ok[0][0] if ok else "—(없음)", "%d / %d" % (thin, len(v)), med, v[-1][1]))

    ns = [s for _d, _c, s in rows["x-indmom"]]
    print("\n산업 모멘텀 섹터 수 — 첫 달 %d · 중앙 %d · 마지막 %d"
          % (ns[0], sorted(ns)[len(ns) // 2], ns[-1]))
    print("\n⚠ 위 표에 성과는 없다. 이 프로브는 '잴 수 있는가'만 답한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
