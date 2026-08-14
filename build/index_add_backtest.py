# -*- coding: utf-8 -*-
"""지수 편입 효과 — 사전등록 PREREG-2026-08-14-INDEXADD.md

최근 K개월 안에 지수에 **편입된 종목 전부**를 동일가중으로 든다. K ∈ {1,3,6}.
사건은 data/index_ledger.json 의 월별 add 이고, 가격은 랩 본편과 같은 격자를 쓴다.

🚨 편출은 안 잰다. 10년 창 SPX 편출 242건 중 가격이 있는 것이 8건뿐이고 그 8종은
  '편출됐는데 오늘 유니버스에 남아 있는' 종목이다 — 살아남은 쪽만 남은 표본이라
  거기서 반등을 재면 생존편향 그 자체를 재게 된다. 등록 §2 참조.

⚠ 재는 것은 '편입 발표 효과' 가 아니다. 편입은 월 중에 발효되고 이 격자는 월말이라
  발표~발효 상승은 이미 지나간 뒤에 산다. 답하는 것은 **편입 이후 표류** 하나다.

⚠ 지표·대조군·구간은 랩 본편에서 그대로 가져온다(tech_backtest). 사본을 만들면
  이 규칙만 다른 자로 재게 되고, 이 저장소는 그 유형의 사고를 되풀이 밟았다.

    python build/index_add_backtest.py
"""
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tech_backtest as TB                                        # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "index_add.json")

HOLD_MONTHS = (1, 3, 6)      # 등록 §3 — 한 번만 돌린다. 다른 격자를 더 돌려 고르지 않는다.
IDX = (("spx", "S&P 500"), ("ndx", "나스닥 100"))


def main():
    led = json.load(io.open(os.path.join(DATA, "index_ledger.json"), encoding="utf-8"))
    dates, px, vlm, hid, lod, meta, rf = TB.load()
    n = len(dates)
    TB.MIN_HIST = max(TB.WARM0, n - int(TB.MAX_YEARS * 252))       # 랩과 같은 10년 상한
    me = TB.month_ends(dates)
    mi = {dates[i][:7]: i for i in me}                             # 월 → 월말 인덱스
    R = TB.daily_rets(px)
    bxr = TB.load_index_tr(dates)                                  # 대조군 = S&P 500(PR)
    bench = bxr.get("S&P 500") if isinstance(bxr, dict) else None
    if bench is None:
        raise SystemExit("대조군(S&P 500 PR)을 못 읽었다 — 판정을 낼 수 없다")

    rows = []
    for key, label in IDX:
        A = led["idx"][key]
        # 사건: 그 달 add 목록. 가격이 없는 종목은 애초에 들 수 없다(사는 척하지 않는다).
        ev = {}
        for m, r in A["m"].items():
            got = [t for t in (r.get("add") or []) if t in px]
            if got:
                ev[m] = got
        for K in HOLD_MONTHS:
            nav, srets, hold_n, turns = [100.0], [], [], 0
            cur = []                                               # [(티커, 편입월)]
            start_i = TB.MIN_HIST + 1
            for i in range(start_i, n):
                d = dates[i - 1]
                if (i - 1) in set(me):
                    mo = d[:7]
                    new = list(cur)
                    # K개월 지난 것을 뺀다 — 월 라벨 차이로 센다.
                    def _age(em):
                        return ((int(mo[:4]) - int(em[:4])) * 12
                                + int(mo[5:7]) - int(em[5:7]))
                    new = [(t, em) for t, em in new if _age(em) < K]
                    for t in ev.get(mo, []):
                        if t not in [x[0] for x in new]:
                            new.append((t, mo))
                    if set(x[0] for x in new) != set(x[0] for x in cur):
                        a, b = set(x[0] for x in new), set(x[0] for x in cur)
                        turns += len(a ^ b) / max(1, len(a) + len(b))
                    cur = new
                ts = [t for t, _ in cur]
                rr = [R[t][i] for t in ts if R[t][i] is not None]
                v = sum(rr) / len(rr) if rr else 0.0
                nav.append(nav[-1] * (1 + v))
                srets.append(v)
                hold_n.append(len(ts))
            d2 = dates[start_i - 1:]
            st = TB.ann_stats(nav, d2, rf)
            bn = [100.0]
            for i in range(start_i, n):
                bn.append(bn[-1] * (1 + (bench[i] or 0.0)))
            bs = TB.ann_stats(bn, d2, rf)
            yrs = max(1e-9, (n - start_i) / 252.0)
            rows.append({
                "idx": key, "label": label, "hold_m": K,
                "name": "%s 편입 후 %d개월 보유" % (label, K),
                "metrics": st, "bench": bs,
                "excess_cagr": round((st.get("cagr") or 0) - (bs.get("cagr") or 0), 2),
                "d_sharpe": round((st.get("sharpe") or 0) - (bs.get("sharpe") or 0), 3),
                "t": TB.tstat(srets, [bench[i] or 0.0 for i in range(start_i, n)]),
                "turnover": round(turns / yrs, 2),
                "hold_avg": round(sum(hold_n) / max(1, len(hold_n)), 1),
                "hold_min": min(hold_n) if hold_n else 0,
                "hold_max": max(hold_n) if hold_n else 0,
                "n_events": sum(len(v) for m, v in ev.items() if m >= dates[start_i][:7]),
                "start": d2[0], "end": dates[-1], "n_days": len(d2),
            })
            print("  %-26s CAGR %6.2f%% (BM %6.2f) · 초과 %+6.2f%%p · 샤프 %.3f · t %5.2f "
                  "· 회전 %5.2f · 평균 %4.1f종(%d~%d)"
                  % (rows[-1]["name"], st.get("cagr") or 0, bs.get("cagr") or 0,
                     rows[-1]["excess_cagr"], st.get("sharpe") or 0, rows[-1]["t"] or 0,
                     rows[-1]["turnover"], rows[-1]["hold_avg"],
                     rows[-1]["hold_min"], rows[-1]["hold_max"]))

    doc = {
        "as_of": dates[-1], "prereg": "build/PREREG-2026-08-14-INDEXADD.md",
        "note": "최근 K개월 안에 지수에 편입된 종목 전부를 동일가중으로 든다. 사건은 "
                "data/index_ledger.json 의 월별 편입이고, 가격·대조군·구간은 랩 본편과 같다.",
        "limits": [
            "🚨 편출 효과는 재지 않았다. 10년 창 SPX 편출 242건 중 가격이 있는 것이 8건뿐이고 "
            "그 8종은 '편출됐는데 오늘 유니버스에 남아 있는' 종목이다 — 살아남은 쪽만 남은 "
            "표본이라 거기서 반등을 재면 생존편향 그 자체를 재게 된다.",
            "⚠ 이것은 '편입 발표 효과' 가 아니다. 편입은 월 중에 발효되고 이 격자는 월말이라 "
            "발표~발효 구간의 상승은 이미 지나간 뒤에 산다. 답하는 것은 편입 이후 표류 하나다.",
            "⚠ 위키 문서가 늦게 갱신된 달은 편입 관측이 실제보다 늦다 — 그만큼 진입이 늦어져 "
            "효과가 과소 측정된다. 방향은 알지만 크기는 모른다.",
            "⚠ 보유 종목 수가 달마다 다르다(그 기간에 몇이 편입됐느냐로 정해진다). "
            "종목 수가 적은 달은 한두 종목이 그 달 성과를 좌우한다 — hold_min 을 볼 것.",
            "무비용(gross)이다. 회전이 큰 규칙이라 비용 후를 반드시 같이 읽어야 한다.",
        ],
        "rows": rows,
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    print("\n→ %s · %d판" % (os.path.relpath(OUT, ROOT), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
