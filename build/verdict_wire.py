# -*- coding: utf-8 -*-
"""build/verdict_wire.py — 사전등록 **판정이 실제로 배선됐는지** 기계로 보고, 자료 쪽은 채운다

무엇을·왜.
  2026-09-03 실측 사고. PREREG-2026-09-03-A1FIX-RESULT 가 「게시하지 않는다 … 판정은
  철회한다」「x-a1payout 은 게시 목록에서 빠진다」라고 **두 번** 못박았는데, 그 배선이
  아무 데도 안 돼서 그 규칙이 게시 48종에 그대로 서 있었다. 같은 날 같이 기각된 형제 둘은
  배선됐고 이것만 빠졌다 — **사람이 세 곳(판정문 · 기각 원장 · 엔진)을 손으로 맞춰야**
  하는 규약이라 그렇다.
  이 저장소의 되풀이 결함 「판정만 하고 안 배선」의 첫째 판이고, 그 뒤 둘이 더 나왔다
  (기각 원장 누락 3건 · 탐색 풀 카드 4건). 세 번 나왔으면 사람 주의력의 문제가 아니다.

  → **문서가 기계가 읽을 수 있게 선언하고, 그 선언과 실제 상태를 대조한다.**

선언(각 RESULT 문서 머리에 한 줄씩).

    풀카드: D13            어느 탐색 풀 카드를 잰 것인가(랩이 스스로 낸 규칙이면 «없음»)
    판정: 기각             기각 · 게시 · 측정만 · 보류  중 하나
    규칙: x-a1payout       이 판정이 걸리는 sid(여럿이면 콤마 · 규칙이 아니면 «없음»)

무엇을 자동으로 하고 무엇을 안 하나.
  **자료는 쓴다** — 기각인데 build/tested_not_published.json 에 없으면 **넣는다.**
    ⚠ 사유(why)를 **지어내지 않는다.** 판정 줄과 «사유는 이 문서 참조» 만 적는다.
      pool_lab 에서 본문을 요약하려다 마크다운이 뒤엉켜 카드에 그대로 나간 적이 있다.
  **코드는 안 고친다** — 엔진 등록(HIDE_SIDS · RETIRED · xsec 호출)은 사람이 판단할 일이라
    어긋나면 **오류로 알리고 멈춘다.** 자동으로 규칙을 등록·해제하면 그것이 더 위험하다.

    python build/verdict_wire.py            # 자료 쪽 배선을 채운다
    python build/verdict_wire.py --check    # 어긋난 것이 있으면 종료코드 1
"""
from __future__ import annotations
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
LEDGER = os.path.join(HERE, "tested_not_published.json")

VERDICTS = ("기각", "게시", "측정만", "보류")
D_VERDICT = re.compile(r"^\s*판정\s*[:：]\s*(.+?)\s*$", re.M)
D_SID = re.compile(r"^\s*규칙\s*[:：]\s*(.+?)\s*$", re.M)


def declarations() -> tuple[list, list]:
    """(선언 목록, 선언이 빠진 문서). 선언은 2026-09-05 이후 문서에만 강제한다."""
    out, missing = [], []
    for fn in sorted(os.listdir(HERE)):
        if not (fn.startswith("PREREG-") and fn.endswith("-RESULT.md")):
            continue
        t = io.open(os.path.join(HERE, fn), encoding="utf-8").read()
        mv, ms = D_VERDICT.search(t), D_SID.search(t)
        if not (mv and ms):
            missing.append(fn)
            continue
        v = mv.group(1).strip()
        sids = [] if "없음" in ms.group(1) else [
            s.strip() for s in re.split(r"[,·]", ms.group(1)) if s.strip()]
        out.append({"doc": fn, "verdict": v, "sids": sids})
    return out, missing


def state() -> dict:
    """지금 실제 배선 상태 — 게시 목록 · 엔진 등록 · 기각 원장."""
    def _j(p):
        try:
            return json.load(io.open(p, encoding="utf-8"))
        except Exception:
            return {}
    idx = _j(os.path.join(DATA, "strategy_index.json"))
    tech = _j(os.path.join(DATA, "tech_strategies.json"))
    asset = _j(os.path.join(DATA, "asset_strategies.json"))
    led = _j(LEDGER)
    return {
        "published": {r.get("sid") for r in (idx.get("items") or [])},
        "engine": ({r["sid"] for r in (tech.get("strategies") or [])}
                   | {"a-" + r["sid"] for r in (asset.get("strategies") or [])}),
        "retired": {r["sid"] for r in (tech.get("retired") or [])},
        "ledger": {r["sid"] for r in (led.get("items") or []) if r.get("sid")},
        "readmitted": {r["sid"] for r in (led.get("items") or []) if r.get("readmitted")},
        "_led": led,
    }


def main(argv) -> int:
    check = "--check" in argv
    decls, missing = declarations()
    S = state()
    errs, added, ok = [], [], 0

    for d in decls:
        v = d["verdict"]
        if not any(k in v for k in VERDICTS):
            errs.append("%s: 판정 «%s» 을 못 읽었다 — %s 중 하나로 적을 것"
                        % (d["doc"], v[:24], " · ".join(VERDICTS)))
            continue
        for sid in d["sids"]:
            pub = sid in S["published"] or ("t-" + sid) in S["published"]
            if "기각" in v:
                # ① 게시돼 있으면 **코드를 고쳐야 한다** — 여기서 안 만진다.
                if pub and sid not in S["readmitted"]:
                    errs.append(
                        "%s 가 «기각» 인데 %s 이 게시 목록에 있다 — 엔진 등록을 내리거나"
                        "(tech_backtest 의 xsec 호출) HIDE_SIDS 에 넣을 것. "
                        "자료가 아니라 코드라 여기서 자동으로 안 고친다" % (d["doc"], sid))
                # ② 원장에 없으면 **자료라서 채운다**(사유는 지어내지 않고 문서를 가리킨다).
                if sid not in S["ledger"]:
                    added.append({"sid": sid, "doc": d["doc"], "verdict": v})
                else:
                    ok += 1
            elif "게시" in v or "측정만" in v:
                if not pub:
                    errs.append("%s 가 «%s» 인데 %s 이 게시 목록에 없다 — 내린 이유가 있으면 "
                                "문서의 판정 줄을 그 사실로 고칠 것" % (d["doc"], v[:12], sid))
                elif sid in S["ledger"] and sid not in S["readmitted"]:
                    errs.append("%s 가 «%s» 인데 %s 이 기각 원장에도 있다 — 한쪽으로 정할 것"
                                % (d["doc"], v[:12], sid))
                else:
                    ok += 1

    if added and not check:
        led = S["_led"]
        for a in added:
            led["items"].append({
                "sid": a["sid"], "name": "", "kind": "", "arch": "", "when": "",
                "src": a["doc"], "paper": "", "t": None, "incr": None,
                "gate": a["verdict"],
                # ⚠ 사유를 지어내지 않는다. 판정문이 정본이고 여기는 가리키기만 한다.
                "why": ("판정 «%s» — 사유와 수치는 build/%s 에 있다. "
                        "(build/verdict_wire.py 가 선언을 읽어 넣은 줄이다. 이름·수치 칸은 "
                        "사람이 채운다 — 기계가 요약하면 그 요약이 정본처럼 읽힌다.)"
                        % (a["verdict"], a["doc"])),
                "blocked_by": "",
            })
        json.dump(led, io.open(LEDGER, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    print("판정 선언 %d편 · 배선 일치 %d건 · 원장에 넣을 것 %d건 · 어긋남 %d건"
          % (len(decls), ok, len(added), len(errs)))
    for a in added:
        print("   + 원장: %s (%s · %s)" % (a["sid"], a["verdict"], a["doc"]))
    for e in errs:
        print("   ❌ " + e)
    if missing:
        print("   ~ 선언이 없는 문서 %d편(2026-09-05 이전은 소급 적용하지 않는다)" % len(missing))

    if check:
        return 1 if (errs or added) else 0
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
