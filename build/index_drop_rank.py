# -*- coding: utf-8 -*-
"""build/index_drop_rank.py — 편출된 종목은 편출 전에 얼마나 컸나 → data/index_drop_rank.json

묻는 것. **지수에서 한때 상위 50% 안에 들었던 종목이 편출당한 적이 있나.**

왜 묻나. 이 랩의 모든 백테스트는 «오늘 지수에 있는 종목» 으로 돌면 생존편향이 낀다. 그런데
편향의 **크기**는 편출이 어디서 일어나는지에 달렸다. 꼬리(하위)만 잘려 나간다면 대형주만
쓰는 규칙은 편향에 덜 노출되고, 상위 절반에서도 빠져나간다면 어떤 규칙도 안전하지 않다.
이 파일은 그 질문에 수로 답한다.

무엇을 시총으로 보나.
  월말 종가(분할조정) × 그 시점 **보고된** 희석주식수(SEC XBRL `sh`, 백만주).
  🚨 주가는 분할조정인데 SEC 주식수는 당시 발행분이다. 그대로 곱하면 분할한 종목의 과거
    시총이 배수만큼 어긋난다(AAPL 2019 는 4배 작게 나온다). 그래서 보고일 **이후** 분할비를
    누적해 주식수를 오늘 기준으로 되맞춘다 — data/splits.json 이 그 용도로 있다.
  ⚠ 부동주가 아니라 발행주식수다. S&P 의 실제 편입 기준(부동주 조정 시총)과 다르다.
    순위를 반쪽으로 가르는 데는 충분하지만 «S&P 가 이 종목을 왜 뺐나» 를 답하지는 않는다.

무엇을 편출로 보나.
  **CIK 기준**이다. 티커로 세면 개명이 편출로 잡힌다(ANTM→ELV, FB→META). CIK 로 묶고
  index_history 의 cik_hist 로 별칭을 합친다.
  그리고 «마지막 달에 없고, 그 뒤로 안 돌아온 것» 만 편출로 센다. 위키 리비전은 한두 달
  흔들리는 자리가 있어(ANSS 가 3개월 ANSYS 로 적힌 구간) 한 달 결석을 편출로 세면 안 된다.
  그 흔들림 자체도 따로 세어 싣는다.

  python build/index_drop_rank.py
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
OUT = os.path.join(DATA, "index_drop_rank.json")

START = "2016-08"       # 편출 종목 가격 캐시(_pit_px_cache)가 덮는 창의 시작
MIN_COV = 0.80          # 그 달 멤버의 이만큼도 시총을 못 매기면 그 달은 순위를 안 낸다


def jload(p, d=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return d


def main() -> int:
    H = jload(os.path.join(DATA, "index_history.json"))
    if not H:
        print("❌ data/index_history.json 없음")
        return 1
    M = H["months"]
    months = [m for m in sorted(M) if m >= START]
    cikmap, cikhist = H["cik"], H["cik_hist"]
    names = H.get("cik_names") or {}

    # 별칭 지도 — 티커 → CIK, CIK → 티커들
    t2c = dict(cikmap)
    for c, ts in cikhist.items():
        for t in ts:
            t2c.setdefault(t, c)
    c2t = {}
    for t, c in t2c.items():
        c2t.setdefault(c, set()).add(t)

    # 가격
    sd_dates = (jload(os.path.join(DATA, "stocks.json")) or {}).get("pxd_dates") or []
    pitpx = jload(os.path.join(DATA, "_pit_px_cache.json"), {}) or {}
    splits = (jload(os.path.join(DATA, "splits.json"), {}) or {}).get("co") or {}

    _px_cache = {}

    def px_series(t):
        """티커 → {날짜: 종가}. 현재 종목은 data/sd, 편출 종목은 PIT 캐시."""
        if t in _px_cache:
            return _px_cache[t]
        out = None
        p = os.path.join(DATA, "sd", "%s.json" % t)
        if os.path.exists(p):
            d = jload(p)
            if d and d.get("pxd"):
                arr = d["pxd"]
                out = {sd_dates[i]: arr[i] for i in range(min(len(arr), len(sd_dates)))
                       if arr[i] is not None}
        if out is None and t in pitpx:
            out = {k: v for k, v in pitpx[t].items() if v is not None}
        _px_cache[t] = out or {}
        return _px_cache[t]

    _sh_cache = {}
    MC_LO, MC_HI = 50.0, 2e7     # 백만달러 — $50M 미만·$20조 초과는 자료가 깨진 것으로 본다
    # 분할비 판정 — 목록을 늘리는 대신 규칙으로 본다.
    # 🚨 처음에는 흔한 비 목록(…12·15·20…)으로 맞췄다가 **NKTR 의 1:14 를 놓쳤다**
    #   (실측 194.75M → 13.92M = 13.99배). 목록에 없는 비를 쓰는 회사가 있다.
    #   그래서 «60 이하의 정수 또는 반정수에 2% 안»으로 바꾼다. 상한 60 은 자료 사고를
    #   분할로 오인하지 않기 위한 것이다 — WAT 의 1,374배는 어떤 분할도 아니다.
    SPLIT_MAX = 60.0
    n_fallback, n_head_drop, n_trunc = [0], [0], [0]

    def split_like(j):
        """단절 배수 j 가 분할비로 설명되면 그 비를 준다. 아니면 None."""
        if not j or j <= 0:
            return None
        big = j if j >= 1 else 1.0 / j
        if big < 1.4 or big > SPLIT_MAX:
            return None
        near = round(big * 2.0) / 2.0                 # 정수 또는 반정수(1.5·2.5·7.5 …)
        if near < 1.4 or abs(big / near - 1.0) > 0.02:
            return None
        return near if j >= 1 else 1.0 / near

    def sh_series(t):
        """티커 → [(보고일, 백만주)] 내림차순. **오늘 기준으로 되맞춘 값**이다.

        🚨 이 측정에서 제일 잘 틀리는 자리다. 주가는 분할조정인데 SEC 주식수는 당시
          보고분이라, 안 맞추면 분할한 종목의 과거 시총이 배수째 어긋난다.

        🚨 처음에는 «보고일 이후 분할비를 곱한다» 로 짰다가 **AMZN 이 2021년에 $35조**로
          나왔다(실측 2026-08-16). 이유는 SEC 자료가 분기마다 다르다는 것이다 — 어떤
          기간은 분할 뒤 비교표시로 **이미 소급**돼 있고 어떤 기간은 아직 아니다. 이미
          소급된 값에 분할비를 또 곱하면 20배가 두 번 걸린다. 랩의 tech_backtest._rebase
          머리말이 같은 현상을 NFLX 에서 기록해 두었다(2025-11 ×10 · 분기마다 오르내림).
        그래서 **splits.json 을 곱하지 않는다.** 계열 자체의 단절만 보고, 그 단절이 흔한
          분할비와 맞을 때만 옛 값을 새 기준으로 끌어온다. 이미 소급된 구간은 단절이
          없으므로 아무 일도 일어나지 않는다 — 이 방식이 소급 여부를 알 필요를 없앤다.

        🚨 닻(최신 관측)이 깨져 있으면 계열 전체가 같이 깨진다. 실측: WAT 의 최근 두 분기가
          82,139M·98,204M 주다(정상은 59.8M). 이것을 닻으로 삼으면 과거 전부가 1,374배로
          부풀어 94개월이 통째로 버려졌다. 그래서 **닻부터 검사한다** — 그 보고일 주가와
          곱해 시총이 타당범위 밖이면 그 관측을 버리고 다음을 닻으로 삼는다.
        ⚠ 분할비와 안 맞는 큰 단절은 자료 사고로 보고 **거기서 끊는다**(그 이전은 안 쓴다).
          조용히 이어 붙이면 순위표가 통째로 뒤틀린다.
        ⚠ 주식으로 치른 대형 인수는 주식수를 한 분기에 크게 늘릴 수 있다. 그 배수가 우연히
          분할비와 맞으면 과거 시총이 실제보다 작아진다. 배수가 아니라 한 자리 오차라
          «상·하위 반» 판정을 뒤집기는 어렵지만, 되맞춘 종목 수를 산출물에 싣는다.
        """
        if t in _sh_cache:
            return _sh_cache[t]
        q = None
        for sub in ("fx", "fx_pit"):
            p = os.path.join(DATA, sub, "%s.json" % t)
            if os.path.exists(p):
                d = jload(p) or {}
                tag = (d.get("tags") or {}).get("sh") or {}
                if tag.get("q"):
                    q = tag["q"]
                    break
        if not q:
            _sh_cache[t] = []
            return []
        raw = sorted(((r[0], float(r[1])) for r in q if r and r[1] and r[1] > 0), reverse=True)
        S = px_series(t)

        def px_at(d0):
            ds = [d for d in S if d <= d0]
            return S[max(ds)] if ds else None

        # ① 닻 고르기 — 시총이 타당범위 안에 드는 첫 관측. 최대 3개까지만 버린다.
        head = 0
        while head < len(raw) - 1 and head < 3:
            p0 = px_at(raw[head][0])
            if p0 is None:
                break
            mc = p0 * raw[head][1]
            if MC_LO <= mc <= MC_HI:
                break
            head += 1
            n_head_drop[0] += 1
        raw = raw[head:]
        if not raw:
            _sh_cache[t] = []
            return []

        # ② 단절에서만 되맞춘다. 분할비와 안 맞는 단절은 사고로 보고 끊는다.
        ser, f, used = [(raw[0][0], raw[0][1])], 1.0, False
        for i in range(1, len(raw)):
            j = raw[i][1] / raw[i - 1][1]
            r = split_like(j)
            if r is not None:
                f /= r
                used = True
            elif j >= 1.9 or j <= 1.0 / 1.9:
                # 🚨 분할비와 안 맞는 큰 단절은 **되맞추지 않고 그냥 지나간다.**
                #   처음에는 여기서 끊었는데(그 이전을 안 씀), 그러면 M&A 로 주식수가 뛴
                #   종목이 통째로 날아간다 — TWX·AAL 처럼 **인수로 사라진 회사가 정확히
                #   그 부류**라 재려던 대상이 표에서 빠졌다(실측 2026-08-16 · 94종 끊김,
                #   상위 50% 편출이 14 → 10 으로 줄었다).
                #   분할이 아닌 주식수 변동은 실제 변동이므로 손대는 것이 오히려 틀린다.
                #   단발 단위오류(COP 2008 1.6M주, NVDA 2009 0.5M주)는 그 관측 하나만
                #   틀리고 시총 타당범위에서 걸린다 — 되맞추면 그 이전 전부가 오염된다.
                n_trunc[0] += 1
            ser.append((raw[i][0], raw[i][1] * f))
        if used:
            n_fallback[0] += 1
        _sh_cache[t] = ser
        return ser

    # 🚨 상한을 $5조로 뒀다가 **NVDA($5.45조)를 내가 버렸다**(2026-08-16 실측). 타당범위는
    #   깨진 자료를 걸러야지 실제 값을 걸러서는 안 된다 — 오늘 최대의 4배로 올려 둔다.
    #   (MC_LO·MC_HI 는 주식수 조립에서도 닻 검사에 쓰므로 위에서 정의한다.)
    SPAN_MAX = 200.0             # 멤버로 있던 기간 안에서 이 배수 넘게 움직인 계열은 못 믿는다
    rejected = {}
    _span_bad = {}

    def span_ok(t, win):
        """멤버 기간 안 최고가/최저가가 SPAN_MAX 를 넘으면 그 계열은 버린다.

        🚨 PARA 를 잡으려고 둔다. 그 계열은 2021~2023 내내 10만 달러 근처에 있다가
          2026-08 에 1.66 달러로 끝난다 — 하루치 급등락이 없어 단절 검사에 안 걸리고,
          시총도 $5조 상한 안에 들어와 «지수 시총 1위(2024-02)» 로 올라와 있었다.
          파라마운트가 아니라 다른 상장물이다.
        ⚠ 실측(2026-08-16): 멤버 기간 기준 200배를 넘는 티커는 **PARA 하나뿐**이다.
          NVDA(10년 약 100배)도 이 문턱에 안 걸린다. 문턱을 넘겨 버려지는 종목이 늘면
          그때는 문턱이 아니라 자료를 봐야 한다 — 그래서 버린 티커를 산출물에 싣는다.
        """
        k = (t, win)
        if k in _span_bad:
            return not _span_bad[k]
        S = px_series(t)
        v = [x for d, x in S.items() if x and win[0] <= d[:7] <= win[1]]
        bad = len(v) >= 30 and max(v) / min(v) > SPAN_MAX
        _span_bad[k] = bad
        return not bad

    def mcap(aliases, month, win):
        """월말 시총(백만달러). 별칭 중 값이 나오는 첫 티커를 쓴다.

        🚨 win 은 그 법인이 지수에 있던 기간이다. **그 밖의 가격은 안 읽는다** — 티커는
          재사용된다. 실측(2026-08-16): POM(2016년 편출)의 캐시에 2025-12 값이 있고 거기서
          하루 ×10.8 이 튄다. 다른 회사 가격이다.
        🚨 그러고도 남는 깨진 계열이 있어 타당범위를 둔다. 실측: PARA 캐시가 2021-02 에
          101,500달러로 시작해 2026-08 에 1.66달러로 끝난다 — 하루치 급등락이 없어 단절
          검사에 안 걸리지만 5년간 6만 배다. 파라마운트가 아니라 다른 상장물이다.
          범위를 벗어난 값은 **버리고 센다**(조용히 넘기면 순위표가 통째로 뒤틀린다).
        """
        end = month + "-31"
        for t in sorted(aliases):
            S = px_series(t)
            if not S:
                continue
            if not span_ok(t, win):
                rejected.setdefault(t, []).append((month, "span"))
                continue
            ds = [d for d in S if d[:7] <= month and win[0] <= d[:7] <= win[1]]
            if not ds:
                continue
            p = S[max(ds)]
            v = next((x for d0, x in sh_series(t) if d0 <= end), None)
            if not p or not v:
                continue
            mc = p * v
            if mc < MC_LO or mc > MC_HI:
                rejected.setdefault(t, []).append((month, round(mc)))
                continue
            return mc
        return None

    doc_idx = {}
    for idx, label in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        memb, ranks, cov_rows, flicker = {}, {}, [], []
        alias_m = {}                     # 월 → {cik: 그달 표기 티커들}
        for m in months:
            ts = M[m].get(idx) or []
            if not ts:
                continue
            cs = {}
            for t in ts:
                c = t2c.get(t)
                if c:
                    cs.setdefault(c, set()).add(t)
            memb[m] = set(cs)
            alias_m[m] = cs
        # 법인별 멤버 기간 — 티커 재사용 가격을 막는 창이다(mcap 머리말 참조)
        win = {}
        for m in months:
            for c in memb.get(m, ()):
                w = win.get(c)
                win[c] = (m, m) if not w else (min(w[0], m), max(w[1], m))
        for m in months:
            cs = alias_m.get(m)
            if not cs:
                continue
            vals = []
            for c, al in cs.items():
                # 🚨 별칭 전부가 아니라 **그 달 명단에 적힌 티커만** 쓴다. CBS·VIAC·PARA 는
                #   한 CIK 인데 상장 기간이 서로 다르다 — 별칭을 다 열어 주면 2024년에
                #   CBS 티커(2019년에 사라졌고 그 뒤 다른 것이 쓰고 있다) 가격을 집어
                #   시총 1위로 올려놨다(실측 2026-08-16 · 473종 중 1위).
                v = mcap(al, m, win[c])
                if v:
                    vals.append((v, c))
            cov = len(vals) / max(1, len(cs))
            cov_rows.append({"m": m, "n": len(cs), "priced": len(vals), "cov": round(cov * 100, 1)})
            if cov < MIN_COV or len(vals) < 20:
                continue
            vals.sort(reverse=True)
            n = len(vals)
            for i, (v, c) in enumerate(vals):
                ranks.setdefault(c, []).append((m, i + 1, n, round(100.0 * i / (n - 1), 1), v))

        last = months[-1]
        cur = memb.get(last, set())
        # 편출 = 마지막 달에 없다. 흔들림(중간 한두 달 결석 후 복귀)은 따로 센다.
        seen_all = set()
        for m in memb:
            seen_all |= memb[m]
        for c in sorted(seen_all):
            ms_in = [m for m in months if c in memb.get(m, set())]
            if len(ms_in) < 2:
                continue
            i0, i1 = months.index(ms_in[0]), months.index(ms_in[-1])
            if (i1 - i0 + 1) != len(ms_in):
                flicker.append({"cik": c, "n_in": len(ms_in),
                                "span": [ms_in[0], ms_in[-1]]})

        rows = []
        for c, rs in ranks.items():
            best = min(rs, key=lambda r: r[3])          # 가장 높이 올라간 달
            lastr = rs[-1]
            gone = c not in cur
            nm = ""
            for d in (names.get(c) or {}).values():
                nm = d
                break
            rows.append({
                "cik": c, "name": nm or "", "t": sorted(c2t.get(c, {c}))[:3],
                "gone": gone,
                "best_pct": best[3], "best_rank": best[1], "best_n": best[2], "best_m": best[0],
                "last_pct": lastr[3], "last_rank": lastr[1], "last_n": lastr[2], "last_m": lastr[0],
                "last_mcap": round(lastr[4]),
                "n_months": len(rs),
            })
        rows.sort(key=lambda r: r["best_pct"])

        ever50 = [r for r in rows if r["best_pct"] <= 50.0]
        g50 = [r for r in ever50 if r["gone"]]
        gone_all = [r for r in rows if r["gone"]]
        # 편출 직전 순위 분포
        buckets = {"상위 10%": 0, "10~25%": 0, "25~50%": 0, "50~75%": 0, "하위 25%": 0}
        for r in gone_all:
            p = r["last_pct"]
            k = ("상위 10%" if p <= 10 else "10~25%" if p <= 25 else
                 "25~50%" if p <= 50 else "50~75%" if p <= 75 else "하위 25%")
            buckets[k] += 1

        # 🚨 순위를 아예 못 매긴 편출 법인 — 이 측정의 **하한**을 정하는 수다.
        #   가격이나 주식수가 없어 빠지는데, 그 결측은 인수·상장폐지된 회사에 몰려 있다.
        #   즉 «상위 50%% 경험 후 편출» 수는 실제보다 적게 나온다.
        gone_all_c = seen_all - cur
        unranked = len(gone_all_c - set(ranks))
        doc_idx[idx] = {
            "label": label,
            "n_gone_total": len(gone_all_c),
            "n_gone_unranked": unranked,
            "months": [months[0], last],
            "n_entities": len(rows),
            "n_gone": len(gone_all),
            "n_ever_top50": len(ever50),
            "n_ever_top50_gone": len(g50),
            "pct_ever_top50_gone": round(100.0 * len(g50) / max(1, len(ever50)), 1),
            "last_pct_buckets": buckets,
            "coverage": {"min": min(c["cov"] for c in cov_rows) if cov_rows else None,
                         "median": sorted(c["cov"] for c in cov_rows)[len(cov_rows) // 2] if cov_rows else None,
                         "months_dropped": sum(1 for c in cov_rows if c["cov"] < MIN_COV * 100)},
            "flicker": len(flicker),
            "top50_gone": sorted(g50, key=lambda r: r["best_pct"])[:60],
            "rows": rows,
        }

        print("\n══ %s · %s ~ %s" % (label, months[0], last))
        print("  법인(CIK) %d · 편출 %d" % (len(rows), len(gone_all)))
        print("  한때 상위 50%% 안 %d개 중 **편출 %d개 (%.1f%%)**"
              % (len(ever50), len(g50), 100.0 * len(g50) / max(1, len(ever50))))
        print("  편출 직전 순위: " + " · ".join("%s %d" % (k, v) for k, v in buckets.items()))
        print("  🚨 편출 %d개 중 %d개는 가격·주식수가 없어 **순위를 아예 못 매겼다** — "
              "아래 수는 하한이다" % (len(gone_all_c), unranked))
        print("  커버리지 중앙 %.1f%% · 최저 %.1f%% · 순위 못 낸 달 %d"
              % (doc_idx[idx]["coverage"]["median"], doc_idx[idx]["coverage"]["min"],
                 doc_idx[idx]["coverage"]["months_dropped"]))
        for r in sorted(g50, key=lambda x: x["best_pct"])[:12]:
            print("    %-6s %-28s 최고 상위 %4.1f%%(%d/%d, %s) → 마지막 %4.1f%% · $%.0fB · %s"
                  % (r["t"][0], (r["name"] or "")[:28], r["best_pct"], r["best_rank"],
                     r["best_n"], r["best_m"], r["last_pct"], r["last_mcap"] / 1000.0, r["last_m"]))

    # 🚨 자기검증 — 마지막 달 계산 시총을 랩이 이미 아는 오늘 시총(stocks.json fund.mc,
    #   단위 억달러)과 맞춰 본다. 이 측정의 값은 «분할조정 주가 × 되맞춘 주식수» 라는
    #   두 단계 조립물이라 어느 한쪽이 어긋나도 순위가 조용히 뒤틀린다. 실제로 이번에
    #   PARA(깨진 계열)와 NKTR(분할 미보정)이 상위권에 올라와 있었고, 둘 다 이 대조를
    #   붙이기 전에는 «그럴듯한 수» 로 보였다. 한 번 맞은 것으로는 다음을 못 잡는다.
    chk = {}
    try:
        cur = {s["t"]: (s.get("fund") or {}).get("mc")
               for s in (jload(os.path.join(DATA, "stocks.json")) or {}).get("stocks", [])}
        last = doc_idx["spx"]["months"][1]
        rows = sorted((r for r in doc_idx["spx"]["rows"]
                       if not r["gone"] and r["last_m"] == last),
                      key=lambda r: -r["last_mcap"])[:20]
        er = []
        for r in rows:
            t = next((x for x in r["t"] if x in cur), None)
            mc = cur.get(t) if t else None
            if mc:
                er.append(abs(r["last_mcap"] / 1e6 / (mc / 1e4) - 1) * 100)
        if er:
            er.sort()
            chk = {"n": len(er), "median_err": round(er[len(er) // 2], 1),
                   "max_err": round(er[-1], 1)}
    except Exception as e:
        chk = {"error": str(e)[:120]}
    if chk.get("median_err") is not None:
        ok = chk["median_err"] <= 5.0
        print("\n자기검증 — 상위 %d종 오늘 시총 대조: 오차 중앙 %.1f%% · 최대 %.1f%% %s"
              % (chk["n"], chk["median_err"], chk["max_err"], "✅" if ok else "🚨 조립이 어긋났다"))
        if not ok:
            print("🚨 중앙 오차가 5%를 넘는다 — 순위표를 믿을 수 없다. 주가·주식수 조립을 볼 것")
    print("주식수 조립: 단절로 되맞춘 종목 %d · 깨진 닻 버림 %d · 분할 아닌 단절 통과 %d"
          % (n_fallback[0], n_head_drop[0], n_trunc[0]))
    print("시총이 타당범위 밖이라 버린 티커 %d %s" % (len(rejected), sorted(rejected)[:8]))
    for t in sorted(rejected):
        rs = rejected[t]
        print("    %-6s %d개월 · 예 %s" % (t, len(rs), rs[:3]))

    doc = {
        "note": "편출된 종목이 편출 전에 지수 안에서 얼마나 컸나. 시총 = 월말 분할조정 종가 × "
                "그 시점 보고 희석주식수(분할 되맞춤). 법인은 CIK 로 묶어 개명을 편출로 세지 않는다.",
        "generated": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limits": [
            "⚠ 부동주 조정 시총이 아니라 발행주식수 기준이다. S&P 의 실제 편입 기준과 다르므로 "
            "«왜 뺐나» 를 답하지 않는다. 순위를 반으로 가르는 데만 쓴다.",
            "⚠ 멤버십은 위키백과 리비전이라 발효일 정본이 아니다(index_history 머리말). 월 단위 "
            "근사이고 한두 달 흔들리는 자리가 있어 «마지막 달에 없는 것» 만 편출로 셌다.",
            "🚨 가격·주식수를 못 구한 법인은 순위에서 빠지는데, 그 결측은 **편출된 쪽에 몰려 "
            "있다**(인수·상장폐지된 회사일수록 자료가 없다). 그래서 이 표의 편출 수는 "
            "실제보다 **적게** 나오는 쪽으로 치우친다 — 커버리지를 같이 싣는 이유다.",
            "⚠ 인수·합병으로 사라진 것과 규모가 줄어 밀려난 것을 구별하지 않는다. 둘 다 "
            "«오늘 유니버스에 없다» 는 점에서 생존편향의 원인은 같지만 뜻은 다르다.",
        ],
        "min_cov": MIN_COV,
        "selfcheck": chk,
        "n_split_fallback": n_fallback[0], "n_anchor_drop": n_head_drop[0], "n_truncated": n_trunc[0],
        "rejected_tickers": {k: len(v) for k, v in sorted(rejected.items())},
        "idx": doc_idx,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("\n→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
