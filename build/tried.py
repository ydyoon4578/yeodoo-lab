# -*- coding: utf-8 -*-
"""build/tried.py — "이거 해 봤나?" 를 **세 목록에서 한 번에** 답한다.

🚨 왜 생겼나. 이 랩의 '이미 해 봤다' 기록이 세 군데 흩어져 있다:

    ① 살아 있는 것   data/tech_strategies.json  .strategies   (87종)
    ② 퇴출한 것      data/tech_strategies.json  .retired      (13종)
    ③ 돌렸지만 게시 안 한 것  build/tested_not_published.json  (15종)

2026-08-08 에 ③을 안 보고 재등록하는 사고가 나서 ③과 검사를 만들었다.
**그런데 2026-08-12 에 같은 사고가 두 번 더 났다** — 다섯 배치가 전부 ①만 훑고
"0건이니 빈 칸"이라고 적었다:

    · x-reta   ③에 있었다(sid 가 같아 검사가 잡았다)
    · x-amihud ③의 x-illiq 과 같은 규칙인데 **이름이 달라 검사를 통과했다.**
      소급 t 6.84 로 게시 직전까지 갔다. 보유 종목이 기각 사유가 지목한 13종과 겹치는 것을
      손으로 보고서야 알았다.

검사는 사고가 난 **뒤에** 막는 장치다. 이 파일은 사고가 나기 **전에** 답하려고 있다.
사전등록 문서에 '0건'이라 쓰기 전에 반드시 이것을 돌릴 것.

  python build/tried.py 유동성 회전율 Amihud     # 낱말로 세 목록 전체를 훑는다
  python build/tried.py --all                    # 세 목록을 통째로 센다
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    t = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"), encoding="utf-8"))
    n = json.load(io.open(os.path.join(ROOT, "build", "tested_not_published.json"),
                          encoding="utf-8"))
    out = []
    for r in (t.get("strategies") or []):
        out.append(("살아있음", r.get("sid"), r.get("name"), r.get("arch"),
                    " ".join(str(r.get(k) or "") for k in ("name", "rule", "why", "arch")),
                    "t %.2f · %s" % (r.get("t") or 0, r.get("verdict"))))
    for r in (t.get("retired") or []):
        out.append(("퇴출", r.get("sid"), r.get("name"), r.get("arch"),
                    " ".join(str(r.get(k) or "") for k in ("name", "why", "arch")),
                    str(r.get("why") or "")[:60]))
    for r in (n.get("items") or []):
        out.append(("선반", r.get("sid"), r.get("name"), r.get("arch"),
                    " ".join(str(r.get(k) or "") for k in
                             ("name", "why", "arch", "paper", "note", "gate")),
                    "%s · t %s" % (r.get("when"), r.get("t"))))
    return out


def main() -> int:
    rows = load()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--all" in sys.argv or not args:
        from collections import Counter
        c = Counter(r[0] for r in rows)
        print("세 목록 합계 %d종 — %s" % (len(rows),
              " · ".join("%s %d" % (k, v) for k, v in c.most_common())))
        print()
        print("🚨 사전등록에 '0건'이라 쓰기 전에 반드시 낱말로 훑을 것:")
        print("   python build/tried.py <낱말> [낱말…]")
        if not args:
            return 0
    hit = {}
    for kind, sid, nm, arch, blob, meta in rows:
        for w in args:
            if w.lower() in (blob or "").lower():
                hit.setdefault((kind, sid, nm, arch, meta), set()).add(w)
    if not hit:
        print("'%s' — 세 목록 %d종 어디에도 없다. (그래도 arch 를 붙여 두면 다음 사람이 "
              "이름을 바꿔 재등록하는 것을 검사가 잡는다)" % (" · ".join(args), len(rows)))
        return 0
    print("'%s' — 세 목록 %d종에서 **%d건** 걸렸다:" % (" · ".join(args), len(rows), len(hit)))
    for (kind, sid, nm, arch, meta), ws in sorted(hit.items(), key=lambda x: x[0][0]):
        print("  [%-5s] %-14s %-34s %s" % (kind, sid or "-", (nm or "")[:34], meta))
        print("           걸린 낱말: %s%s" % (", ".join(sorted(ws)),
                                            ("  · arch=%s" % arch) if arch else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
