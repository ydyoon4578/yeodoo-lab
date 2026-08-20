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

MIN_COV = 0.60

# ── 따라 사는 레그 — 공시 지연을 태운다 (2026-08-20 사용자 지시) ──────────────
# 「2개월 뒤에 샀다는 가정하에 백테스트를 진행해줘. 3월 말 포트는 5월 말에 사는걸로.
#   실제 내가 따라할수 있게끔」
#
# 규칙(하나뿐이고, 결과를 보고 바꾸지 않는다):
#   분기말 q 의 신고 포트폴리오를 **q 의 2개월 뒤 월말에 사서 다음 신고분을 살 때까지 든다.**
#   즉 3/31 신고분 → 5/31 매수 → 8/31 교체. 창이 빈틈없이 이어지므로 «항상 투자» 다.
#
# ✅ 이 지연이 실제로 충분한지 자료로 확인했다. guru_history.filed 의 접수일 1,325건:
#      최소 8일 · 중앙 45일 · 95분위 47일 · 최대 49일
#      «분기말 + 2개월 말일» 보다 늦게 접수된 건 **0건**
#    즉 이 규칙은 전 구간에서 실행 가능했다. 45일 법정기한보다 보수적이다.
#
# ⚠ 신고가 빠진 분기는 **직전 명단을 그대로 든다**(carried). 새 13F 가 안 나왔는데 파는 것이
#   오히려 규칙 밖의 행동이라서다. 27곳 중 26곳은 결손이 없고, 페어홈만 9분기 있다 —
#   그 운용사의 수치는 그만큼 무르게 읽어야 하므로 carried 를 행과 요약에 함께 싣는다.
# ⚠ 마지막 한두 분기는 창이 아직 안 끝나 빠진다(as-of 레그보다 짧다). 이건 결손이 아니라
#   «아직 안 일어난 일» 이다.
LAG_MONTHS = 2          # 가격이 이만큼도 안 잡히면 그 분기는 수치를 내지 않는다


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


    # ── 따라 사는 레그 ────────────────────────────────────────────────────
    # 🚨 **채점기를 새로 만들지 않는다.** 위 as-of 레그와 같은 비중(신고 가치 비례)·같은
    #   가격 행렬·같은 커버리지 규칙을 쓰고, **창만 2개월 민다.** 사본을 만들면 언젠가
    #   한쪽만 고쳐지고 두 수가 갈린다 — 이 저장소가 되풀이 밟은 자리다.
    def bask_ret(hold, j0, j1):
        """그 명단을 j0→j1(월 인덱스) 구간 들었을 때의 수익률과 잡힌 비중."""
        tot = sum(v for v in hold.values() if v and v > 0)
        if tot <= 0:
            return None, 0.0
        wsum, acc = 0.0, 0.0
        for t, v in hold.items():
            if not v or v <= 0:
                continue
            arr = P.get(t)
            if not arr or j0 >= len(arr) or j1 >= len(arr):
                continue
            p0, p1 = arr[j0], arr[j1]
            if p0 in (None, 0) or p1 is None:
                continue
            w = v / tot
            wsum += w
            acc += w * (p1 / p0 - 1.0)
        return (acc / wsum if wsum > 0 else None), wsum

    lag_rows, lag_mgr = [], {}
    ciks = sorted({c for q in quarters for c in (H.get(q) or {})})
    for cik in ciks:
        held, carried = None, 0          # 아직 안 산 상태 · 직전 명단을 며칠째 들고 있나
        for qi in range(len(quarters) - 1):
            q0, q1 = quarters[qi], quarters[qi + 1]
            cur = (H.get(q0) or {}).get(cik)
            if cur:
                held, carried = cur, 0
            elif held is not None:
                carried += 1            # 신고가 없으면 직전 명단을 그대로 든다
            if held is None:
                continue                # 이 운용사의 첫 신고 전 — 아직 살 것이 없다
            j0 = mi.get(q_to_month(q0)); j1 = mi.get(q_to_month(q1))
            if j0 is None or j1 is None:
                continue
            j0 += LAG_MONTHS; j1 += LAG_MONTHS
            if j1 >= len(months):       # 창이 아직 안 끝났다 — 결손이 아니라 미래다
                continue
            r, wsum = bask_ret(held, j0, j1)
            if r is None or wsum < MIN_COV:
                continue
            bs = span_ret(spx, months[j0], months[j1])
            bn = span_ret(ndx, months[j0], months[j1])
            row = {"cik": cik, "name": names.get(cik) or cik,
                   "q": q0, "buy": months[j0], "to": months[j1],
                   "ret": round(r * 100, 2),
                   "spx": None if bs is None else round(bs * 100, 2),
                   "ndx": None if bn is None else round(bn * 100, 2),
                   "vs_spx": None if bs is None else round((r - bs) * 100, 2),
                   "vs_ndx": None if bn is None else round((r - bn) * 100, 2),
                   "cov": round(wsum * 100, 1), "n": len(held),
                   "carried": carried}
            lag_rows.append(row)
            lag_mgr.setdefault(cik, []).append(row)

    # 누적 곡선 — 분기 창이 빈틈없이 이어지므로 그대로 이어 붙이면 «따라 산» 자산곡선이다.
    # 운용사별 «유니버스 안 가치 비율» — guru.json(벌크·필터 전)의 현재 분기 값이다.
    # 🚨 이 백테스트의 가장 큰 한계가 이 수다. guru_history 는 우리 유니버스(오늘의
    #   S&P 500 ∪ NDX) 안 보유만 남기므로, 여기서 «따라 산» 것은 신고 포트폴리오 전체가
    #   아니라 그 일부다 — 중앙 60% · 페어홈 3%. cov=100% 는 «걸러진 것 안에서 100%» 라
    #   이 수 없이 읽으면 오해가 된다. 행마다 붙여서 화면이 반드시 같이 말하게 한다.
    # ⚠ 과거 분기의 비율은 모른다(이력 파일이 밖 종목을 아예 안 실었다) — 현재 분기 값을
    #   대리로 쓰고 그렇게 적는다.
    _uni_pct = {}
    _gj = load("guru.json") or {}
    for _g in (_gj.get("managers") or []):
        _tv, _uv = _g.get("total_val"), _g.get("uni_val")
        if _tv and _uv is not None:
            _uni_pct[str(_g.get("cik"))] = round(100.0 * _uv / _tv, 1)

    lag_summary, lag_curve = [], {}
    for cik, rs in lag_mgr.items():
        nav = bs_ = bn_ = 100.0
        pts = [{"d": rs[0]["buy"], "nav": 100.0, "spx": 100.0, "ndx": 100.0}]
        for x in rs:
            nav *= 1.0 + (x["ret"] or 0) / 100.0
            bs_ *= 1.0 + (x["spx"] or 0) / 100.0
            bn_ *= 1.0 + (x["ndx"] or 0) / 100.0
            pts.append({"d": x["to"], "nav": round(nav, 2),
                        "spx": round(bs_, 2), "ndx": round(bn_, 2)})
        lag_curve[cik] = pts
        n = len(rs)
        yrs = n / 4.0
        def _cagr(v):
            return round(((v / 100.0) ** (1.0 / yrs) - 1.0) * 100, 2) if yrs > 0 and v > 0 else None
        lag_summary.append({
            "cik": cik, "name": names.get(cik) or cik, "n_q": n,
            "from": rs[0]["buy"], "to": rs[-1]["to"],
            "cagr": _cagr(nav), "cagr_spx": _cagr(bs_), "cagr_ndx": _cagr(bn_),
            "cum": round(nav - 100, 1), "cum_spx": round(bs_ - 100, 1), "cum_ndx": round(bn_ - 100, 1),
            "win_spx": round(100.0 * sum(1 for x in rs if (x.get("vs_spx") or 0) > 0) / n, 1),
            "win_ndx": round(100.0 * sum(1 for x in rs if (x.get("vs_ndx") or 0) > 0) / n, 1),
            "avg_vs_spx": round(sum(x.get("vs_spx") or 0 for x in rs) / n, 2),
            "avg_vs_ndx": round(sum(x.get("vs_ndx") or 0 for x in rs) / n, 2),
            "carried": sum(1 for x in rs if x["carried"] > 0),
            "uni_pct": _uni_pct.get(str(cik)),
        })
    # 🚨 정렬은 CAGR 이 아니라 **이름** 으로 둔다. 27곳을 성적순으로 늘어놓으면 그 자체가
    #   «위에서부터 고르라» 는 말이 된다 — 이 표는 고르라고 있는 것이 아니다.
    lag_summary.sort(key=lambda x: x["name"])

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
        # ── 따라 사는 레그(공시 지연 2개월). 위 as-of 와 **같은 채점기**, 창만 밀었다.
        "tradeable": {
            "lag_months": LAG_MONTHS,
            "rule": ("분기말 신고 포트폴리오를 그 2개월 뒤 월말에 사서 다음 신고분을 살 때까지 "
                     "든다(3/31 신고분 → 5/31 매수 → 8/31 교체). 신고가 빠진 분기는 직전 "
                     "명단을 그대로 든다."),
            "feasible": ("접수일 1,325건 실측 — 최소 8일 · 중앙 45일 · 최대 49일. «분기말+2개월 "
                         "말일» 보다 늦게 접수된 건은 0건이라 이 규칙은 전 구간에서 실행 "
                         "가능했다(법정기한 45일보다 보수적이다)."),
            "limits": [
                "🚨 **신고 포트폴리오 전체가 아니다.** 이력 자료가 이 랩의 유니버스(오늘의 "
                "S&P 500 ∪ NDX 518종) 안 보유만 남기므로, 여기서 따라 산 것은 그 안쪽 조각이다 "
                "— 값 기준 중앙 60%, 버크셔 97% 부터 페어홈 3% 까지 운용사마다 크게 다르다"
                "(uni_pct). 이 비율이 낮은 운용사의 수치는 그 운용사가 아니라 «그 운용사의 "
                "대형주 조각» 의 성과다.",
                "🚨 유니버스가 **오늘의** 구성이라 생존편향이 있다. 그때 들고 있다가 그 뒤 "
                "상장폐지·편출된 종목은 가격이 없어 빠졌다 — 남은 것은 살아남은 쪽이라 수치가 "
                "계통적으로 부풀려진 방향이다. 크기는 이 자료로 못 잰다.",
                "⚠ 여전히 무비용(gross)이다. 분기마다 명단을 통째로 갈아엎는 회전이 안 실렸다.",
                "⚠ 13F 는 롱온리 미국주식 상장분만 담는다 — 그 운용사의 실제 성과가 아니라 "
                "«신고된 주식 바구니» 를 따라 산 결과다.",
                "⚠ 매수·매도 시점을 **월말 종가**로 잡았다. 실제로는 공시 다음 날 살 수도 "
                "있고 그러면 수치가 달라진다 — 월 격자만 갖고 있어 그 이상 못 쪼갠다.",
                "⚠ 대조군은 가격지수(PR)라 배당이 빠진다 — 지수가 연 ~2%p 불리하다.",
                "⚠ 마지막 한두 분기는 창이 아직 안 끝나 빠져 있다(결손이 아니라 미래다).",
            ],
            "n_rows": len(lag_rows), "n_managers": len(lag_mgr),
            "summary": lag_summary, "by_manager": lag_mgr, "curve": lag_curve,
        },
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("운용사 %d곳 · 분기 관측 %d개 · %.0fKB"
          % (len(per_mgr), len(rows), os.path.getsize(OUT) / 1024))
    for s in summary[:6]:
        print("  %-26s %2d분기 · SPX 대비 평균 %+6.2f%%p (승률 %4.1f%%) · NDX 대비 %+6.2f%%p"
              % (s["name"][:26], s["n_q"], s["avg_vs_spx"], s["win_spx"], s["avg_vs_ndx"]))
    print()
    print("── 따라 사는 레그(공시 %d개월 뒤 매수) · %d곳 · 관측 %d분기 ──"
          % (LAG_MONTHS, len(lag_mgr), len(lag_rows)))
    print("  %-26s %-4s %-17s %8s %8s %8s  %s"
          % ("운용사", "분기", "구간", "연CAGR", "SPX", "NDX", "SPX승률"))
    for x in sorted(lag_summary, key=lambda r: -(r["cagr"] or -99)):
        print("  %-26s %4d %s~%s %+7.2f%% %+7.2f%% %+7.2f%%   %4.1f%%  유니버스내 %s%%%s"
              % (x["name"][:26], x["n_q"], x["from"], x["to"],
                 x["cagr"] or 0, x["cagr_spx"] or 0, x["cagr_ndx"] or 0, x["win_spx"],
                 x.get("uni_pct") if x.get("uni_pct") is not None else "?",
                 ("  ⚠직전명단 %d분기" % x["carried"]) if x["carried"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
