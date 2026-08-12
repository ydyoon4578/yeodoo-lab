# -*- coding: utf-8 -*-
"""build/probe_insider.py — 내부자 거래(Form 4)를 규칙으로 쓸 수 있는지 **재기만** 한다.

🚨 이 파일에는 수익률 코드가 한 줄도 없다. 사전등록 규약(build/PREREG-2026-08-04.md)이
   요구하는 순서가 '자료를 먼저 재고 → 규칙을 확정해 커밋하고 → 그다음 돌린다' 이기 때문이다.
   여기서 수익률을 한 번이라도 보면 그 뒤에 고른 정의는 전부 오염된다.

무엇을 재나 — 규칙의 운명을 미리 정해 버리는 것들만:
  ① 커버리지 — 518종 중 몇 종에 장내매수(P)가 있나
  ② 창 — 백테스트 구간(2023-07~2026-07)을 덮나
  ③ 공시지연(fd − d) — 며칠 뒤에 알 수 있나. **d 로 채점하면 선견이다**
  ④ 월말 후보 밀도 — 매달 상위 10을 고를 만큼 후보가 있나
  ⑤ 10위 경계 동점 — 동점이 많으면 '상위 10'이 규칙이 아니라 정렬 순서가 된다
  ⑥ 거래코드 분포 — P(장내매수)와 A(주식보상)를 섞으면 신호가 아니라 보상일정이 된다

  python build/probe_insider.py
"""
from __future__ import annotations
import io, json, os, sys, glob
import datetime as dt
from collections import Counter, defaultdict

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INS = os.path.join(ROOT, "data", "ins")
SD = os.path.join(ROOT, "data", "sd")


def _dates():
    """백테스트가 쓰는 거래일 격자 — data/sd 아무 파일에서나 뽑는다."""
    for p in sorted(glob.glob(os.path.join(SD, "*.json")))[:5]:
        d = json.load(io.open(p, encoding="utf-8"))
        ds = d.get("pxd") and d.get("d")
        if d.get("d"):
            return d["d"]
    return []


def main() -> int:
    fs = sorted(glob.glob(os.path.join(INS, "*.json")))
    print("내부자 파일 %d개" % len(fs))
    if not fs:
        raise SystemExit("data/ins 가 비었다")

    n_any = n_p = 0
    codes = Counter()
    rel = Counter()
    lag = []
    first, last = [], []
    # 종목×월 → 장내매수 건수 / 순매수 금액
    by_m = defaultdict(set)          # 'YYYY-MM' → {티커}  (그 달에 공시된 P 가 있는 종목)
    p_by_t = Counter()
    for p in fs:
        d = json.load(io.open(p, encoding="utf-8"))
        t = d.get("t") or os.path.basename(p)[:-5]
        tr = d.get("tr") or []
        if tr:
            n_any += 1
        ps = []
        for r in tr:
            c = r.get("c")
            codes[c] += 1
            rel[(r.get("rel") or "?")] += 1
            dd, fd = r.get("d"), r.get("fd")
            if dd and fd:
                try:
                    lag.append((dt.date.fromisoformat(fd) - dt.date.fromisoformat(dd)).days)
                except Exception:
                    pass
            if c == "P":
                ps.append(r)
                if fd:
                    by_m[fd[:7]].add(t)
        if ps:
            n_p += 1
            p_by_t[t] = len(ps)
            fds = [r["fd"] for r in ps if r.get("fd")]
            if fds:
                first.append(min(fds)); last.append(max(fds))

    print()
    print("① 커버리지 — 거래이력 있는 종목 %d / %d · **장내매수(P) 있는 종목 %d (%.1f%%)**"
          % (n_any, len(fs), n_p, 100.0 * n_p / max(1, len(fs))))
    print("⑥ 거래코드 분포(전체 %d건): %s" % (sum(codes.values()),
          " · ".join("%s %d(%.1f%%)" % (k, v, 100.0 * v / sum(codes.values()))
                     for k, v in codes.most_common(8))))
    print("   관계: %s" % " · ".join("%s %d" % (k[:22], v) for k, v in rel.most_common(5)))

    if first:
        first.sort(); last.sort()
        print()
        print("② 창 — P 최초공시 중앙 %s (가장 이른 %s) · 최종공시 중앙 %s (가장 늦은 %s)"
              % (first[len(first) // 2], first[0], last[len(last) // 2], last[-1]))

    if lag:
        lag.sort()
        n = len(lag)
        print()
        print("③ 공시지연(fd − d) — 중앙 %d일 · 90분위 %d일 · 최대 %d일 · 음수 %d건"
              % (lag[n // 2], lag[int(n * 0.9)], lag[-1], sum(1 for x in lag if x < 0)))
        print("   🚨 채점은 **fd(공시일)** 기준이어야 한다. d(거래일)로 잡으면 중앙 %d일치 선견이다."
              % lag[n // 2])

    print()
    print("④ 월별 '그 달에 P 가 공시된 종목 수' — 상위 10을 고를 수 있나")
    ms = sorted(by_m)
    ms = [m for m in ms if m >= "2023-01"]
    thin = [m for m in ms if len(by_m[m]) < 10]
    cnt = [len(by_m[m]) for m in ms]
    if cnt:
        cnt_s = sorted(cnt)
        print("   2023-01 이후 %d개월 · 중앙 %d종 · 최소 %d종 · 최대 %d종 · **10 미만인 달 %d개**"
              % (len(ms), cnt_s[len(cnt_s) // 2], cnt_s[0], cnt_s[-1], len(thin)))
        if thin:
            print("   얇은 달: %s" % ", ".join("%s(%d)" % (m, len(by_m[m])) for m in thin[:14]))
        print("   최근 12개월: %s" % ", ".join("%s:%d" % (m[2:], len(by_m[m])) for m in ms[-12:]))

    # ⑤ 12개월 누적창으로 보면 후보가 얼마나 되나 — 창을 넓히면 밀도 문제가 풀리는지
    print()
    print("⑤ 누적창별 후보 수(그 창 안에 P 공시가 하나라도 있는 종목) — 창을 넓히면 풀리나")
    allm = sorted(by_m)
    for W in (1, 3, 6, 12):
        vals = []
        for i in range(len(allm)):
            if allm[i] < "2023-07":
                continue
            win = allm[max(0, i - W + 1):i + 1]
            s = set()
            for m in win:
                s |= by_m[m]
            vals.append(len(s))
        if vals:
            vs = sorted(vals)
            print("   %2d개월 창 → 중앙 %3d종 · 최소 %3d종 · 최대 %3d종 · 10 미만인 달 %d"
                  % (W, vs[len(vs) // 2], vs[0], vs[-1], sum(1 for v in vals if v < 10)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
