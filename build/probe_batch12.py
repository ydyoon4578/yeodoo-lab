# -*- coding: utf-8 -*-
"""build/probe_batch12.py — 후보 규칙 넷의 **자료만** 잰다(2026-08-12).

🚨 수익률 코드가 한 줄도 없다. 사전등록 규약이 요구하는 순서다 —
   재고 → 규칙을 확정해 커밋하고 → 그다음 돌린다. 여기서 수익률을 보면 뒤 선택이 전부 오염된다.

재는 후보(전략 탐색 풀 미검정분에서):
  E22 실적발표 프리미엄      data/earnings_history.json  발표월에 드는 종목이 매달 몇이나
  E23 배당월 프리미엄        data/fx/*.json dps          배당월 예측이 가능한 종목이 몇이나
  E34 매출총이익 서프라이즈   data/fx/*.json rev·cogs     🚨 DATA-FACTS#1(gp 커버 38.3%)이 걸리나
  C1  월말 효과             data/sd/*.json              (타이밍 — 후보 밀도 문제 없음, 창만 본다)

  python build/probe_batch12.py
"""
from __future__ import annotations
import io, json, os, sys, glob
import datetime as dt
from collections import Counter, defaultdict

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")


def probe_e34():
    """rev·cogs 로 매출총이익을 만들 수 있는 종목이 몇이나 — DATA-FACTS#1 재확인."""
    print("── E34 매출총이익 서프라이즈 ─────────────────────────────────")
    fs = glob.glob(os.path.join(D, "fx", "*.json"))
    n_rev = n_cogs = n_both = 0
    n_both_4q = 0
    sect = Counter()
    # 섹터를 알려면 stocks.json 이 필요하다
    sec_of = {}
    try:
        st = json.load(io.open(os.path.join(D, "stocks.json"), encoding="utf-8"))
        for s in (st.get("stocks") or []):
            sec_of[s.get("t")] = s.get("sector") or "?"
    except Exception:
        pass
    for p in fs:
        d = json.load(io.open(p, encoding="utf-8"))
        t = d.get("t") or os.path.basename(p)[:-5]
        tg = d.get("tags") or {}
        r = (tg.get("rev") or {}).get("q") or []
        c = (tg.get("cogs") or {}).get("q") or []
        if r: n_rev += 1
        if c: n_cogs += 1
        if r and c:
            n_both += 1
            if len(r) >= 8 and len(c) >= 8:      # 전년동기 비교에 최소 8분기
                n_both_4q += 1
                sect[sec_of.get(t, "?")] += 1
    n = len(fs)
    print("  재무 파일 %d · rev 있음 %d(%.1f%%) · cogs 있음 %d(%.1f%%) · **둘 다 %d(%.1f%%)**"
          % (n, n_rev, 100.0*n_rev/n, n_cogs, 100.0*n_cogs/n, n_both, 100.0*n_both/n))
    print("  둘 다 + 8분기 이상: %d종 (%.1f%%)" % (n_both_4q, 100.0*n_both_4q/n))
    if sect:
        tot = sum(sect.values())
        print("  🚨 섹터 쏠림(둘 다 있는 %d종): %s" % (tot,
              " · ".join("%s %d(%.0f%%)" % (k[:18], v, 100.0*v/tot) for k, v in sect.most_common(6))))
    return n_both_4q


def probe_e22():
    """실적발표일 — 매달 '이번 달에 발표하는 종목'이 몇이나."""
    print()
    print("── E22 실적발표 프리미엄 ────────────────────────────────────")
    p = os.path.join(D, "earnings_history.json")
    if not os.path.exists(p):
        print("  ❌ data/earnings_history.json 없음"); return 0
    j = json.load(io.open(p, encoding="utf-8"))
    print("  최상위 keys: %s" % list(j)[:8])
    rows = j.get("stocks") or j.get("rows") or j
    by_m = defaultdict(set)
    n_t = 0
    lo = hi = None
    if isinstance(rows, dict):
        it = rows.items()
    else:
        it = [((r.get("t") or "?"), r) for r in rows]
    for t, v in it:
        ds = []
        if isinstance(v, dict):
            for k in ("dates", "d", "hist", "events"):
                if isinstance(v.get(k), list):
                    ds = v[k]; break
        elif isinstance(v, list):
            ds = v
        got = False
        for x in ds:
            s = x if isinstance(x, str) else (x.get("d") or x.get("date") if isinstance(x, dict) else None)
            if not (isinstance(s, str) and len(s) >= 7):
                continue
            got = True
            by_m[s[:7]].add(t)
            lo = s if lo is None or s < lo else lo
            hi = s if hi is None or s > hi else hi
        if got: n_t += 1
    print("  종목 %d · 발표일 범위 %s ~ %s" % (n_t, lo, hi))
    ms = sorted(m for m in by_m if "2023-07" <= m <= "2026-07")
    if ms:
        c = sorted(len(by_m[m]) for m in ms)
        print("  백테스트 창(2023-07~2026-07) %d개월 · 그달 발표 종목수 중앙 %d · 최소 %d · 최대 %d"
              % (len(ms), c[len(c)//2], c[0], c[-1]))
        print("  최근 12개월: %s" % ", ".join("%s:%d" % (m[2:], len(by_m[m])) for m in ms[-12:]))
    return len(ms)


def probe_e23():
    """배당 — 배당월이 예측 가능한(과거 같은 달에 배당한 이력이 있는) 종목이 몇이나."""
    print()
    print("── E23 배당월 프리미엄 ──────────────────────────────────────")
    fs = glob.glob(os.path.join(D, "fx", "*.json"))
    n_dps = 0
    per = Counter()
    spans = []
    for p in fs:
        d = json.load(io.open(p, encoding="utf-8"))
        rows = ((d.get("tags") or {}).get("dps") or {}).get("q") or []
        if not rows:
            continue
        n_dps += 1
        ds = sorted(r[0] for r in rows if isinstance(r, list) and r and isinstance(r[0], str))
        if len(ds) >= 8:
            per[len(ds)] += 1
            spans.append((ds[0], ds[-1]))
    n = len(fs)
    print("  dps(분기) 있는 종목 %d / %d (%.1f%%) · 8분기 이상 %d종"
          % (n_dps, n, 100.0*n_dps/n, sum(per.values())))
    if spans:
        st = sorted(s for s, _ in spans); en = sorted(e for _, e in spans)
        print("  이력 시작 중앙 %s · 종료 중앙 %s" % (st[len(st)//2], en[len(en)//2]))
    print("  ⚠ dps 는 **회계기간** 기준이라 실제 배당락일이 아니다. 배당월 예측에 쓰려면"
          " 지급월을 알아야 하는데 이 태그는 그것을 주지 않는다 — 아래 판정 참조.")
    return sum(per.values())


def probe_c1():
    """월말 효과 — 타이밍 규칙이라 후보 밀도 문제는 없다. 창과 거래일 수만 본다."""
    print()
    print("── C1 월말 효과(타이밍) ────────────────────────────────────")
    fs = sorted(glob.glob(os.path.join(D, "sd", "*.json")))[:1]
    if not fs:
        print("  ❌ data/sd 없음"); return 0
    d = json.load(io.open(fs[0], encoding="utf-8"))
    ds = d.get("d") or []
    print("  거래일 %d · %s ~ %s" % (len(ds), ds[0] if ds else "-", ds[-1] if ds else "-"))
    # 월별 거래일 수 — '마지막 -1일 ~ 다음달 +3일' 창이 몇 %를 차지하나
    bym = defaultdict(list)
    for x in ds:
        bym[x[:7]].append(x)
    ms = sorted(bym)
    inwin = 0
    for i, m in enumerate(ms):
        inwin += min(1, len(bym[m]))       # 각 달 마지막 1일
        inwin += min(3, len(bym[m]))       # 각 달 첫 3일
    print("  월 %d개 · 월말1+월초3 창이 전체 거래일의 %.1f%% 를 차지한다(시장 노출 비율)"
          % (len(ms), 100.0*inwin/max(1, len(ds))))
    print("  ⚠ 타이밍 규칙은 **매매 대상과 판정 대조군이 같은 자산이어야** 한다(DATA-FACTS#12).")
    return len(ds)


def main() -> int:
    print("=" * 68)
    print("후보 자료 프로브 — 2026-08-12 · 수익률 코드 없음")
    print("=" * 68)
    probe_e34()
    probe_e22()
    probe_e23()
    probe_c1()
    return 0


if __name__ == "__main__":
    sys.exit(main())
