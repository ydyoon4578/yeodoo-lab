# -*- coding: utf-8 -*-
"""build/audit_refs_twin.py — «짝은 논문이 있는데 크기만 다른 판에는 없는» 규칙을 찾는다.

왜 있나
   `x-payout`(상위 10)에는 Boudoukh·Michaely·Richardson·Roberts(2007)가 붙어 있는데,
   **같은 점수 함수를 쓰는** `x-payout-n50`(원 전략 크기)에는 `papers` 가 비어 있다.
   규칙 문장이 스스로 «이 규칙은 짝이 되는 10종판과 **점수 함수가 같다**» 고 적어 뒀다.
   **같은 점수를 쓰는 두 규칙이 서로 다른 출처를 갖는 것은 둘 중 하나가 틀린 것이다.**

   이 랩의 출처 규약(`build/strategy_refs.json` 의 policy)은
   «확실하지 않은 규칙은 비워 둔다» 인데, 이건 «확실하지 않아서» 가 아니라
   **배선이 빠져서** 빈 것이다. 그 둘은 다르다.

무엇을 하나
   `sid` 가 `<base>-n<숫자>` 꼴인 규칙을 찾아 `<base>` 에 논문이 있는지 본다.
   있으면 **후보로 보고한다.** 🚨 자동으로 붙이지 않는다 —
   점수 함수가 정말 같은지는 규칙 문장을 사람이 읽어야 한다.

  python build/audit_refs_twin.py
"""
from __future__ import annotations
import io, json, os, re, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def main():
    refs = json.load(io.open(os.path.join(ROOT, "build", "strategy_refs.json"),
                             encoding="utf-8"))
    P = refs.get("papers") or {}
    rep = json.load(io.open(os.path.join(DATA, "strategy_report.json"), encoding="utf-8"))
    M = {x["sid"]: x for x in rep["items"]}

    rows = []
    for sid, it in sorted(M.items()):
        m = re.match(r"^(.*)-n\d+$", sid)
        if not m:
            continue
        base = m.group(1)
        has_self, has_base = bool(P.get(sid)), bool(P.get(base))
        same = "점수 함수가 같다" in (it.get("why") or "")
        rows.append((sid, base, has_self, has_base, same, base in M))

    print("크기 변형(-nNN) 규칙 %d개\n" % len(rows))
    hit = [r for r in rows if not r[2] and r[3]]
    print("🚨 짝에는 논문이 있는데 이쪽은 비어 있는 것 — %d개" % len(hit))
    print("   %-22s %-16s %-6s %s" % ("sid", "짝(base)", "짝에 논문", "«점수 함수가 같다» 명시"))
    for sid, base, _, _, same, base_live in hit:
        print("   %-22s %-16s %-6s %s%s"
              % (sid, base, "있음", "예" if same else "**안 적혀 있다**",
                 "" if base_live else "  ⚠ 짝이 게시 목록에 없다"))
        for p in P[base]:
            print("      → %s (%s) %s · %s" % (p.get("a"), p.get("y"), p.get("t"), p.get("j")))

    both = [r for r in rows if not r[2] and not r[3]]
    print("\n둘 다 비어 있는 것 — %d개 (이쪽은 배선이 아니라 정말 출처가 없는 쪽이다)" % len(both))
    for sid, base, _, _, _, _ in both:
        print("   %-22s (짝 %s)" % (sid, base))

    print("""
🚨 자동으로 붙이지 않는다. 위 목록은 **후보**다.
   점수 함수가 정말 같은지는 규칙 문장을 사람이 읽어야 하고, 크기·주기가 원 논문과
   다르면 그 사실을 함께 적어야 한다. 이 랩의 출처 규약이 «확실하지 않으면 비워 둔다» 이고,
   «짝에 있으니 붙인다» 는 확실함이 아니다.""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
