# -*- coding: utf-8 -*-
"""build/monotonicity.py — 팩터의 **단조성**을 잰다(Fan 2026 · Two Heads Are Better Than One).

논문: Jiawei Fan, "Two Heads Are Better Than One: t-Statistics and Monotonicity in the
      Factor Zoo" (Brandeis, 2026-08-26 · SSRN 7356759).
  팩터 품질을 두 축으로 본다 —
    t-stat        Q5−Q1 **양 끝** 차이의 강도
    Monotonicity  매월 Q1≤Q2≤Q3≤Q4≤Q5 가 성립한 **달의 비율**
  둘은 in-sample 에서 거의 무관하고(ρ = −0.08), 두 순위의 합이 상위 30%인 팩터가
  OOS 월 33.4bp, 하위 30%가 10.2bp 였다.

🚨 **이것은 측정이지 선택이 아니다.**
   여기서 나온 수로 «어느 규칙을 몇 종으로 담을지» 를 고치면, 이 랩이 2026-08-29 에
   폐기한 `nsel`(성적을 보고 N 을 고르던 절차)을 이름만 바꿔 되살리는 것이 된다.
   그 자유도의 값은 이미 측정돼 있다 — **33종에서 샤프 중앙 −0.114 · t 중앙 −0.62**
   (PREREG-2026-08-29-ASWRITTEN-RESULT §1-2). 이 산출물을 근거로 설계를 바꾸려면
   **새 사전등록**이 먼저다. 논문도 combined rank 를 «어느 팩터를 쓸지» 고르는 데 쓰지
   크기를 다시 고르는 데 쓰지 않는다.

🚨 **채점기를 다시 짜지 않는다.** tech_backtest.xsec_score_at() 을 그대로 부른다 —
   이 랩의 «유일한 횡단면 채점기» 이고, 사본을 만들면 어긋난다(그 파일 머리주석이
   하루에 넷을 그렇게 잡았다고 적어 뒀다). pit_backtest.py 가 같은 방식의 선례다.

🚨 **tech_strategies.json 을 건드리지 않는다.** 이 클론에는 data/_ratings_cache.json 이
   없어 revdrift 계열이 후보 0 이 된다. 전면 재실행이 금지인 이유가 그것이다
   (게시 산출물이 망가진다). 여기서는 TB 를 **읽기 전용**으로 빌려 쓰고 새 파일로만 낸다.
   ⚠ 투자의견 캐시가 필요한 규칙은 결과에서 빼고, 뺐다는 사실을 산출물에 적는다.

⚠ 무엇을 재는지 — **팩터**이지 게시된 전략이 아니다.
   논문 정의대로 «매월» 채점해 5분위로 나누고 1개월 보유한다. 게시 전략은 규칙마다
   리밸 주기(주·월·분기)와 바스켓 크기가 다르다. 그래서 여기 t 와 카드의 t 는 다르다.
   같아야 하는 값이 아니다 — 카드의 t 는 «그 설계» 의 t, 여기 t 는 «그 팩터» 의 t 다.

  python build/monotonicity.py            전체
  python build/monotonicity.py --limit 8  앞 8종만(연습)
"""
from __future__ import annotations
import io, json, os, sys, time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_monotonicity.json")
sys.path.insert(0, os.path.join(ROOT, "build"))
import tech_backtest as TB                                       # noqa: E402

NQ = 5                    # 논문과 같은 5분위
MIN_POOL = 50             # 한 달에 이보다 후보가 적으면 그달은 안 센다(분위당 10종)


def spearman(a, b):
    n = len(a)
    if n < 3:
        return None
    ra = sorted(range(n), key=lambda i: a[i])
    rb = sorted(range(n), key=lambda i: b[i])
    Ra, Rb = [0] * n, [0] * n
    for k, i in enumerate(ra):
        Ra[i] = k
    for k, i in enumerate(rb):
        Rb[i] = k
    ma, mb = sum(Ra) / n, sum(Rb) / n
    num = sum((Ra[i] - ma) * (Rb[i] - mb) for i in range(n))
    den = (sum((x - ma) ** 2 for x in Ra) * sum((x - mb) ** 2 for x in Rb)) ** 0.5
    return num / den if den else None


def tstat(v):
    n = len(v)
    if n < 3:
        return None
    m = sum(v) / n
    sd = (sum((x - m) ** 2 for x in v) / (n - 1)) ** 0.5
    return m / (sd / n ** 0.5) if sd > 0 else None


def fwd_ret(R, t, i, j):
    """티커 t 의 일자 i→j 누적 수익. 하나라도 결측이면 None."""
    c = 1.0
    r = R.get(t)
    if not r:
        return None
    for k in range(i + 1, j + 1):
        v = r[k]
        if v is None:
            return None
        c *= (1.0 + v)
    return c - 1.0


def main() -> int:
    lim = None
    if "--limit" in sys.argv:
        lim = int(sys.argv[sys.argv.index("--limit") + 1])

    t0 = time.time()
    TB.build_strats()
    TB._RAT = TB.load_ratings()          # 캐시 없으면 빈 dict — revdrift 계열만 후보 0
    no_rat = not TB._RAT
    print("규칙 %d종 등록 · 투자의견 캐시 %s"
          % (len(TB.STRATS), "없음(revdrift 계열 제외)" if no_rat else "있음"))

    dates, px, vlm, hid, lod, meta, rf = TB.load(full=True)
    n = len(dates)
    tickers = sorted(px)
    R = TB.daily_rets(px)
    me_list = TB.month_ends(dates)
    me = set(me_list)
    ixr, ix = [None], [100.0]
    for i in range(1, n):
        rs = [R[t][i] for t in tickers if R[t][i] is not None]
        r = sum(rs) / len(rs) if rs else 0.0
        ixr.append(r)
        ix.append(ix[-1] * (1 + r))
    ixvol = [TB.vol(ixr, i, 20) for i in range(n)]
    # 🚨 run() 과 **같은 모양**이어야 한다 — 키 하나라도 빠지면 KeyError 로 죽는다.
    X = {"FACP": TB.load_factor_proxies(dates), "FU": TB.load_fund(), "R": R,
         "dates": dates, "hid": hid, "lod": lod, "ixr": ixr, "ixvol": ixvol, "me": me,
         "me_list": me_list, "meta": meta, "px": px, "vlm": vlm, "tickers": tickers,
         "macd10": TB.macro_daily("DGS10", dates),
         "macfx": TB.macro_daily("DTWEXBGS", dates),
         "mac_real": TB.macro_level("DFII10", dates),
         "mac_curve": TB.macro_level("T10Y2Y", dates),
         "mac_usd": TB.macro_level("DTWEXBGS", dates)}
    # 창 — run() 과 같게 10년으로 자른다.
    TB.MIN_HIST = max(TB.WARM0, n - int(TB.MAX_YEARS * 252))
    idx = [i for i in range(len(dates)) if i in me and i >= TB.MIN_HIST]
    pairs = [(idx[k], idx[k + 1]) for k in range(len(idx) - 1)]
    print("격자 %d일 · 월말 %d개 · 창 %s~%s (%.1f년) · 준비 %.0f초"
          % (n, len(pairs), dates[pairs[0][0]], dates[pairs[-1][1]],
             len(pairs) / 12.0, time.time() - t0))

    xs = [S for S in TB.STRATS if S["kind"] == "xsec"]
    if lim:
        xs = xs[:lim]
    rows, skipped = [], []
    for z, S in enumerate(xs, 1):
        sid = S["sid"]
        qr = [[] for _ in range(NQ)]      # 분위별 월수익
        mono, sp, nm_ = 0, [], 0
        try:
            for (i, j) in pairs:
                sc, _ind, _cr = TB.xsec_score_at(S, i + 1, X)   # 신호일 = i
                if len(sc) < MIN_POOL:
                    continue
                ts = [t for _v, t in sc]                        # 점수 내림차순
                m = len(ts)
                qs = []
                ok = True
                for q in range(NQ):                             # q=0 → 최고점수
                    a, b = int(m * q / NQ), int(m * (q + 1) / NQ)
                    vals = [fwd_ret(R, t, i, j) for t in ts[a:b]]
                    vals = [v for v in vals if v is not None]
                    if len(vals) < 3:
                        ok = False; break
                    qs.append(sum(vals) / len(vals))
                if not ok:
                    continue
                qs = qs[::-1]                                   # Q1(최저) … Q5(최고)
                for q in range(NQ):
                    qr[q].append(qs[q])
                nm_ += 1
                if all(qs[k] <= qs[k + 1] for k in range(NQ - 1)):
                    mono += 1
                sp.append(spearman(list(range(NQ)), qs))
        except Exception as e:
            skipped.append({"sid": sid, "name": S["name"], "why": "계산 실패 — %s" % e})
            print("  [%3d/%d] %-18s 실패 %s" % (z, len(xs), sid, str(e)[:60]))
            continue
        if nm_ < 24:
            skipped.append({"sid": sid, "name": S["name"],
                            "why": "잴 수 있는 달이 %d개뿐(후보 부족)%s"
                                   % (nm_, " — 투자의견 캐시 없음" if no_rat and "revdrift" in sid else "")})
            continue
        ls = [qr[NQ - 1][k] - qr[0][k] for k in range(nm_)]      # Q5 − Q1
        spv = [x for x in sp if x is not None]
        rows.append({
            "sid": "t-" + sid, "name": S["name"], "arch": S.get("arch"),
            "n_months": nm_,
            "q_mean_pct": [sum(qr[q]) / nm_ * 100 for q in range(NQ)],
            "mono_pct": mono / nm_ * 100,
            "spearman_mean": (sum(spv) / len(spv)) if spv else None,
            "ls_mean_bp": sum(ls) / nm_ * 10000,
            "ls_t": tstat(ls),
        })
        if z % 10 == 0 or z == len(xs):
            print("  [%3d/%d] %-18s mono %5.1f%% · ls t %6.2f · %.0f초"
                  % (z, len(xs), sid, rows[-1]["mono_pct"],
                     rows[-1]["ls_t"] or 0, time.time() - t0))

    # ── Combined Rank ────────────────────────────────────────────────────
    def prank(vals, v):
        return sum(1 for x in vals if x < v) / (len(vals) - 1) * 100 if len(vals) > 1 else 50.0

    TS = [r["ls_t"] for r in rows if r["ls_t"] is not None]
    MO = [r["mono_pct"] for r in rows]
    for r in rows:
        r["rank_t"] = prank(TS, r["ls_t"]) if r["ls_t"] is not None else None
        r["rank_mono"] = prank(MO, r["mono_pct"])
        r["combined"] = ((r["rank_t"] or 0) + r["rank_mono"])

    doc = {"note": "팩터 단조성 — Fan(2026) Two Heads. **측정이지 선택이 아니다**; 이 수로 "
                   "설계를 바꾸려면 새 사전등록이 먼저다(nsel 폐기 규약).",
           "paper": {"a": "Jiawei Fan", "y": 2026,
                     "t": "Two Heads Are Better Than One: t-Statistics and Monotonicity "
                          "in the Factor Zoo", "ssrn": "7356759"},
           "method": "매월 말 tech_backtest.xsec_score_at 로 채점 → 5분위 → 1개월 보유 "
                     "동일가중. mono = Q1≤Q2≤Q3≤Q4≤Q5 인 달의 비율. ls_t = Q5−Q1 의 t.",
           "caveat": "게시 카드의 t 와 다르다 — 카드는 그 설계(주기·바스켓 크기)의 t 이고 "
                     "여기는 그 팩터를 매월 5분위로 잰 t 다. 같아야 하는 값이 아니다.",
           "window": [dates[pairs[0][0]], dates[pairs[-1][1]]],
           "n_q": NQ, "n": len(rows), "ratings_cache": bool(TB._RAT),
           "skipped": skipped, "rows": rows}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("\n잰 규칙 %d종 · 건너뛴 것 %d종 · %.0f초 → %s"
          % (len(rows), len(skipped), time.time() - t0, os.path.basename(OUT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
