# -*- coding: utf-8 -*-
"""build/rrg.py — RRG 4분면으로 본 팩터 로테이션 → data/_rrg.json

사전등록: build/PREREG-2026-09-22-RRG.md (계산 전 커밋 6ea920f)

무엇을. 상대강도를 **수준**(RS-Ratio)과 **기울기**(RS-Mom) 두 축에 놓고 4분면을 만든다.
  RRG 가 파는 전제는 둘 —
    ① 주도(Leading) 사분면이 부진(Lagging) 사분면보다 낫다
    ② 회복 → 주도 → 약화 → 부진 으로 **시계 방향** 회전한다
  둘 다 잰다.

🚨 F3 이 이 검정의 함정이다. **RS-Mom 은 RS-Ratio 의 차분이라 시계 방향은 어느 정도
   구성상 강제된다.** 「시계가 반시계보다 많다」는 아무 증거가 아니다. 그래서 각 팩터의
   월수익을 창 안에서 뒤섞어 같은 산식으로 RRG 를 다시 만들고(셔플 200회) 그 귀무분포와
   견준다. 95 백분위를 못 넘으면 기각이다.

🚨 F5 — 같은 달의 110개 팩터는 같은 시장을 탄다. (팩터·달) 쌍을 독립으로 세면 t 가
   부푼다. 달 단위로 묶어 다시 재고 두 판정이 갈리면 보류.

⚠ 여기서 백테스트를 다시 돌리지 않는다. strategy_charts.json 과 strategy_index.json
   둘만 읽는다.

  python build/rrg.py
"""
from __future__ import annotations
import io, json, math, os, random, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_rrg.json")

BENCH = "S&P 500"
LOOK = 12            # 되돌아보기(개월) — 사전등록 고정
CUT = 100.0          # 4분면 컷 — 사전등록 고정
END = "2026-08"      # 검정 마지막 달. 2026-09 는 부분 달이라 뺀다
MIN_MO = 100         # 모집단 조건 — 월 계열 최소 길이
NSHUF = 200          # F3 셔플 횟수 — 사전등록 고정
F2_T = 1.5           # F2 문턱 — 이 랩이 다른 등록에서 쓴 값
F4_MIN = 500         # F4 — 사분면당 최소 관측
SEED = 20260922

Q = ["회복", "주도", "약화", "부진"]      # 시계 방향 차례 — 이 순서가 CW 정의다
QEN = {"회복": "Improving", "주도": "Leading", "약화": "Weakening", "부진": "Lagging"}


def mean(v):
    return sum(v) / len(v) if v else None


def sd(v):
    if len(v) < 2:
        return None
    m = mean(v)
    return (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** .5


def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    va, vb = sd(a), sd(b)
    den = (va * va / len(a) + vb * vb / len(b)) ** .5
    return (mean(a) - mean(b)) / den if den and den > 0 else None


def t1(v):
    """한 표본 t — 평균이 0 과 다른가."""
    if len(v) < 2:
        return None
    s = sd(v)
    return mean(v) / (s / len(v) ** .5) if s and s > 0 else None


def rrg_axes(rel):
    """상대 NAV 계열 → (RS-Ratio, RS-Mom). 앞 LOOK+1 칸은 None."""
    n = len(rel)
    ratio = [None] * n
    for i in range(LOOK - 1, n):
        w = rel[i - LOOK + 1:i + 1]
        m, s = mean(w), sd(w)
        ratio[i] = CUT + ((rel[i] - m) / s if s and s > 0 else 0.0)
    mom = [None] * n
    diff = [None] * n
    for i in range(1, n):
        if ratio[i] is not None and ratio[i - 1] is not None:
            diff[i] = ratio[i] - ratio[i - 1]
    for i in range(n):
        w = [diff[k] for k in range(max(0, i - LOOK + 1), i + 1) if diff[k] is not None]
        if len(w) < LOOK:
            continue
        m, s = mean(w), sd(w)
        mom[i] = CUT + ((diff[i] - m) / s if s and s > 0 else 0.0)
    return ratio, mom


def quad(r, m):
    if r is None or m is None:
        return None
    if r >= CUT:
        return "주도" if m >= CUT else "약화"
    return "회복" if m >= CUT else "부진"


def rel_from(rets, bret):
    """월수익(%) 쌍 → 상대 NAV(100 기준)."""
    out, f, b = [], 1.0, 1.0
    for x, y in zip(rets, bret):
        f *= 1 + x / 100.0
        b *= 1 + y / 100.0
        out.append(100.0 * f / b)
    return out


def cw_share(seq):
    """사분면 계열 → (시계 전이 수, 반시계 전이 수). 제자리·맞은편은 안 센다."""
    cw = ccw = 0
    for a, b in zip(seq, seq[1:]):
        if a is None or b is None or a == b:
            continue
        d = (Q.index(b) - Q.index(a)) % 4
        if d == 1:
            cw += 1
        elif d == 3:
            ccw += 1
    return cw, ccw


def main() -> int:
    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))
    IX = {s["sid"]: s for s in json.load(
        io.open(os.path.join(DATA, "strategy_index.json"), encoding="utf-8"))["items"]}
    bm = CH["idx_monthly"][BENCH]

    # ── 모집단 — 사전등록대로 고른다 ────────────────────────────────────
    F = []
    for sid, c in CH["charts"].items():
        s = IX.get(sid)
        mo = c.get("monthly") or []
        if not s or s.get("src") != "종목 전략" or s.get("role") != "수익엔진":
            continue
        if len(mo) < MIN_MO:
            continue
        rows = [(m["m"], m["r"]) for m in mo if m["m"] in bm and m["m"] <= END
                and m.get("r") is not None]
        if len(rows) < MIN_MO:
            continue
        F.append({"sid": sid, "name": s.get("name") or sid, "pit": bool(s.get("pit")),
                  "grade": s.get("grade"), "reb": s.get("reb_label"),
                  "months": [a for a, _b in rows], "r": [b for _a, b in rows]})
    print("팩터 %d종 · 벤치 %s · 창 ~%s · 되돌아보기 %d개월" % (len(F), BENCH, END, LOOK))

    # ── 축·사분면 ──────────────────────────────────────────────────────
    cells, per_month, tails = {q: [] for q in Q}, {}, []
    cwt = ccwt = 0
    for f in F:
        b = [bm[m] for m in f["months"]]
        rel = rel_from(f["r"], b)
        ratio, mom = rrg_axes(rel)
        qs = [quad(ratio[i], mom[i]) for i in range(len(rel))]
        a, c = cw_share(qs)
        cwt += a; ccwt += c
        f["_q"], f["_ratio"], f["_mom"] = qs, ratio, mom
        # 다음 달 초과 — 마지막 달은 앞이 없다
        for i in range(len(rel) - 1):
            q = qs[i]
            if q is None:
                continue
            ex = f["r"][i + 1] - b[i + 1]
            cells[q].append(ex)
            per_month.setdefault(f["months"][i], {}).setdefault(q, []).append(ex)
        last = len(rel) - 1
        if qs[last]:
            tails.append({"sid": f["sid"], "name": f["name"], "pit": f["pit"],
                          "grade": f["grade"], "reb": f["reb"], "q": qs[last],
                          "ratio": round(ratio[last], 2), "mom": round(mom[last], 2),
                          "tail": [{"m": f["months"][k],
                                    "x": round(ratio[k], 2), "y": round(mom[k], 2),
                                    "q": qs[k]}
                                   for k in range(last - 5, last + 1)
                                   if ratio[k] is not None and mom[k] is not None]})

    base = [x for v in cells.values() for x in v]
    stat = {q: {"n": len(v), "mean": mean(v),
                "win": (sum(1 for x in v if x > 0) / len(v) * 100) if v else None,
                "lift": (mean(v) - mean(base)) if v else None} for q, v in cells.items()}

    # ── F1·F2 — 주도 vs 부진 (묶지 않은 것) ─────────────────────────────
    lead, lag = cells["주도"], cells["부진"]
    f1_diff = (mean(lead) - mean(lag)) if (lead and lag) else None
    f1_hit = not (f1_diff is not None and f1_diff > 0)
    t_pool = welch(lead, lag)
    f2_hit = not (t_pool is not None and abs(t_pool) >= F2_T)

    # ── F5 — 달 단위로 묶어 다시 ────────────────────────────────────────
    md = []
    for m in sorted(per_month):
        d = per_month[m]
        if d.get("주도") and d.get("부진"):
            md.append(mean(d["주도"]) - mean(d["부진"]))
    t_clu = t1(md)
    f5_pass = (t_clu is not None and abs(t_clu) >= F2_T)
    f5_split = ((not f2_hit) != f5_pass)

    # ── F3 — 시계 방향이 산식이 강제하는 것보다 많은가 ───────────────────
    #   🚨 셔플로 귀무를 만든다. 월수익을 창 안에서 뒤섞으면 자기상관은 깨지고
    #     산식의 성질은 남는다 — 그게 이 대조군의 요점이다.
    rnd = random.Random(SEED)
    real = cwt / (cwt + ccwt) if (cwt + ccwt) else None
    null = []
    for _ in range(NSHUF):
        a = c = 0
        for f in F:
            r2 = f["r"][:]
            rnd.shuffle(r2)
            b = [bm[m] for m in f["months"]]
            ra, mo2 = rrg_axes(rel_from(r2, b))
            x, y = cw_share([quad(ra[i], mo2[i]) for i in range(len(r2))])
            a += x; c += y
        if a + c:
            null.append(a / (a + c))
    null.sort()
    p95 = null[int(.95 * len(null))] if null else None
    f3_hit = not (real is not None and p95 is not None and real > p95)

    thin = [q for q in Q if stat[q]["n"] < F4_MIN]
    f4_hit = bool(thin)

    verdict = ("측정 불가" if f4_hit else
               "기각" if (f1_hit or f3_hit) else
               "보류" if f5_split else "측정만")

    doc = {"note": "RRG 4분면 팩터 로테이션. 사전등록 PREREG-2026-09-22-RRG(커밋 6ea920f) "
                   "대로 계산 전에 실패조건을 못박았다. 되돌아보기·컷·산식 판은 그 문서 값 그대로다.",
           "as_of": END, "bench": BENCH, "look": LOOK, "cut": CUT,
           "n_factors": len(F), "n_obs": len(base),
           # ⚠ 여기 빼기표는 **하이픈(U+002D)** 이어야 한다. U+2212(진짜 빼기표)는
           #   맑은 고딕에 없어 종이에서 두부가 된다 — 실제로 한 번 냈다.
           "axis_note": "RS-Ratio = 100 + (RS - SMA12(RS))/SD12(RS) · "
                        "RS-Mom = 100 + (M - SMA12(M))/SD12(M), M = RS-Ratio 1개월 차분. "
                        "RS = 팩터 누적 / S&P 500 누적(100 기준).",
           "quadrants": {q: {"en": QEN[q], **stat[q]} for q in Q},
           "base_mean": mean(base),
           "f1": {"hit": f1_hit, "diff": f1_diff,
                  "n_lead": len(lead), "n_lag": len(lag),
                  "말": "주도 사분면의 다음 달 초과가 부진 사분면보다 큰가"},
           "f2": {"hit": f2_hit, "t_pooled": t_pool, "문턱": F2_T},
           "f3": {"hit": f3_hit, "cw": cwt, "ccw": ccwt, "real": real,
                  "null_p95": p95, "null_median": null[len(null) // 2] if null else None,
                  "null_min": null[0] if null else None, "null_max": null[-1] if null else None,
                  "n_shuffle": NSHUF,
                  "말": "시계 방향 회전이 산식이 강제하는 것보다 많은가(셔플 귀무 95%)"},
           "f4": {"hit": f4_hit, "thin": thin, "문턱": F4_MIN},
           "f5": {"split": f5_split, "t_clustered": t_clu, "n_months": len(md),
                  "mean_diff": mean(md),
                  "말": "달 단위로 묶어도 같은 판정인가"},
           "verdict": verdict,
           "positions": sorted(tails, key=lambda x: (Q.index(x["q"]), -x["ratio"]))}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    # ── 화면 ──────────────────────────────────────────────────────────
    print("\n기준 %s · 관측 %d(팩터·달) · 기준선 %+.3f%%" % (END, len(base), mean(base)))
    print("\n  %-6s %-11s %6s %9s %8s %10s" % ("사분면", "", "종수", "다음달", "승률", "기준선차"))
    cur = {}
    for p in tails:
        cur[p["q"]] = cur.get(p["q"], 0) + 1
    for q in Q:
        s = stat[q]
        print("  %-6s %-11s %4d칸 %8.3f%% %7.0f%% %+9.3f%%p   지금 %d종"
              % (q, QEN[q], s["n"], s["mean"], s["win"], s["lift"], cur.get(q, 0)))

    print("\n🚨 실패 조건")
    print("  F1 주도 − 부진 = %s  (주도 %d · 부진 %d) → %s"
          % ("%+.3f%%p" % f1_diff if f1_diff is not None else "—",
             len(lead), len(lag), "걸림 ✗" if f1_hit else "통과"))
    print("  F2 그 차이의 t(묶지 않음) = %s (문턱 %.1f) → %s"
          % ("%.2f" % t_pool if t_pool is not None else "—", F2_T,
             "구별 불가" if f2_hit else "통과"))
    print("  F3 시계 %d · 반시계 %d → 실제 %.1f%%  vs  셔플 귀무 중앙 %.1f%% · 95%% %.1f%%"
          % (cwt, ccwt, (real or 0) * 100,
             (null[len(null) // 2] if null else 0) * 100, (p95 or 0) * 100))
    print("     → %s" % ("걸림 ✗ 산식이 강제하는 만큼뿐" if f3_hit else "통과"))
    print("  F4 %d칸 미만 사분면 %s → %s"
          % (F4_MIN, thin or "없음", "측정 불가 ✗" if f4_hit else "통과"))
    print("  F5 달 단위 묶음 t = %s (달 %d) → %s"
          % ("%.2f" % t_clu if t_clu is not None else "—", len(md),
             "묶지 않은 것과 갈림 → 보류" if f5_split else "같은 판정"))
    if t_pool and t_clu:
        print("     묶지 않은 t %.2f → 묶은 t %.2f  (%.0f%% 로 %s)"
              % (t_pool, t_clu, abs(t_clu) / abs(t_pool) * 100,
                 "줄었다" if abs(t_clu) < abs(t_pool) else "늘었다"))
    print("\n판정: **%s**" % verdict)
    print("→ _rrg.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
