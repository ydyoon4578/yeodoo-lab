# -*- coding: utf-8 -*-
"""build/split_fix.py — 벤더가 **소급 적용하지 않은 분할**을 찾아 고친다.

## 왜 있나 (2026-08-19 · 사용자 발견)

  "mnst 차트가 이상한데 분할한게 반영이 안됐나"

  맞았다. MNST 는 2026-08-11 에 2:1 분할했는데 가격 계열이 이랬다:
      2026-08-07  90.36   ← 분할 전 기준 그대로
      2026-08-10  None
      2026-08-11  45.53   ← 분할 후
  🚨 **야후의 분할 이력에는 그 분할이 있다**(t.splits 에 2026-08-11 · 2.0).
    그런데 auto_adjust=True 로 받은 가격 이력을 소급 조정하지 않았다 — 벤더가 늦은 것이다.
    랩은 받은 대로 실었고, 그래서 화면과 모든 전략이 **가짜 −50% 하루**를 보았다.

  ⚠ 이 랩은 이미 그 사실을 전제로 적어 두고 있었다 — build/refresh_splits.py 머리말:
    «가격은 분할조정본(auto_adjust=True)이라 전 구간이 오늘 기준인데…».
    전제를 적어 두는 것과 그 전제가 지켜지는지 재는 것은 다르다. 이 파일이 그것을 잰다.

## 왜 일간 변동 검사가 못 잡았나

  분할일(08-10)이 **결측**이라 «어제 대비 오늘» 이 90.36 → None → 45.53 으로 끊겼다.
  하루씩 보는 검사는 결측을 건너뛰지 않으므로 그 점프를 영영 못 본다.
  → 여기서는 **결측을 건너뛴 인접 관측**으로 본다.

## 무엇을 하나 / 안 하나

  · data/splits.json(랩이 이미 굽는 분할 이력)에 있는 분할만 본다. **비율을 추정하지 않는다** —
    회사가 공시한 사실만 쓴다(refresh_splits.py 가 세운 규약 그대로).
  · 분할일 앞뒤 관측의 비가 그 분할비와 맞으면 «소급 안 됨» 으로 보고, 분할일 **앞** 구간을
    분할비로 나눈다. 거래량은 곱한다.
  · 🚨 pxd·hd·ld·vd 를 같은 규칙으로 함께 고친다. 종가만 고치면 고가·저가가 종가보다
    두 배인 계열이 된다 — 그건 더 나쁘다.
  · 이미 소급된 계열은 건드리지 않는다(비가 1 근처다).
  · ⚠ 벤더가 나중에 소급을 적용하면 이 보정이 **두 번** 걸릴 수 있다. 그래서 고친 사실을
    파일에 적고(split_fix), 다음 실행은 앞뒤 비를 다시 재서 이미 맞으면 아무것도 안 한다.

    python build/split_fix.py --dry-run
    python build/split_fix.py
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
SD = os.path.join(DATA, "sd")
GAP = 6          # 결측을 이만큼까지 건너뛰어 인접 관측을 찾는다(거래일)
TOL = 0.12       # 분할비와 이만큼 이내로 맞으면 «그 분할» 로 본다


def _near(i, dts, px, d0):
    """분할일 d0 을 사이에 두고 가장 가까운 앞·뒤 관측 (색인, 값)."""
    lo = hi = None
    for k in range(i - 1, max(-1, i - 1 - GAP), -1):
        if k >= 0 and px[k] is not None:
            lo = (k, px[k]); break
    for k in range(i, min(len(dts), i + GAP)):
        if px[k] is not None:
            hi = (k, px[k]); break
    return lo, hi


def main() -> int:
    dry = "--dry-run" in sys.argv
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dts = st["pxd_dates"]
    n = len(dts)
    di = {d: k for k, d in enumerate(dts)}
    SP = (json.load(io.open(os.path.join(DATA, "splits.json"), encoding="utf-8")) or {}).get("co") or {}
    print("분할 이력 %d종 · 격자 %d일 (%s ~ %s)" % (len(SP), n, dts[0], dts[-1]))

    fixed, checked = [], 0
    for t, evs in sorted(SP.items()):
        p = os.path.join(SD, "%s.json" % t)
        if not os.path.exists(p):
            continue
        obj = json.load(io.open(p, encoding="utf-8"))
        px = list(obj.get("pxd") or [])
        if not px:
            continue
        px += [None] * (n - len(px))
        todo = []
        for d0, ratio in evs:
            i = di.get(d0)
            if i is None or not ratio or ratio <= 1:
                continue                       # 격자 밖(옛 분할)은 볼 것이 없다
            checked += 1
            lo, hi = _near(i, dts, px, d0)
            if not lo or not hi or not lo[1] or not hi[1]:
                continue
            r = hi[1] / lo[1]
            # 소급이 됐으면 r 이 1 근처다. 안 됐으면 r ≈ 1/ratio 다.
            if abs(r - 1.0 / ratio) <= TOL / ratio:
                todo.append((i, float(ratio), dts[lo[0]], lo[1], dts[hi[0]], hi[1], r))
        if not todo:
            continue
        for i, ratio, d_a, p_a, d_b, p_b, r in todo:
            fixed.append((t, dts[i], ratio, d_a, p_a, d_b, p_b, r))
            if dry:
                continue
            # 🚨 분할일 **앞** 구간만 나눈다. 뒤는 이미 분할 후 기준이다.
            for key, op in (("pxd", "div"), ("hd", "div"), ("ld", "div"), ("vd", "mul")):
                a = obj.get(key)
                if not isinstance(a, list):
                    continue
                for k in range(min(i, len(a))):
                    if a[k] is None:
                        continue
                    a[k] = (round(a[k] / ratio, 4) if op == "div" else int(round(a[k] * ratio)))
                obj[key] = a
        if not dry and todo:
            rec = list(obj.get("split_fix") or [])
            for i, ratio, d_a, p_a, d_b, p_b, r in todo:
                rec.append({"d": dts[i], "ratio": ratio,
                            "before": [d_a, p_a], "after": [d_b, p_b]})
            obj["split_fix"] = rec
            obj["split_fix_note"] = (
                "벤더(yfinance)가 이 분할을 가격 이력에 **소급 적용하지 않아** 랩이 여기서 "
                "고쳤다 — 분할일 앞 구간을 분할비로 나누고 거래량은 곱했다. 분할 사실은 "
                "data/splits.json(회사 공시)에서 읽었고 비율을 추정하지 않았다. "
                "build/split_fix.py")
            io.open(p, "w", encoding="utf-8", newline="").write(
                json.dumps(obj, ensure_ascii=False, separators=(",", ":")))

    print("격자 안 분할 %d건 확인 · 소급 안 된 것 %d건" % (checked, len(fixed)))
    for t, d, ratio, d_a, p_a, d_b, p_b, r in fixed:
        print("   %-6s %s  %.0f:1  %s %.2f → %s %.2f (×%.3f)"
              % (t, d, ratio, d_a, p_a, d_b, p_b, r))
    if dry:
        print("(--dry-run) 쓰지 않았다")
    elif fixed:
        print("→ %d종목 고침 · data/sd/ 에 기록(split_fix)" % len({x[0] for x in fixed}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
