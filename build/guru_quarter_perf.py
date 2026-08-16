# -*- coding: utf-8 -*-
"""build/guru_quarter_perf.py — 운용사별 분기 성과 → data/guru_qperf.json

무엇을 재나. **그 운용사가 분기말에 신고한 포트폴리오가 다음 분기에 어떻게 됐나.**
  3월 31일 신고분 → 3월 31일 ~ 6월 30일 3개월 수익률
비중은 신고 가치(value) 비례이고, 분기 사이는 표류(매수후보유)로 둔다.

🚨 이것은 **따라 살 수 있었던 성과가 아니다.** 13F 는 분기말 45일 뒤에 공시되므로,
  3월 31일 포트폴리오를 3월 31일에 알 방법이 없다. 그러니 이 표가 답하는 것은
      "그들이 그 분기에 들고 있던 것이 어떻게 됐나"
  이지
      "그들을 따라 샀으면 얼마를 벌었나"
  가 아니다. 뒤쪽 질문은 build/guru_overlap_backtest.py 가 공시 지연을 태워서 답한다.
  ⚠ 이 구별을 화면이 흐리면 독자는 사후 성과를 매매 가능한 성과로 읽는다. 산출물의
    limits 와 화면 문구가 그 말을 먼저 한다.

⚠ 13F 는 **롱온리 미국주식 상장분만** 담는다. 공매도·채권·현금·해외분이 빠지므로 이 수치는
  그 운용사의 실제 성과가 아니라 '신고된 주식 바구니' 의 성과다.
⚠ 커버리지를 같이 싣는다. 가격을 못 찾은 종목은 비중에서 빼고 그 비율을 적는다 —
  많이 빠진 분기의 수익률은 그만큼 덜 믿을 값이다.

  python build/guru_quarter_perf.py
"""
from __future__ import annotations
import io
import json
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru_qperf.json")

MIN_COV = 0.60          # 가격이 이만큼도 안 잡히면 그 분기는 수치를 내지 않는다


def load(fn):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def idx_monthly(months, tk):
    """월말 지수 수익률 {달: 수익률}. ^GSPC(S&P 500) · ^NDX(나스닥 100) 둘 다 가격지수다."""
    a = load("assets.json") or {}
    dates, px = a.get("dates") or [], (a.get("px") or {}).get(tk) or []
    last = {}
    for d, p in zip(dates, px):
        if p is not None:
            last[d[:7]] = p
    out = {}
    for i in range(1, len(months)):
        p0, p1 = last.get(months[i - 1]), last.get(months[i])
        if p0 and p1 and p0 > 0:
            out[months[i]] = p1 / p0 - 1.0
    return out


def q_to_month(q):
    """분기말 날짜(2026-03-31) → 월 라벨(2026-03)."""
    return q[:7]


def main() -> int:
    G = load("guru_history.json")
    if not G:
        print("❌ data/guru_history.json 없음 — build/refresh_13f_history.py 를 먼저 돌릴 것")
        return 1
    months, P = G["months"], G["mpx"]
    mi = {m: i for i, m in enumerate(months)}
    names = G.get("names") or {}
    H = G.get("holdings") or {}
    quarters = sorted(H)
    spx = idx_monthly(months, "^GSPC")
    ndx = idx_monthly(months, "^NDX")
    if not spx or not ndx:
        print("❌ 대조군 지수를 못 읽었다(^GSPC/^NDX) — data/assets.json 을 먼저 갱신할 것")
        return 1

    def span_ret(series, m0, m1):
        """m0(제외) ~ m1(포함) 구간 누적 수익률. 월 라벨로 센다."""
        i0, i1 = mi.get(m0), mi.get(m1)
        if i0 is None or i1 is None or i1 <= i0:
            return None
        acc = 1.0
        for j in range(i0 + 1, i1 + 1):
            acc *= (1.0 + (series.get(months[j]) or 0.0))
        return acc - 1.0

    rows, per_mgr = [], {}
    for qi in range(len(quarters) - 1):
        q0, q1 = quarters[qi], quarters[qi + 1]
        m0, m1 = q_to_month(q0), q_to_month(q1)
        i0, i1 = mi.get(m0), mi.get(m1)
        if i0 is None or i1 is None or i1 <= i0:
            continue
        b_spx, b_ndx = span_ret(spx, m0, m1), span_ret(ndx, m0, m1)
        for cik, hold in (H.get(q0) or {}).items():
            tot = sum(v for v in hold.values() if v and v > 0)
            if tot <= 0:
                continue
            # 종목별 비중 × 그 구간 수익률. 가격이 없는 종목은 **빼고** 커버리지를 적는다.
            wsum, acc = 0.0, 0.0
            for t, v in hold.items():
                if not v or v <= 0:
                    continue
                arr = P.get(t)
                if not arr:
                    continue
                p0 = arr[i0] if i0 < len(arr) else None
                p1 = arr[i1] if i1 < len(arr) else None
                if p0 in (None, 0) or p1 is None:
                    continue
                w = v / tot
                wsum += w
                acc += w * (p1 / p0 - 1.0)
            if wsum < MIN_COV:
                continue
            r = acc / wsum                      # 잡힌 비중 안에서 재정규화
            row = {"cik": cik, "name": names.get(cik) or cik,
                   "q": q0, "to": q1, "ret": round(r * 100, 2),
                   "spx": None if b_spx is None else round(b_spx * 100, 2),
                   "ndx": None if b_ndx is None else round(b_ndx * 100, 2),
                   "cov": round(wsum * 100, 1), "n": len(hold)}
            row["vs_spx"] = None if b_spx is None else round((r - b_spx) * 100, 2)
            row["vs_ndx"] = None if b_ndx is None else round((r - b_ndx) * 100, 2)
            rows.append(row)
            per_mgr.setdefault(cik, []).append(row)

    # 운용사별 요약 — 이긴 분기 비율과 평균 초과. 줄 세우려는 것이 아니라 분포를 보이려는 것이다.
    summary = []
    for cik, rs in per_mgr.items():
        n = len(rs)
        ws = sum(1 for x in rs if (x.get("vs_spx") or 0) > 0)
        wn = sum(1 for x in rs if (x.get("vs_ndx") or 0) > 0)
        summary.append({
            "cik": cik, "name": names.get(cik) or cik, "n_q": n,
            "win_spx": round(100.0 * ws / n, 1), "win_ndx": round(100.0 * wn / n, 1),
            "avg_vs_spx": round(sum(x.get("vs_spx") or 0 for x in rs) / n, 2),
            "avg_vs_ndx": round(sum(x.get("vs_ndx") or 0 for x in rs) / n, 2),
            "last": rs[-1] if rs else None,
        })
    summary.sort(key=lambda x: -x["avg_vs_spx"])

    doc = {
        "note": "운용사별 분기 성과 — 분기말 신고 포트폴리오가 다음 분기말까지 어떻게 됐나. "
                "비중은 신고 가치 비례, 분기 사이는 표류(매수후보유).",
        "generated": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bench": {"spx": "S&P 500 가격지수(^GSPC)", "ndx": "나스닥 100 가격지수(^NDX)",
                  "note": "둘 다 가격지수(PR)라 배당이 빠진다 — 지수가 연 ~2%p 불리하다."},
        "limits": [
            "🚨 이것은 «따라 살 수 있었던 성과»가 아니다. 13F 는 분기말 45일 뒤에 공시되므로 "
            "3월 31일 포트폴리오를 3월 31일에 알 방법이 없다. 이 표가 답하는 것은 «그들이 그 "
            "분기에 들고 있던 것이 어떻게 됐나» 이지 «따라 샀으면 얼마를 벌었나» 가 아니다. "
            "뒤쪽 질문은 겹침 전략(공시 지연을 태운다)이 답한다.",
            "⚠ 13F 는 롱온리 미국주식 상장분만 담는다. 공매도·채권·현금·해외분이 빠지므로 "
            "이 수치는 그 운용사의 실제 성과가 아니라 «신고된 주식 바구니» 의 성과다.",
            "⚠ 분기 중 매매는 안 보인다. 3월 31일 명단을 6월 30일까지 그대로 들고 있었다고 "
            "가정한다 — 실제로는 그 사이 사고팔았을 것이고, 그만큼 이 수치와 갈린다.",
            "⚠ 가격을 못 찾은 종목은 비중에서 빼고 그 비율(cov)을 적는다. 커버리지가 낮은 "
            "분기는 그만큼 덜 믿을 값이다. %d%% 미만은 아예 싣지 않는다." % int(MIN_COV * 100),
            "무비용(gross)이다. 분기마다 갈아엎는 회전은 이 표에 안 실린다.",
        ],
        "n_rows": len(rows), "n_managers": len(per_mgr),
        "quarters": quarters,
        "summary": summary,
        "by_manager": per_mgr,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("운용사 %d곳 · 분기 관측 %d개 · %.0fKB"
          % (len(per_mgr), len(rows), os.path.getsize(OUT) / 1024))
    for s in summary[:6]:
        print("  %-26s %2d분기 · SPX 대비 평균 %+6.2f%%p (승률 %4.1f%%) · NDX 대비 %+6.2f%%p"
              % (s["name"][:26], s["n_q"], s["avg_vs_spx"], s["win_spx"], s["avg_vs_ndx"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
