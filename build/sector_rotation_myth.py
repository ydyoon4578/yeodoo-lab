# -*- coding: utf-8 -*-
"""재현 — Molchanov & Stangl(2024) 「경기순환 섹터 로테이션이라는 신화」.

원문: *International Journal of Finance & Economics* 29(4), 4419–4442. DOI 10.1002/ijfe.2882.
규약: build/PREREG-2026-09-07-SRMYTH.md — **계산 전 커밋 3d1ace32**.

🚨 **게시용 규칙이 아니다.** 완전 예지(다음 고점·저점을 안다)를 쓰므로 실시간에 못 쓴다.
  전략 등록부에 안 올린다(등록 §7). 랩의 실시간판은 asset_backtest 의 a7-fidelity 다.

🚨 **음성 결과 논문의 재현이라 «안 나왔다» 가 자동으로 «맞았다» 가 되면 안 된다.**
  등록 §4 가 원문을 **반증하는** 조건 셋을 계산 전에 못박았고, 이 스크립트가 그 셋을
  기계로 판정해 산출물에 싣는다.
"""
import io
import json
import os
import random
import statistics as st
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

# ── 등록이 못박은 상수 — 결과를 보고 안 바꾼다 ──────────────────────────────
MKT = "SPY"
COST_BP = 20            # 랩 규약 왕복 20bp(원문의 Roll 실효 스프레드를 재현 못 한다)
BLOCK_M = 3             # 블록 부트스트랩 블록 길이(개월) = 랩 규약(한 분기)
REPS = 1000             # 무작위 로테이션 반복 — 등록 §5④
SEED = 20260907
MIN_STAGE_M = 10        # F2 — 단계 관측이 이보다 적으면 그 단계 수치를 안 싣는다

# 등록 §3 — Stovall(1996) 표 3 을 SPDR 섹터로 옮긴 것. ⚠ 내가 판단한 자리 둘은 등록에 밝혔다.
STAGE_MAP = {
    1: ["XLK"],                       # 확장초 — Technology · Transportation
    2: ["XLB", "XLI"],                # 확장중 — Basic materials · Capital goods · Services
    3: ["XLP", "XLV", "XLE"],         # 확장말 — Consumer staples · Healthcare · Energy
    4: ["XLU", "XLC"],                # 침체초 — Utilities · Telecom (XLC 는 2018-06 부터)
    5: ["XLY", "XLF"],                # 침체말 — Consumer cyclical · Financial
}
ALL_SEC = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
STAGE_NAME = {1: "확장초(I)", 2: "확장중(II)", 3: "확장말(III)",
              4: "침체초(IV)", 5: "침체말(V)"}


def load():
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    dates, px = A["dates"], A["px"]
    # 월말 인덱스
    me, prev = [], None
    for i, d in enumerate(dates):
        if prev is not None and d[:7] != prev[:7]:
            me.append(i - 1)
        prev = d
    me.append(len(dates) - 1)
    urec = (A.get("macro") or {}).get("USREC") or {}
    return dates, px, me, urec


def cycle_stages(urec):
    """NBER 월별 침체 더미 → 5단계 지도 {YYYY-MM: stage}. 미정의 달은 안 담는다.

    등록 §2 — 확장은 **다음 고점**을 알아야 3등분되므로, **끝나지 않은 확장은 단계가
    정의되지 않는다.** 억지로 나누지 않고 빼고, 그 사실을 산출물에 적는다.
    🚨 이것이 이 재현의 결과 하나다 — 완전 예지를 가정한 방법은 오늘 쓸 수가 없다.
    """
    ks = sorted(urec)
    ym = [k[:7] for k in ks]
    v = [int(urec[k]) for k in ks]
    segs, cur, kind = [], [], v[0]
    for i, x in enumerate(v):
        if x == kind:
            cur.append(ym[i])
        else:
            segs.append((kind, cur))
            cur, kind = [ym[i]], x
    segs.append((kind, cur))
    stage, undef = {}, []
    for si, (k, months) in enumerate(segs):
        first = (si == 0)
        last = (si == len(segs) - 1)
        n = len(months)
        if first or last:
            # 앞뒤가 잘린 구간은 «시작→끝» 을 모르므로 등분할 수 없다.
            #   ⚠ 다만 **첫 구간**은 그 앞 전환점이 자료 밖일 뿐 끝(다음 전환점)은 안다 —
            #     그래도 길이를 모르면 3등분이 안 되므로 똑같이 미정의로 둔다.
            undef.extend(months)
            continue
        if k == 0:                       # 확장 → 3등분
            b = [n * 1 // 3, n * 2 // 3]
            for j, m in enumerate(months):
                stage[m] = 1 if j < b[0] else (2 if j < b[1] else 3)
        else:                            # 침체 → 2등분
            h = n // 2
            for j, m in enumerate(months):
                stage[m] = 4 if j < h else 5
    return stage, undef


def monthly(px, dates, me, tick):
    """월말→월말 수익. 값이 없는 달은 None."""
    s = px.get(tick)
    out = {}
    for a, b in zip(me, me[1:]):
        pa = s[a] if s else None
        pb = s[b] if s else None
        out[dates[b][:7]] = ((pb / pa - 1.0) if (pa and pb and pa > 0) else None)
    return out


def run_basket(months, pick, R, cost_bp=COST_BP):
    """단계별 바스켓을 동일가중으로 굴린다. pick(m) → 티커 목록. 비용은 회전분에만."""
    rets, held = [], set()
    for m in months:
        cur = [t for t in pick(m) if R.get(t, {}).get(m) is not None]
        if not cur:
            rets.append((m, 0.0, 0.0))
            continue
        r = sum(R[t][m] for t in cur) / len(cur)
        turn = (len(set(cur) ^ held) / max(1, len(cur) + len(held))) if held else 1.0
        c = turn * (cost_bp / 10000.0)
        rets.append((m, r, r - c))
        held = set(cur)
    return rets


def stats(rs):
    """월 평균·표준편차(%) · 샤프(월). 원문 표 6 과 같은 눈금."""
    v = [x * 100 for x in rs]
    n = len(v)
    if n < 2:
        return {}
    m = sum(v) / n
    sd = st.stdev(v)
    return {"n": n, "mean": round(m, 3), "sd": round(sd, 3),
            "sharpe": round(m / sd, 3) if sd > 0 else None}


def beta(rs, bs):
    n = len(rs)
    mr, mb = sum(rs) / n, sum(bs) / n
    vb = sum((y - mb) ** 2 for y in bs)
    return round(sum((x - mr) * (y - mb) for x, y in zip(rs, bs)) / vb, 3) if vb else None


def block_boot(diff, reps=2000, seed=SEED):
    """차이 계열의 평균에 대한 블록 부트스트랩 p값(단측: 평균 ≤ 0 이라는 귀무).

    ⚠ 랩 규약과 같은 블록 길이(3개월). 원문도 블록 부트스트랩으로 유의성을 냈다.
    """
    n = len(diff)
    if n < 12:
        return None
    obs = sum(diff) / n
    c = [x - obs for x in diff]          # 귀무(평균 0)를 계열에 새긴다
    rnd = random.Random(seed)
    nb = (n + BLOCK_M - 1) // BLOCK_M
    hit = 0
    for _ in range(reps):
        idx = []
        for _b in range(nb):
            s0 = rnd.randrange(n)
            idx.extend((s0 + k) % n for k in range(BLOCK_M))
        idx = idx[:n]
        if sum(c[j] for j in idx) / n >= obs:
            hit += 1
    return round(hit / reps, 4)


def main():
    dates, px, me, urec = load()
    stage, undef = cycle_stages(urec)
    R = {t: monthly(px, dates, me, t) for t in ALL_SEC + [MKT]}
    have = sorted(set(R[MKT]) & set(stage))
    # 주 판정 창 — 단계가 정의된 달만. 진행 중 확장은 여기 안 든다(등록 F3).
    months = [m for m in have if R[MKT][m] is not None]
    if not months:
        raise SystemExit("겹치는 달이 없다 — 재현 불가.")
    cnt = {}
    for m in months:
        cnt[stage[m]] = cnt.get(stage[m], 0) + 1
    thin = {STAGE_NAME[s]: n for s, n in sorted(cnt.items()) if n < MIN_STAGE_M}

    def pick_rot(m):
        return [t for t in STAGE_MAP[stage[m]] if R.get(t, {}).get(m) is not None]

    def pick_mkt(m):
        return [MKT]

    def pick_time(m):
        # 원문의 «시장 타이밍» — 침체초(IV)만 현금, 나머지는 시장.
        return [] if stage[m] == 4 else [MKT]

    rot = run_basket(months, pick_rot, R)
    mkt = run_basket(months, pick_mkt, R, cost_bp=0)     # 매수후보유 — 회전 없음
    tim = run_basket(months, pick_time, R)

    g = {n: [r for _m, r, _c in x] for n, x in
         (("rot", rot), ("mkt", mkt), ("tim", tim))}
    gn = {n: [c for _m, _r, c in x] for n, x in
          (("rot", rot), ("mkt", mkt), ("tim", tim))}

    out = {
        "note": ("재현 — Molchanov & Stangl(2024) 「경기순환 섹터 로테이션이라는 신화」. "
                 "🚨 게시용 규칙이 아니다 — 완전 예지를 쓰므로 실시간에 못 쓴다."),
        "paper": {"title": "The myth of business cycle sector rotation",
                  "authors": "Molchanov, A. & Stangl, J.",
                  "journal": "International Journal of Finance & Economics 29(4) 4419-4442 (2024)",
                  "doi": "10.1002/ijfe.2882",
                  "reported": {"market": {"mean": 0.89, "sd": 4.30, "beta": 1.00, "sharpe": 0.21},
                               "rotation": {"mean": 1.05, "sd": 4.98, "beta": 1.01, "sharpe": 0.21},
                               "timing": {"mean": 1.07, "sd": 3.97, "beta": 0.85, "sharpe": 0.27},
                               "rotation_11sector": {"mean": 0.98, "sd": 5.54,
                                                     "beta": 1.10, "sharpe": 0.17},
                               "window": "1948-01~2022-05 · 경기순환 15개 · FF48 산업"}},
        "prereg": "build/PREREG-2026-09-07-SRMYTH.md (계산 전 커밋 3d1ace32)",
        "window": {"from": months[0], "to": months[-1], "n_months": len(months)},
        "undefined_months": {"n": len(undef), "note":
                             ("단계가 정의되지 않은 달 — 끝나지 않은 확장과 자료 앞 끝이다. "
                              "🚨 확장을 3등분하려면 다음 고점을 알아야 하므로, 이 방법은 "
                              "**진행 중인 국면에 쓸 수가 없다.** 억지로 나누지 않고 뺐다."),
                             "range": ([undef[0], undef[-1]] if undef else None)},
        "stage_months": {STAGE_NAME[s]: n for s, n in sorted(cnt.items())},
        "thin_stages": thin,
        "cost_bp": COST_BP, "block_months": BLOCK_M, "reps": REPS, "seed": SEED,
        "gross": {k: dict(stats(v), beta=beta(v, g["mkt"])) for k, v in g.items()},
        "net": {k: dict(stats(v), beta=beta(v, gn["mkt"])) for k, v in gn.items()},
    }

    # ── 등록 §4 의 반증 조건 셋을 **기계가** 판정한다 ────────────────────────
    d_rm = [a - b for a, b in zip(gn["rot"], gn["mkt"])]
    p_rm = block_boot(d_rm)
    c1 = (sum(d_rm) / len(d_rm)) > 0
    c2 = (p_rm is not None and p_rm < 0.05)
    c3 = ((out["net"]["rot"].get("sharpe") or -9) > (out["net"]["tim"].get("sharpe") or -9))
    out["vs_market"] = {"mean_diff_pp": round(sum(d_rm) / len(d_rm) * 100, 4),
                        "block_boot_p": p_rm}
    out["refutation"] = {
        "definition": ("등록 §4 — 원문을 반증하려면 셋을 «동시에» 만족해야 한다: "
                       "① 로테이션이 시장 대비 월 평균 초과 > 0 · ② 그 초과의 블록 "
                       "부트스트랩 p < 0.05 · ③ 로테이션이 시장 타이밍을 샤프에서 이긴다."),
        "c1_beats_market": bool(c1), "c2_significant": bool(c2),
        "c3_beats_timing": bool(c3),
        "refuted": bool(c1 and c2 and c3),
        "reading": ("원문이 이 창에서 **반증됐다**" if (c1 and c2 and c3)
                    else "원문의 주장이 이 창에서 **지지된다**"),
    }

    # ── 무작위 로테이션 — 우연이면 어디쯤인가(등록 §5④) ────────────────────
    rnd = random.Random(SEED)
    sizes = {s: len(STAGE_MAP[s]) for s in STAGE_MAP}
    rr = []
    for _ in range(REPS):
        amap = {}
        for s in STAGE_MAP:
            amap[s] = rnd.sample(ALL_SEC, sizes[s])
        rs = run_basket(months, lambda m, _a=amap: [
            t for t in _a[stage[m]] if R.get(t, {}).get(m) is not None], R)
        rr.append(sum(c for _m, _r, c in rs) / len(rs) * 100)
    rr.sort()
    act = out["net"]["rot"]["mean"]
    out["random_rotation"] = {
        "note": ("단계마다 섹터를 무작위로 배정해 %d회. 원문의 «random chance» 비교를 "
                 "이 랩으로 옮긴 것이다. 통념 매핑이 무작위 배정보다 나은가를 본다." % REPS),
        "median": round(rr[len(rr) // 2], 3), "p05": round(rr[int(.05 * REPS)], 3),
        "p95": round(rr[int(.95 * REPS)], 3),
        "actual_mean": act,
        "pct_rank": round(sum(1 for x in rr if x < act) / REPS, 3),
        "reading": ("통념 매핑이 무작위 배정 %d%% 지점에 선다 — 50%% 근처면 «우연과 구별 안 됨»"
                    % round(sum(1 for x in rr if x < act) / REPS * 100)),
    }

    # ── 타이밍 오차 −3~+3개월(원문 6.4) ────────────────────────────────────
    shifts = {}
    for k in range(-3, 4):
        def _p(m, _k=k):
            i = months.index(m)
            j = i + _k
            if j < 0 or j >= len(months):
                return []
            return [t for t in STAGE_MAP[stage[months[j]]] if R.get(t, {}).get(m) is not None]
        s = run_basket(months, _p, R)
        shifts[("%+d" % k) if k else "0"] = stats([c for _m, _r, c in s])
    out["timing_shift"] = {
        "note": ("전환 시점을 −3~+3개월 옮긴 판. 음수는 **선행**(미리 바꾼다), 양수는 지연. "
                 "원문 6.4 절과 같은 시험이다."),
        "rows": shifts}

    p = os.path.join(DATA, "sector_rotation_myth.json")
    json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→ %s" % p)
    print("  창 %s~%s · %d개월 · 단계 미정의 %d개월"
          % (months[0], months[-1], len(months), len(undef)))
    print("  단계별 관측: %s" % out["stage_months"])
    if thin:
        print("  ⚠ 관측 %d개월 미만 단계: %s" % (MIN_STAGE_M, thin))
    print()
    print("  %-14s %8s %8s %8s %8s" % ("(비용 뒤 월%)", "평균", "표준편차", "베타", "샤프"))
    for k, lab in (("mkt", "시장"), ("rot", "섹터 로테이션"), ("tim", "시장 타이밍")):
        v = out["net"][k]
        print("  %-14s %8s %8s %8s %8s"
              % (lab, v.get("mean"), v.get("sd"), v.get("beta"), v.get("sharpe")))
    print()
    print("  🚨 반증 조건 — ①시장 초과 %s · ②유의 %s(p %s) · ③타이밍 초과 %s → **%s**"
          % (c1, c2, p_rm, c3, out["refutation"]["reading"]))
    print("  무작위 로테이션 대비 백분위: %s" % out["random_rotation"]["pct_rank"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
