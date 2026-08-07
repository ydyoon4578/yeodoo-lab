# -*- coding: utf-8 -*-
"""사전등록 PREREG-2026-08-08-WEBRESEARCH5.md §5 실행 검산.

🚨 이것은 **성적을 읽기 전에** 통과해야 하는 검사다. 규칙이 규약대로 구현됐는지만 본다.
  실패하면 '결과가 나빴다'가 아니라 **구현 오류**이고, 그때 할 일은 규약을 고치는 것이
  아니라 구현을 고쳐 다시 돌리는 것이다.

검산 항목(사전등록 §5 그대로, 뺀 두 규칙 항목은 제외):
  ① x-fscore 점수가 0~9 정수이고 중앙값이 5 근처인가.
     상위 10종이 전부 9점이면 동점 처리(B/P)가 선택을 다 하는 것이므로 그 비율을 적는다.
  ② x-indmom 월별 보유 종목 수가 40~150 인가(10 근처면 TOPN 경로로 샌 것,
     500 근처면 섹터 정렬이 안 걸린 것).
  ③ x-indmom 보유 섹터가 매달 정확히 2개인가.
  ⑤ 회전율이 규칙마다 그럴듯한가.
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


def main():
    dates, px, vlm, hi, lo, meta, rf = T.load()
    FU = T.load_fund()
    me = T.month_ends(dates)
    fail = []

    # ── ① x-fscore 점수 분포 ────────────────────────────────────────────
    dist, tie_all9, months = {}, 0, 0
    top_scores = []
    for mi in me[-60:]:                      # 최근 5년 월말
        dt = dates[mi]
        sc = []
        for t in px:
            if (meta.get(t) or {}).get("sector") == "Financials":
                continue
            f = FU.get(t) or {}
            sn = T.asof_fund(f.get("sh"), dt)
            p0 = px[t][mi]
            mc = (sn * p0) if (sn and p0 and sn > 0 and p0 > 0) else None
            v = T._fscore(f, dt, mc)
            if v is not None:
                sc.append((v, t))
        if len(sc) < T.XSEC_MIN_POOL:
            continue
        months += 1
        sc.sort(reverse=True)
        for v, _t in sc:
            dist[int(v)] = dist.get(int(v), 0) + 1
        top = [int(v) for v, _t in sc[:10]]
        top_scores.append(top)
        if all(x == 9 for x in top):
            tie_all9 += 1

    tot = sum(dist.values())
    run, med = 0, None
    for k in sorted(dist):
        run += dist[k]
        if med is None and run >= tot / 2:
            med = k
    print("① x-fscore 점수 분포 (최근 %d개 월말 · 관측 %d)" % (months, tot))
    for k in sorted(dist):
        print("     %d점 %6d (%4.1f%%)" % (k, dist[k], 100.0 * dist[k] / tot))
    print("     중앙값 %s" % med)
    n9 = sum(1 for tp in top_scores for x in tp if x == 9)
    n8p = sum(1 for tp in top_scores for x in tp if x >= 8)
    print("     상위10 중 9점 %.1f%% · 8점 이상 %.1f%%" %
          (100.0 * n9 / max(1, len(top_scores) * 10), 100.0 * n8p / max(1, len(top_scores) * 10)))
    print("     상위10이 **전부 9점**인 달: %d / %d  ← 동점 처리(B/P)가 선택을 다 한 달" %
          (tie_all9, months))
    if med is None or not (3 <= med <= 7):
        fail.append("x-fscore 점수 중앙값 %s — 0~9 척도가 깨졌다" % med)

    # ── ②③ x-indmom 보유 종목 수·섹터 수 ────────────────────────────────
    ns, nsec, sec_seq = [], [], []
    for mi in me:
        dt = dates[mi]
        ind = {}
        for t in px:
            r6 = T.ret(px[t], mi, 126)
            sg = (meta.get(t) or {}).get("sector") or ""
            if r6 is not None and sg:
                ind.setdefault(sg, []).append((t, r6))
        if not ind:
            continue
        pw = T.pick_industry(ind, top_sectors=2)
        if not pw:
            continue
        ns.append(len(pw))
        held = {(meta.get(t) or {}).get("sector") for t, _w in pw}
        nsec.append(len(held))
        sec_seq.append(tuple(sorted(held)))
    ns_s = sorted(ns)
    print("\n② x-indmom 월별 보유 종목 수 — 최소 %d · 중앙 %d · 최대 %d (월말 %d회)"
          % (ns_s[0], ns_s[len(ns_s) // 2], ns_s[-1], len(ns)))
    if not (40 <= ns_s[len(ns_s) // 2] <= 150):
        fail.append("x-indmom 보유 종목 수 중앙 %d — 40~150 밖이다" % ns_s[len(ns_s) // 2])
    if ns_s[0] < 20:
        fail.append("x-indmom 최소 보유 %d종 — 섹터가 비는 달이 있다" % ns_s[0])
    bad = [n for n in nsec if n != 2]
    print("③ x-indmom 보유 섹터 수 — 2개가 아닌 달 %d / %d" % (len(bad), len(nsec)))
    if bad:
        fail.append("x-indmom 이 2섹터가 아닌 달 %d개" % len(bad))
    chg = sum(1 for a, b in zip(sec_seq, sec_seq[1:]) if a != b)
    print("     승자 섹터 쌍이 바뀐 달 %d / %d (%.0f%%) — 회전율의 원천"
          % (chg, len(sec_seq) - 1, 100.0 * chg / max(1, len(sec_seq) - 1)))
    from collections import Counter
    cs = Counter(s for tup in sec_seq for s in tup)
    print("     승자로 뽑힌 횟수 상위: %s"
          % " · ".join("%s %d" % (k, v) for k, v in cs.most_common(5)))

    # ── ⑤ 회전율 ────────────────────────────────────────────────────────
    d = json.load(io.open(os.path.join(T.DATA, "tech_strategies.json"), encoding="utf-8"))
    by = {r["sid"]: r for r in d["strategies"]}
    print("\n⑤ 회전율 — %s" % " · ".join(
        "%s %.2f" % (s, by[s]["turnover"]) for s in ("x-fscore", "x-debtiss", "x-indmom")))
    print("   (참고) x-valcomp-sn 회전율 %.2f — 분모 정정(20→22)이 반영된 값"
          % by["x-valcomp-sn"]["turnover"])

    print()
    if fail:
        print("실행 검산: 실패 ❌ %d건 — 구현 오류다. 성적을 읽지 말 것." % len(fail))
        for f in fail:
            print("  - " + f)
        return 1
    print("실행 검산: 통과 ✅ — 규약대로 구현됐다. 이제 성적을 읽어도 된다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
