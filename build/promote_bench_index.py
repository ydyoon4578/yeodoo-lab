# -*- coding: utf-8 -*-
r"""배포 원장의 **판정선을 지수(PR)로 올리고, 원래 대조군을 보조로 내린다** — 1회성 전환기.

왜. 2026-08-13 사용자 결정(2차): "아직 전략 랩에 벤치마크가 SPX, NDX PR이 아닌 것들이
있는데 고쳐줘". 1차에서 TR→PR 은 맞췄지만 원장 5종은 대조군이 애초에 지수가 아니었다 —
'모전략', '동일 유니버스 균등', 'SPY 원계열'. 한 화면에서 세로로 못 읽는다.

🚨 **갈아 끼우지 않고 내린다.** '변형 vs 모전략'은 "이 변형이 원판보다 나은가"를 묻는데,
  지수로 덮어쓰면 그 질문이 통째로 사라지고 원장의 존재 이유가 없어진다. 판정선은 위로,
  원래 질문은 아래(보조)로 — 둘 다 잰다.

🚨 **자리는 둘뿐이라 종전 보조가 밀려난다.** 밀려나는 것을 조용히 지우지 않는다 —
  이 스크립트가 끝에 무엇이 밀려났는지 전부 출력하고, 그 요약을 note_bench 필드에 싣는다.

날짜 관례는 repoint_bench_pr.py 에서 증명한 것과 같다(월말, 마지막 하나만 end 날짜).
계열이 assets.json(2006-01~) 밖으로 나가면 yfinance 에서 그 구간만 따로 받는다 —
섹터 모멘텀 로테이션이 1999-11 부터라 그렇다.

  python build/promote_bench_index.py --dry
  python build/promote_bench_index.py
  python build/strategy_metrics.py            # metrics 재계산(필수 후속)
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

# sid → (지수 티커, 화면 이름). 지수를 규칙으로 고르지 않고 **손으로 적는다** —
# 이 전략이 무엇을 사는지 알아야 짝을 고를 수 있고, 그 판단은 이름에 안 적혀 있다.
PICK = {
    "eps-revision-universe-ext":  ("^NDX",  "NDX(PR)"),    # NDX 유니버스 종목선택
    "eps-revision-turnover-band": ("^NDX",  "NDX(PR)"),
    "cross-asset-rp-vol-window":  ("^NDX",  "NDX(PR)"),    # 모전략(크로스에셋 RP)이 NDX(PR)이다
    "sector-momentum-top4":       ("^GSPC", "SPX(PR)"),    # 미국 섹터 ETF 로테이션
    "dma200-timing":              ("^GSPC", "SPX(PR)"),    # SPY 타이밍
}


def _dd(nav):
    pk, out, raw = -1e18, [], []
    for x in nav:
        pk = max(pk, x)
        v = (x / pk - 1) * 100
        raw.append(v)
        out.append(round(v, 1))
    return out, round(min(raw), 2)


def _yearly(dates, nav):
    endof = {}
    for m, x in zip(dates, nav):
        endof[m[:4]] = x
    out, prev = {}, nav[0]
    for y in sorted(endof):
        out[int(y)] = round((endof[y] / prev - 1) * 100, 1)
        prev = endof[y]
    return out


def _from_assets(tk, dates, end):
    """assets.json 격자에서 원장 관례대로 월말 종가를 뽑는다. 구간 밖이면 None."""
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    d = A["dates"]
    pos = {x: i for i, x in enumerate(d)}
    last = {}
    for i, x in enumerate(d):
        last[x[:7]] = i
    ix = [last.get(m) for m in dates[:-1]] + [pos.get(end, last.get(dates[-1]))]
    if any(i is None for i in ix):
        return None
    s = (A.get("px") or {}).get(tk)
    if not s or any(s[i] is None for i in ix):
        return None
    return [s[i] for i in ix]


def _from_yf(tk, dates, end):
    """assets.json 밖 구간 — yfinance 에서 그 티커만 따로 받는다.
    ⚠ 지수(^GSPC·^NDX)는 배당이 없어 auto_adjust 여부와 무관하게 가격지수다. 그래도
      명시적으로 auto_adjust=False 를 준다 — 규약이 바뀌어도 PR 인 채로 있게."""
    import yfinance as yf
    start = dates[0] + "-01"
    df = yf.download(tk, start=start, auto_adjust=False, progress=False, threads=False)
    if df is None or df.empty:
        return None
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    col = "Close" if "Close" in df.columns else df.columns[0]
    by_day = {str(k)[:10]: float(v) for k, v in df[col].items() if v == v}
    last_of = {}
    for k in sorted(by_day):
        last_of[k[:7]] = by_day[k]
    out = [last_of.get(m) for m in dates[:-1]] + [by_day.get(end) or last_of.get(dates[-1][:7])]
    return None if any(x is None for x in out) else out


def main() -> int:
    dry = "--dry" in sys.argv
    doc = json.load(io.open(BT, encoding="utf-8"))
    S = doc["strategies"]
    n_hit, bumped, failed = 0, [], []

    for nm, v in S.items():
        sid = v.get("sid")
        if sid not in PICK or "(PR)" in (v.get("bench_label") or ""):
            continue
        tk, lab = PICK[sid]
        dates, end = v["dates"], v.get("end")
        px = _from_assets(tk, dates, end)
        src = "assets.json"
        if px is None:
            try:
                px = _from_yf(tk, dates, end)
                src = "yfinance"
            except Exception as e:
                print("  ✗ %-34s yfinance 실패 — %s" % (nm[:34], str(e)[:50]))
                px = None
        if px is None:
            failed.append("%s (%s · %s~)" % (nm[:34], tk, dates[0]))
            continue
        nav = [round(x / px[0] * 100, 1) for x in px]
        d_, m_ = _dd(nav)
        yy = _yearly(dates, nav)
        old_b2 = v.get("bench2_label")
        print("  %s %-34s 판정선 → %s (%s · 끝 %.1f · MDD %s)"
              % ("·" if dry else "✓", nm[:34], lab, src, nav[-1], m_))
        print("      보조로 내림: %s" % (v.get("bench_label") or "")[:60])
        if old_b2:
            print("      🚨 밀려남:   %s" % old_b2[:60])
            bumped.append("%s — %s" % (nm[:30], old_b2))
        if dry:
            continue

        # 원래 대조군을 보조로 내린다(계열·낙폭·연도까지 통째로 옮긴다).
        v["bench2"] = v["bench"]
        v["bench2_label"] = v["bench_label"]
        v["dd_b2"] = v.get("dd_b")
        v["mdd_b2"] = v.get("mdd_b")
        for row in v.get("yearly") or []:
            if "b" in row:
                row["b2"] = row["b"]
        # 판정선을 지수로 올린다.
        v["bench"] = nav
        v["bench_label"] = lab
        v["dd_b"] = d_
        v["mdd_b"] = m_
        # ⚠ 역할표도 같이 내린다. 여기서 새 이름('control')을 지어내면 validate_site 의
        #   허용값(context·index·parent·selfuniverse·underlying·volmatched)에 없어 검사가
        #   막힌다 — 실제로 막혔다. 이 대조군이 무엇인지는 **이미 적혀 있었다.**
        v["bench2_role"] = v.get("bench_role") or "context"
        v["bench_role"] = "index"
        for row in v.get("yearly") or []:
            if row.get("y") in yy:
                row["b"] = yy[row["y"]]
        # ⚠ 밀려난 대조군을 기록으로 남긴다. 화면이 안 읽더라도 파일이 기억해야 한다.
        if old_b2:
            v["bench_bumped"] = old_b2
            v["note_bench"] = ("2026-08-13 판정선을 %s 로 올리면서 종전 대조군을 보조로 "
                               "내렸다. 자리가 둘뿐이라 그 전 보조 '%s' 는 목록에서 빠졌다."
                               % (lab, old_b2))
        n_hit += 1

    if dry:
        print("\n--dry — 쓰지 않고 끝낸다.")
        return 0
    if n_hit:
        io.open(BT, "w", encoding="utf-8").write(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
        print("\n판정선 %d개를 지수(PR)로 올렸다 → %s" % (n_hit, os.path.relpath(BT, ROOT)))
        print("→ 다음: python build/strategy_metrics.py  (metrics 블록 재계산 · 필수)")
    if bumped:
        print("\n🚨 자리가 둘뿐이라 밀려난 보조 대조군 %d개 — 없어진 것이 아니라 목록에서 빠진 것이다:"
              % len(bumped))
        for x in bumped:
            print("   · " + x)
    if failed:
        print("\n⚠ 지수 계열을 못 만든 전략 %d개 — 판정선을 그대로 뒀다:" % len(failed))
        for x in failed:
            print("   · " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
