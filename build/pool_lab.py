# -*- coding: utf-8 -*-
"""build/pool_lab.py — 사전등록 판정을 **탐색 풀 카드에 되돌려 붙인다** → data/rotation_pool.json

무엇을·왜.
  rotation.html 의 카드에는 「랩 자체 검증 결과」 칸(`lab`)이 있다. 그런데 그 칸을 **손으로**
  채워 왔고, 그래서 채워지지 않았다 — 실측 2026-09-04:

      A1(자사주매입+배당성장) · C14(달러 캐리) · D8(채권 롤다운) · D13(듀레이션 스타일 로테이션)
      → 넷 다 사전등록으로 실제로 돌려 셋을 기각했는데 **카드에는 한 줄도 안 실렸다.**

  즉 공개 페이지가 「외부 출처 · 미검증」이라 말하는 동안 랩은 이미 재고 기각했다.
  이 저장소의 되풀이 결함 「판정만 하고 안 배선」의 세 번째 판이다(x-a1payout 은 게시
  목록에서, 이번은 탐색 풀 카드에서).

🚨 왜 산문에서 «추론» 하지 않나.
  RESULT 문서가 카드를 지목하는 방식이 제각각이다 — 「탐색 풀 B11」·「E21 카드」·
  「카드 A22」·「풀 카드 D13」. 실측으로 61편에서 카드 6종밖에 못 잇는다.
  카드 **이름**으로 맞춰도 A1 만 걸리고 C14·D8·D13 은 못 찾는다.
  → **선언하게 한다.** 각 RESULT 문서가 머리에 한 줄로 적는다:

        풀카드: D13            (여러 개면 콤마 — `풀카드: D8, D13`)
        풀카드: 없음           (랩이 스스로 낸 규칙이라 카드가 없을 때)

  build/validate_site.py 가 새 문서에 그 줄이 있는지 강제한다. 추론은 조용히 틀리고,
  선언은 빠지면 걸린다.

⚠ 이 스크립트는 **판정문을 고치지 않는다.** 읽어서 카드에 옮길 뿐이다.
⚠ data/rotation_pool.json 은 로컬 스케줄러(KB_RotationDaily)가 매일 웹 리서치로 다시
  쓴다. 그래서 lab 칸은 **매번 여기서 다시 붙여야 한다** — 그 잡 뒤에 이것을 돌린다.
  (붙이는 것이 멱등이라 여러 번 돌려도 같다.)

    python build/pool_lab.py            # 붙인다
    python build/pool_lab.py --check    # 안 붙은 것이 있으면 종료코드 1
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
POOL = os.path.join(ROOT, "data", "rotation_pool.json")

# 문서 머리의 선언 줄. 콜론 뒤에 카드 id 를 콤마로 나열하거나 「없음」.
DECL = re.compile(r"^\s*풀카드\s*[:：]\s*(.+?)\s*$", re.M)
CARD = re.compile(r"\b([A-E]\d{1,2})\b")


def verdict_of(text: str) -> str:
    """판정 한 줄. 제목 줄의 **굵은 판정**을 먼저 보고, 없으면 「판정」 절을 본다.

    ⚠ 지어내지 않는다 — 못 찾으면 빈 문자열을 돌려주고 호출부가 그 사실을 적는다.
    """
    head = text.split("\n", 1)[0]
    m = re.search(r"\*\*(.+?)\*\*", head)
    if m:
        return m.group(1).strip()
    # 🚨 본문 「판정」 절을 긁지 않는다. 처음에 160자를 잘라 왔더니 마크다운과 여러 갈래
    #   판정이 뒤엉켜 카드에 그대로 나갔다(DURSTYLE4 실측). **못 읽은 것을 못 읽었다고
    #   말하는 편이 낫다** — 지어낸 요약이 카드에 실리면 그것이 정본처럼 읽힌다.
    #   제목 줄에 **굵은 판정**을 적는 것이 이 랩의 규약이다(대부분의 문서가 이미 그렇다).
    return ""


def scan() -> dict:
    """카드 id → {docs, verdicts}. 선언이 없는 문서는 undeclared 로 따로 센다."""
    out, undecl, none_decl = {}, [], 0
    d = os.path.join(ROOT, "build")
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith("PREREG-") and fn.endswith("-RESULT.md")):
            continue
        t = io.open(os.path.join(d, fn), encoding="utf-8").read()
        m = DECL.search(t)
        if not m:
            undecl.append(fn)
            continue
        body = m.group(1)
        if "없음" in body:
            none_decl += 1
            continue
        for cid in CARD.findall(body):
            out.setdefault(cid, {"docs": [], "verdicts": []})
            out[cid]["docs"].append(fn)
            v = verdict_of(t)
            if v:
                out[cid]["verdicts"].append(v)
    return {"cards": out, "undeclared": undecl, "no_card": none_decl}


def main(argv) -> int:
    check = "--check" in argv
    s = scan()
    pool = json.load(io.open(POOL, encoding="utf-8"))
    cards = {c.get("id"): c for c in pool.get("strategies") or [] if c.get("id")}

    missing, wrote = [], 0
    for cid, info in sorted(s["cards"].items()):
        c = cards.get(cid)
        if c is None:
            missing.append(cid)          # 문서가 없는 카드를 가리킨다 — 오타이거나 카드가 지워졌다
            continue
        # 🚨 여러 등록이 같은 카드를 잰 경우 **하나를 고르지 않는다.**
        #   처음에 「최신 문서의 판정」을 실었더니 D13 이 틀렸다 — 다섯 편이 서로 다른 답을
        #   냈는데(RATE2 통과·DURSTYLE4 러셀 기각/CRSP 게시·DURATION 기각·SSROT 기각·
        #   BMROT 여섯 조건 통과) 알파벳 마지막 하나만 실려 「기각」으로 보였다.
        #   그리고 「최신」의 기준도 파일명 정렬이라 뜻이 없었다.
        #   → **편마다 나열한다.** 한 줄로 접으면 그 카드를 여러 각도로 잰 사실 자체가 사라진다.
        pairs = list(zip(info["docs"], info["verdicts"] + [""] * len(info["docs"])))
        def _short(fn):
            m = re.match(r"PREREG-\d{4}-\d{2}-\d{2}-(.+)-RESULT\.md$", fn)
            return m.group(1) if m else fn
        if len(pairs) == 1:
            v = pairs[0][1] or "판정 문구를 못 읽었다"
        else:
            v = " · ".join("%s %s" % (_short(f), (x or "판정 문구를 못 읽었다"))
                           for f, x in pairs)
        lab = {"v": v,
               "t": str(c.get("name") or ""),
               "why": ("사전등록 %d편에서 이 랩의 구현으로 쟀다: %s. "
                       "⚠ 검증 대상은 «이 랩의 특정 구현» 이라 카드 규칙과 완전히 같지는 않다 — "
                       "각 문서의 §1(규칙)과 한계를 볼 것. "
                       "⚠ 편마다 다른 구현을 쟀을 수 있다(같은 카드를 각도를 바꿔 여러 번 잰다)."
                       % (len(info["docs"]), " · ".join(info["docs"]))),
               "docs": info["docs"]}
        if c.get("lab") != lab:
            c["lab"] = lab
            wrote += 1

    print("사전등록 RESULT — 카드 선언 %d종 · 「없음」 선언 %d편 · **선언 없는 문서 %d편**"
          % (len(s["cards"]), s["no_card"], len(s["undeclared"])))
    if s["undeclared"]:
        print("  선언 없는 문서(옛 것): " + ", ".join(s["undeclared"][:6])
              + (" 외 %d편" % (len(s["undeclared"]) - 6) if len(s["undeclared"]) > 6 else ""))
    if missing:
        print("  ⚠ 풀에 없는 카드를 가리킨다: %s — 오타이거나 카드가 지워졌다" % ", ".join(missing))

    if check:
        if wrote:
            print("::error::카드 %d종의 lab 칸이 판정과 다르다 — python build/pool_lab.py 를 돌릴 것"
                  % wrote)
            return 1
        print("  ~ 카드 lab 칸 대조 통과(선언된 %d종 전부 최신)" % len(s["cards"]))
        return 0

    if wrote:
        json.dump(pool, io.open(POOL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("→ %s · 카드 %d종에 판정을 붙였다" % (POOL, wrote))
    else:
        print("  바뀐 것 없음")
    n_lab = sum(1 for c in cards.values() if c.get("lab"))
    print("  풀 %d종 중 랩 검증이 붙은 것 %d종(%.0f%%)"
          % (len(cards), n_lab, 100.0 * n_lab / max(1, len(cards))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
