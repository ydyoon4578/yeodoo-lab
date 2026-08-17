# -*- coding: utf-8 -*-
"""build/audit_commit_lists.py — 워크플로가 «쓰는» data 파일 vs ci_push 커밋 목록 대조.

왜 있나.
  잡이 산출물을 만들면서 커밋 목록에 안 넣으면 `build/ci_push.sh` 가 잡을 통째로 실패시킨다
  («data/ 산출물이 커밋 목록에서 빠졌습니다»). 그 가드는 옳고 실제로 여러 번 잡았다 —
  home_reco · target_history · source_outages(2026-08-17) · verdicts(2026-08-18).
  🚨 그런데 가드는 **그 파일이 실제로 바뀌는 날에만** 터진다. 매번 바뀌지 않는 산출물은
    몇 주 초록으로 지나가다가 **정작 자료가 바뀌는 날 잡을 죽인다.** 그게 더 나쁘다.
  → 이 스크립트는 그것을 **바뀌기 전에** 찾는다.

🚨 이 감사는 «이상 없음» 을 증명하지 못한다. 정적 분석이라 경로가 변수로 만들어지는 쓰기를
  못 푼다(마지막 줄에 그 개수를 찍는다). **권위는 여전히 ci_push 의 실행시 가드에 있고**,
  이것은 그 앞에 두는 사전 점검이다. 그래서 이 스크립트는 **아무것도 실패시키지 않는다** —
  못 푼 것이 있는데 exit 1 을 내면 «통과했다» 는 잘못된 안심을 준다.

  python build/audit_commit_lists.py
"""
from __future__ import annotations
import io
import os
import re
import subprocess
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")


def writes_of(rel):
    """그 스크립트가 쓰는 data/ 파일 집합, 그리고 정적으로 못 푼 쓰기 수."""
    p = os.path.join(ROOT, rel)
    try:
        s = io.open(p, encoding="utf-8").read()
    except Exception:
        return set(), 0
    out = set()
    # 변수 = os.path.join(… "data" …, "x.json")  →  open(변수, "w")
    for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*os\.path\.join\(([^\n]*?)"([^"]+\.json)"\s*\)',
                         s, re.M):
        var, mid, fn = m.group(1), m.group(2), m.group(3)
        if ("DATA" in mid or '"data"' in mid) and re.search(r'open\(\s*%s\s*,\s*"w"' % re.escape(var), s):
            out.add(fn)
    # 인라인 open(os.path.join(… "x.json"), "w")
    out |= set(re.findall(r'open\(\s*os\.path\.join\([^\n]*?"([^"]+\.json)"\s*\)\s*,\s*"w"', s))
    # 경로가 변수인 쓰기 — 못 푼다. 수만 센다(이 감사의 재현율 한계).
    unresolved = len(re.findall(r'open\(\s*([a-z_][a-z0-9_]*)\s*,\s*"w"', s))
    return out, unresolved


def ignored(fn):
    return subprocess.run(["git", "check-ignore", "data/" + fn.rstrip("/")],
                          cwd=ROOT, capture_output=True).returncode == 0


def main() -> int:
    print("%-30s %-6s %-6s %-8s %s" % ("워크플로", "쓰기", "목록", "미해석", "목록에 빠진 것"))
    bad, unres_tot = [], 0
    for wf in sorted(os.listdir(WF)):
        if not wf.endswith(".yml"):
            continue
        src = io.open(os.path.join(WF, wf), encoding="utf-8").read()
        m = re.search(r'ci_push\.sh\s+"[^"]*"([\s\S]*?)\n\s*(?:#|-\s|\w+:)', src)
        if not m:
            continue        # 커밋하지 않는 잡(검증 전용 등)
        listed = {x.rstrip("/") for x in re.findall(r'data/([A-Za-z_0-9]+(?:\.json)?)', m.group(1))}
        w, un = set(), 0
        for sc in re.findall(r'run:\s*python\s+(build/[a-z_0-9]+\.py)', src):
            a, b = writes_of(sc)
            w |= a
            un += b
        keep = {f for f in w if not ignored(f)}     # gitignore 된 캐시는 뺀다
        miss = sorted(x for x in keep if x.rstrip("/") not in listed)
        unres_tot += un
        if miss:
            bad.append((wf, miss))
        print("%-30s %-6d %-6d %-8d %s"
              % (wf, len(keep), len(listed), un, " · ".join(miss) if miss else "—"))
    print()
    if bad:
        print("🚨 커밋 목록에 빠진 산출물 %d개 잡:" % len(bad))
        for wf, miss in bad:
            print("   %s → %s" % (wf, " · ".join(miss)))
        print("   → 그 잡의 ci_push.sh 인자에 더할 것. 안 더하면 그 파일이 바뀌는 날 잡이 죽는다.")
    else:
        print("목록에 빠진 산출물 없음.")
    print("⚠ 정적으로 못 푼 쓰기 %d곳 — 이 감사는 «이상 없음» 을 증명하지 못한다."
          % unres_tot)
    print("  권위는 ci_push 의 실행시 가드에 있다. 이것은 그 앞에 두는 사전 점검이다.")
    return 0        # 🚨 일부러 항상 0 — 위 주석 참조


if __name__ == "__main__":
    sys.exit(main())
