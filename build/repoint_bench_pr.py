# -*- coding: utf-8 -*-
r"""배포 원장의 **지수 대조군을 TR → PR 로 갈아 끼운다** — 1회성 전환기.

왜. 2026-08-13 사용자 결정: "전략랩에서 어떤 전략들은 BM이 TR이고 어떤건 PR인데 PR로 통일해".
종목 랩 98종은 이미 S&P 500(PR)이고 자산 랩 35종은 같은 날 ^GSPC(PR)로 옮겼는데,
배포 원장 4종만 NDX(TR)·SPX(TR)로 남아 한 화면에서 표기가 갈렸다.

🚨 **이 전환에는 값이 붙는다.** 전략 수익은 배당 재투자(TR)인데 대조군만 배당이 빠진다.
  실측: SPY 11.19% vs ^GSPC 9.19%(2006~2026, 연 2.00%p) · QQQ 15.81% vs ^NDX 14.98%(0.83%p).
  즉 대조군이 그만큼 낮아져 전략이 유리해 보인다. 이 사실은 화면(explorer)이 적는다.

🚨 data/strategy_backtests.json 은 이 저장소가 굽는 파일이 아니라 **손으로 관리하는 원장**이다.
  그래서 계열을 새로 쓰기 전에 **관례를 먼저 증명했다** —
  저장된 NDX(TR)·SPX(TR) 계열을 같은 관례로 QQQ·SPY 에서 재현해 보고 최대 상대편차
  0.37% · 0.04% 를 확인했다. 즉 아래 날짜 관례가 원장을 만든 관례와 같다:
    · dates 는 'YYYY-MM' 이고 마지막 하나를 뺀 전부가 **그 달의 마지막 거래일**이다.
    · 마지막 하나만 end 날짜다(미완결 월 — partial_month).
    · bench[0] = 100 이고 이후는 그 기준일 대비 배수다.
  dd_b 공식도 저장값과 **정확히 일치**함을 확인했다(dd = 전고점 대비 %, 소수 1자리).

무엇을 바꾸나 — **지수 대조군만.**
  NDX(TR) → NDX(PR) (^NDX) · SPX(TR) → SPX(PR) (^GSPC), b·b2 양쪽.
  bench·dd_b·mdd_b·bench2·dd_b2·mdd_b2·yearly[].b·.b2·라벨을 다시 쓴다.
  metrics 블록은 손대지 않는다 — build/strategy_metrics.py 가 이 계열에서 다시 굽는다.

⚠ 안 바꾸는 것.
  · '모전략 …' · '동일 유니버스 균등' · 'SPY 매수후보유 (타이밍 없는 원계열)' ·
    'SPY 변동성매칭' — 지수가 아니라 **같은 것을 다르게 굴린 대조군**이다. 지수로 바꾸면
    비교 자체가 성립하지 않는다(타이밍 규칙을 지수와 겨루는 것이 바로 그 오류다).
  · 섹터 모멘텀 로테이션의 b2 'SPY (S&P 500 시총가중, 맥락)' — 구간이 1999-11 부터라
    assets.json(2006-01~) 으로 **못 만든다.** 라벨이 '맥락'이라 판정에도 안 쓴다.
    ⚠ 남겨 두는 것이므로 이 스크립트가 끝에 그 사실을 반드시 출력한다.

  python build/repoint_bench_pr.py --dry     # 무엇이 바뀌는지만 본다
  python build/repoint_bench_pr.py
  python build/strategy_metrics.py           # metrics 재계산(필수 후속)
"""
from __future__ import annotations

import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BT = os.path.join(DATA, "strategy_backtests.json")

# TR 라벨 → (PR 라벨, 지수 티커). 여기 없는 라벨은 손대지 않는다.
SWAP = {"NDX(TR)": ("NDX(PR)", "^NDX"),
        "SPX(TR)": ("SPX(PR)", "^GSPC")}
# 전환 전 계열이 무엇이었는지 대조해 확인할 TR 프록시(관례 검증용).
PROXY = {"^NDX": "QQQ", "^GSPC": "SPY"}


def _grid(A):
    """assets.json 격자 → (날짜→인덱스, 월→그 달 마지막 인덱스)."""
    d = A["dates"]
    pos = {x: i for i, x in enumerate(d)}
    last = {}
    for i, x in enumerate(d):
        last[x[:7]] = i
    return pos, last


def _idx(dates, end, pos, last):
    """원장의 관례대로 관측 위치를 만든다 — 마지막 하나만 end 날짜, 나머지는 월말."""
    out = []
    for m in dates[:-1]:
        if m not in last:
            return None
        out.append(last[m])
    out.append(pos.get(end, last.get(dates[-1])))
    return None if out[-1] is None else out


def _nav(px, ix):
    base = px[ix[0]]
    if not base:
        return None
    if any(px[i] is None for i in ix):
        return None
    return [round(px[i] / base * 100, 1) for i in ix]


def _dd(nav):
    """전고점 대비 낙폭(%) 계열과 MDD. 저장값과 일치함을 확인한 공식이다."""
    pk, out, raw = -1e18, [], []
    for x in nav:
        pk = max(pk, x)
        v = (x / pk - 1) * 100
        raw.append(v)
        out.append(round(v, 1))
    return out, round(min(raw), 2)


def _yearly(dates, nav):
    """달력연도 수익(%). 첫 해는 부분연도라 dates[0] 기준이다(원장 관례)."""
    endof = {}
    for m, x in zip(dates, nav):
        endof[m[:4]] = x
    out, prev = {}, nav[0]
    for y in sorted(endof):
        out[int(y)] = round((endof[y] / prev - 1) * 100, 1)
        prev = endof[y]
    return out


def main() -> int:
    dry = "--dry" in sys.argv
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    pos, last = _grid(A)
    px = A["px"]
    doc = json.load(io.open(BT, encoding="utf-8"))
    S = doc["strategies"]

    n_hit = 0
    left = []
    for nm, v in S.items():
        ix = None
        for slot, klab, kser, kdd, kmdd, ky in (
                ("주", "bench_label", "bench", "dd_b", "mdd_b", "b"),
                ("보조", "bench2_label", "bench2", "dd_b2", "mdd_b2", "b2")):
            lab = v.get(klab)
            if lab not in SWAP:
                # 지수가 아닌 대조군은 그대로 둔다. 다만 TR 성격인데 못 바꾼 것은 적어 둔다.
                if lab and ("SPY" in lab or "QQQ" in lab) and "원계열" not in lab \
                        and "변동성매칭" not in lab:
                    left.append("%s · %s대조군 '%s'" % (nm[:34], slot, lab))
                continue
            new_lab, tk = SWAP[lab]
            if ix is None:
                ix = _idx(v["dates"], v.get("end"), pos, last)
                if ix is None:
                    left.append("%s · 격자 밖(구간 %s~)" % (nm[:34], v["dates"][0]))
                    break
            old = v.get(kser) or []
            nav = _nav(px[tk], ix)
            if nav is None or len(nav) != len(old):
                left.append("%s · %s대조군 계열 재현 실패" % (nm[:34], slot))
                continue

            # 🚨 관례 검증 — 갈아 끼우기 **전에**, 저장된 TR 계열을 TR 프록시로 재현해 본다.
            #   여기서 어긋나면 날짜 관례가 다른 것이고, 그러면 PR 계열도 엉뚱한 날의 값이 된다.
            # ⚠ **처음 EARLY 관측만** 본다. 전 구간을 보면 ETF 보수가 잡힌다 —
            #   실측: 저장된 SPX(TR) 2건이 SPY 대비 10.5년에 걸쳐 1.17% 벌어지는데,
            #   연 0.11%씩 매끄럽게 누적하는 모양이라 SPY 보수(0.0945%)다. 즉 그 원장의
            #   SPX(TR)은 ETF 가 아니라 실제 S&P 500 TR 지수다(다른 2건은 SPY 와 0.00% 일치 —
            #   원장이 출처를 섞어 썼다). 보수 누적은 **수준 차이**지 날짜가 어긋난 것이 아니다.
            #   초기 구간에서는 그 누적이 0에 가까우므로, 거기서 어긋나야 진짜 관례 불일치다.
            EARLY = 12
            chk = _nav(px[PROXY[tk]], ix)
            err = max(abs(c / o - 1) for c, o in zip(chk[:EARLY], old[:EARLY]) if o) * 100 \
                if chk else 99
            if err > 1.0:
                print("  ✗ %s %s대조군 — 관례 대조 편차 %.2f%% > 1%% · 건드리지 않는다"
                      % (nm[:34], slot, err))
                left.append("%s · %s대조군 관례 불일치" % (nm[:34], slot))
                continue

            yy = _yearly(v["dates"], nav)
            d_, m_ = _dd(nav)
            print("  %s %-34s %s대조군 %s → %s  (관례 대조 %.2f%% · 끝 %.1f → %.1f · MDD %s → %s)"
                  % ("·" if dry else "✓", nm[:34], slot, lab, new_lab, err,
                     old[-1], nav[-1], v.get(kmdd), m_))
            if dry:
                continue
            v[klab] = new_lab
            v[kser] = nav
            v[kdd] = d_
            v[kmdd] = m_
            for row in v.get("yearly") or []:
                if row.get("y") in yy:
                    row[ky] = yy[row["y"]]
            n_hit += 1

    if dry:
        print("\n--dry — 쓰지 않고 끝낸다.")
        return 0
    if n_hit:
        io.open(BT, "w", encoding="utf-8").write(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
        print("\n대조군 %d개를 PR 로 갈아 끼웠다 → %s" % (n_hit, os.path.relpath(BT, ROOT)))
        print("→ 다음: python build/strategy_metrics.py  (metrics 블록 재계산 · 필수)")
    else:
        print("\n바꿀 것이 없다 — 이미 전부 PR 이다.")
    # ⚠ 못 바꾼 것을 반드시 적는다. '다 바꿨다'로 끝내면 남은 TR 이 조용해진다.
    if left:
        print("\n⚠ TR 인데 못 바꾼 대조군 %d개 — 화면이 이 사실을 적어야 한다:" % len(left))
        for x in left:
            print("   · " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
