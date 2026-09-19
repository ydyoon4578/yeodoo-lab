# -*- coding: utf-8 -*-
"""build/quarterly_report.py — 분기 보고 한 장. 손으로 하지 않는다.

매 분기 이것만 돌리면 된다.

  ① 지금 어느 국면인가        국면 축 다섯 · 삼분위
  ② 그래서 얼마를 기대하나     그 칸의 과거 실측(_regime_table.json)
  ③ 실제로 얼마였나           확정 잣대 B 의 분기·연초 이후 초과수익
  ④ 시장은 무엇을 가리고 있나   시장 폭 세 축(_breadth_gauge.json)
  ⑤ 설계를 의심할 자리인가     ②와 ③의 차

🚨 이 보고서는 **매매 신호가 아니다.** 국면으로 비중을 바꾸지 않는다 —
   이 랩은 국면 조건부 규칙을 10건 돌려 9건 기각했다(CGATE t 0.86).
   국면은 «지금 무엇을 기대할 것인가» 의 기준선이지 예보가 아니다.

  python build/quarterly_report.py            화면에 찍는다
  python build/quarterly_report.py --md 경로   마크다운으로도 쓴다
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import numpy as np
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
D18 = r"C:\Users\Win10\Documents\여두_20260918"
AX = {"①가치(HML)": "hml", "②모멘텀(MOM)": "mom", "③수익성(RMW)": "rmw",
      "④규모(SMB)": "smb", "⑤시장변동성": "vol"}
BUCKET_KEY = {"하위": "low", "중간": "mid", "상위": "high"}
FUND = "펀드(우량성장30)"
L = []


def say(s=""):
    print(s); L.append(s)


def fund_monthly():
    qg = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_monthly.pkl"))
    idx = pd.read_pickle(os.path.join(D18, r"02_우량성장_최소구성\qg_index.pkl"))
    ipr = dict(zip(idx.ym, idx.ret_pct / 100.0))
    X = pd.read_csv(os.path.join(D18, r"01_이관묶음\01_우량성장선별_산출물\idx_div_monthly_20260918.csv"))
    idiv = dict(zip(X.iloc[:, 0].astype(str), X.iloc[:, 4]))
    ret = {m: dict(zip(g.tkr, g.r_tr / 100.0)) for m, g in qg.groupby("ym")}
    sel, forms = {}, []
    for f, g in qg[qg.top30 == "Y"].groupby("ym"):
        if int(f[5:7]) in (3, 6, 9, 12):
            sel[f] = dict(zip(g.tkr, g.wtgt / 100.0)); forms.append(f)

    def add(y, k):
        t = int(y[:4]) * 12 + int(y[5:7]) - 1 + k
        return "%04d-%02d" % (t // 12, t % 12 + 1)
    out, prev = {}, {}
    for f in sorted(forms):
        w = sel[f]
        trade = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
        ch = False
        for k in (1, 2, 3):
            hm = add(f, k)
            if not ("2014-07" <= hm <= "2026-08"):
                continue
            r = ret.get(add(f, k - 1), {})
            ok = {t: v for t, v in w.items() if t in r}
            s = sum(ok.values())
            if s <= 0:
                continue
            g = sum(v / s * r[t] for t, v in ok.items())
            out[hm] = g - (trade * 0.0025 if not ch else 0.0)
            ch = True
            w = {t: (v / s) * (1 + r[t]) for t, v in ok.items()}
            z = sum(w.values()); w = {t: v / z for t, v in w.items()}
        prev = w
    ms = sorted(m for m in out if m in ipr and m in idiv and pd.notna(ipr[m]))
    return pd.Series([out[m] - (ipr[m] + idiv[m]) for m in ms],
                     index=pd.PeriodIndex(ms, freq="M"))


def main():
    need = ["_regime_table.json", "ff_daily.json"]
    for f in need:
        if not os.path.exists(os.path.join(DATA, f)):
            print("❌ %s 없음 — build/regime_table.py 를 먼저 돌린다" % f); return 1
    RT = json.load(io.open(os.path.join(DATA, "_regime_table.json"), encoding="utf-8"))
    ff = json.load(io.open(os.path.join(DATA, "ff_daily.json"), encoding="utf-8"))
    F = pd.DataFrame(ff["series"], index=pd.to_datetime(ff["dates"])) / 100.0
    MF = (1 + F).groupby(F.index.to_period("M")).prod() - 1
    cum = {c: (1 + MF[c]).rolling(12).apply(np.prod, raw=True) - 1
           for c in ("hml", "mom", "rmw", "smb")}
    cum["vol"] = F.mkt_rf.groupby(F.index.to_period("M")).std() * np.sqrt(252)

    say("=" * 74)
    say("  우량성장 선별 30 — 분기 보고    (%s 작성 · 국면 기준일 %s)"
        % (dt.date.today().isoformat(), ff["end"]))
    say("=" * 74)

    # ── ① 지금 어느 국면인가 ──────────────────────────────────────────────
    say("\n① 지금 어느 국면인가")
    say("   %-16s %9s %7s   %-24s %s" % ("축", "값", "칸", "그 칸의 과거 실측", "펀드에"))
    exp, buckets = [], {}
    for axn, key in AX.items():
        c = cum[key].dropna()
        q1, q2 = c.quantile(1 / 3), c.quantile(2 / 3)
        v = float(c.iloc[-1])
        b = "하위" if v <= q1 else ("중간" if v <= q2 else "상위")
        buckets[axn] = b
        row = RT["table"].get(axn, {}).get(FUND, {})
        mu = row.get(BUCKET_KEY[b])
        best = max((row.get(k) for k in ("low", "mid", "high")
                    if row.get(k) is not None), default=None)
        worst = min((row.get(k) for k in ("low", "mid", "high")
                     if row.get(k) is not None), default=None)
        mark = "—"
        if mu is not None and best is not None:
            mark = "✅ 유리" if mu >= best - 1e-9 else ("❌ 불리" if mu <= worst + 1e-9 else "➖ 중간")
            exp.append(mu)
        say("   %-16s %+9.3f %7s   월 %+6.3f%% (연 %+5.1f%%p)   %s"
            % (axn, v, b, mu if mu is not None else float("nan"),
               (mu or 0) * 12, mark))

    # ── ② 그래서 얼마를 기대하나 ──────────────────────────────────────────
    e = float(np.mean(exp)) if exp else float("nan")
    say("\n② 그래서 이 분기 기대치")
    say("   다섯 칸 평균 — 월 %+.3f%% = **연 %+.1f%%p**" % (e, e * 12))
    say("   ⚠ 축끼리 상관이 있어 더하기가 아니다. 그리고 국면은 사후에 안다 —")
    say("      다음 달이 어느 칸일지는 모른다. 이것은 예보가 아니라 기준선이다.")

    # 참고 — 최적·최악 국면
    rows = RT["table"]
    allv = [rows[a][FUND][k] for a in AX if FUND in rows.get(a, {})
            for k in ("low", "mid", "high") if rows[a][FUND].get(k) is not None]
    if allv:
        say("   참고 — 이 펀드의 국면별 폭: 월 %+.3f%% ~ %+.3f%% (연 %+.1f ~ %+.1f%%p)"
            % (min(allv), max(allv), min(allv) * 12, max(allv) * 12))

    # ── ③ 실제로 얼마였나 ─────────────────────────────────────────────────
    say("\n③ 실제로 얼마였나 (확정 잣대 B — 바스켓 TR − S&P 500 TR)")
    try:
        ex = fund_monthly()
        last = ex.index[-1]
        y = last.year
        ytd = ex[[i for i in ex.index if i.year == y]]
        q = ex.iloc[-3:]
        say("   최근 3개월  %+7.2f%%p   (%s ~ %s)"
            % ((np.prod(1 + q.to_numpy()) - 1) * 100, q.index[0], q.index[-1]))
        say("   %d년 누적    %+7.2f%%p   (%d개월)"
            % (y, (np.prod(1 + ytd.to_numpy()) - 1) * 100, len(ytd)))
        say("   전 구간 연율 %+7.2f%%p   (%d개월 · %s ~ %s)"
            % (ex.mean() * 1200, len(ex), ex.index[0], ex.index[-1]))
        gap = ytd.mean() * 100 - e
        say("\n⑤ 설계를 의심할 자리인가")
        say("   올해 월평균 %+.3f%% vs 기대 %+.3f%% → 차 %+.3f%%p/월" % (ytd.mean() * 100, e, gap))
        if gap < -0.5:
            say("   ⚠ 기대보다 월 0.5%p 넘게 나쁘다. **설계를 볼 자리다.**")
        elif gap < 0:
            say("   ➖ 기대보다 낮지만 폭이 작다. 국면으로 설명되는 범위다.")
        else:
            say("   ✅ 기대 이상이다. 국면이 불리한데 이겼다면 그것도 기록해 둔다.")
    except Exception as exn:
        say("   ⚠ 성과 계산 실패: %s" % exn)

    # ── ④ 시장 폭 ─────────────────────────────────────────────────────────
    say("\n④ 시장은 무엇을 가리고 있나 (우리 518종에서 직접)")
    bg = os.path.join(DATA, "_breadth_gauge.json")
    if os.path.exists(bg):
        B = json.load(io.open(bg, encoding="utf-8"))
        say("   기준일 %s" % B["as_of"])
        for k, v in B["today"].items():
            say("   %-24s %+9.2f  백분위 %3.0f%%" % (k, v["level"], v["pct"]))
        try:
            beat = B["today"]["②지수이긴비율 21일"]
            if beat["pct"] <= 20:
                say("   → 지수를 이긴 종목이 %.0f%% 뿐이다(백분위 %.0f). "
                    "**30종이 지수에 뒤지는 것이 정상인 국면이다.**"
                    % (beat["level"], beat["pct"]))
        except KeyError:
            pass
    else:
        say("   ⚠ _breadth_gauge.json 없음 — build/breadth_gauge.py 를 돌린다")

    say("\n" + "=" * 74)
    say("🚨 이 보고서로 비중을 바꾸지 않는다. 랩이 국면 조건부 규칙을 10건 중 9건")
    say("   기각했다(CGATE — 집중도로 국면을 가른 규칙 · t 0.86).")
    say("   이 표의 쓰임은 하나다 — «이 분기 부진이 설계 탓인가 국면 탓인가».")
    say("=" * 74)

    if "--md" in sys.argv:
        p = sys.argv[sys.argv.index("--md") + 1]
        io.open(p, "w", encoding="utf-8").write(
            "# 우량성장 선별 30 — 분기 보고\n\n```\n" + "\n".join(L) + "\n```\n")
        print("\n→ %s" % p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
