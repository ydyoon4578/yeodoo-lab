# -*- coding: utf-8 -*-
"""build/log_from_git.py — 커밋 이력으로 갱신 피드(data/updates.json)의 빠진 날을 채운다.

왜 만드나.
  `build/log_update.py` 는 **사람이 기억해서 불러야** 기록이 남는다. 그 방식은 이미 두 번
  깨졌다 — log_update.py 머리말이 «2026-07-23~25 사흘이 그렇게 비었다» 를 적어 두었고,
  이번 점검(2026-08-16)에서 **2026-08-12 ~ 08-16 닷새에 비-chore 커밋 123건이 있는데
  피드에는 사람 작업이 0건**인 것을 다시 찾았다. 자동 갱신 잡만 자기 기록을 남기고 있어서,
  갱신 기록 화면은 «마지막 변경 2026-08-11» 로 보였다.

  🚨 이것은 그 화면이 막으려던 상태의 정확한 거울상이다. 화면 머리말이 이렇게 적혀 있다 —
    «데이터 자동 갱신과 사람이 한 작업을 같은 줄에 섞어 남깁니다. 나누면 "데이터는 매일
    도는데 사이트는 몇 달째 그대로"인 상태가 가려지기 때문입니다.»
    지금은 그 반대다. 데이터만 기록되고 사람 작업이 안 남아, 사이트가 멈춘 것처럼 보인다.

무엇을 하나.
  · git log 에서 **chore(...) 가 아닌** 커밋을 읽어 (날짜, 시각, 제목) 을 만든다.
  · 제목으로 target 을 고른다(아래 RULES). 못 고르면 site 다 — 버리지 않는다.
  · 같은 (날짜·대상·제목) 이 이미 있으면 건너뛴다. 여러 번 돌려도 늘지 않는다.
  ⚠ 커밋 제목을 **그대로** 싣는다. 요약해 다듬지 않는다 — 다듬는 순간 이 도구도 사람의
    기억에 기대게 되고, 그게 처음에 깨진 바로 그 고리다.
    딱 하나 예외가 «%%» → «%» 치환이다(아래 참조). 뜻을 안 바꾸는 기계적 치환이고,
    안 하면 품질 관문이 산출물을 막는다.
  ⚠ chore(data)·chore(rotation) 은 이미 잡이 자기 기록을 남기므로 뺀다. 넣으면 두 벌이 된다.

  python build/log_from_git.py --since 2026-08-12            # 채운다
  python build/log_from_git.py --since 2026-08-12 --dry-run  # 무엇이 들어갈지만 본다
"""
from __future__ import annotations
import io
import json
import os
import re
import subprocess
import sys
import datetime as _dt

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "updates.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from log_update import TARGETS                                   # noqa: E402

# 제목 → target. 위에서부터 먼저 맞는 것을 쓴다. 오른쪽은 log_update.TARGETS 의 값이어야 한다.
RULES = [
    # 🚨 «홈» 을 맨 위에 둔다. 아래 규칙 어디에나 걸릴 수 있는 말(수익률·표·차트)이 제목에
    #   섞여 있어, 나중에 두면 홈 변경이 엉뚱한 대상으로 떨어진다.
    (r"홈|\bhome\b|index\.html|메뉴|nav\b", "site"),
    (r"guru|13F|거장|운용사|겹침|복제", "guru"),
    (r"rotation|탐색|최근동향", "rotation"),
    (r"regime|국면|사이클", "regime"),
    (r"stocks|종목 신호|종목 테크니컬|스윙|Williams|시그널", "stocks"),
    (r"\bco\b|종목 정보|종목 재무|페어", "company"),
    (r"sector|섹터", "sector"),
    (r"macro|경제지표", "macro"),
    (r"screener|스크리너", "screener"),
    (r"portfolio|포트폴리오|배포", "portfolio"),
    (r"filings|공시|8-K", "filings"),
    (r"sentiment|심리", "sentiment"),
    (r"holdings|보유", "holdings"),
    (r"method|방법론|규약|판정", "method"),
    (r"sources|출처|기준일", "sources"),
    # 랩 측정 커밋은 제목에 화면 이름이 없다 — «run(...)», «편향», «시점정확», «문턱» 처럼
    # 무엇을 쟀는지로만 적힌다. 이 줄이 없으면 그 37건이 전부 site 로 떨어진다(실측).
    (r"explorer|lab|전략|prereg|등록|백테스트|편출|지수|run\(|편향|시점정확|\bPIT\b|"
     r"문턱|관문|바스켓|타이밍|통계 기반|감사\(", "explorer"),
    (r"archive|기각|원장", "archive"),
]


def pick(title):
    for pat, tgt in RULES:
        if re.search(pat, title, re.I):
            return tgt if tgt in TARGETS else "site"
    return "site"


def main() -> int:
    a = sys.argv[1:]
    dry = "--dry-run" in a
    since = a[a.index("--since") + 1] if "--since" in a else None
    if not since:
        print("❌ --since <YYYY-MM-DD> 가 필요하다 — 어디부터 채울지 정하지 않으면 이력 전체를 긁는다")
        return 1
    # 🚨 하루 앞에서부터 긁는다. git 의 --since 는 **UTC 로 해석**되는데 커밋 시각은
    #   로컬(KST)이라, 새벽~오전 커밋이 «어제 UTC» 로 밀려 통째로 빠진다.
    #   실측(2026-08-18): 07:58 KST 커밋이 --since 2026-08-18 에 안 잡혔다 —
    #   그래서 **validate_site 는 «08-18 을 채우라» 는데 이 도구는 «채울 것이 없다»** 고 했다.
    #   검사와 채우는 도구가 서로 다른 말을 하면 둘 다 못 믿게 된다.
    # ⚠ 넓게 긁어도 안전하다 — 아래 have 로 중복을 거른다(여러 번 돌려도 안 늘어난다).
    try:
        _y, _m, _d = (int(x) for x in since.split("-"))
        since_q = (_dt.date(_y, _m, _d) - _dt.timedelta(days=1)).isoformat()
    except Exception:
        since_q = since
    try:
        out = subprocess.run(
            ["git", "log", "--since", since_q, "--pretty=%ad|%s",
             "--date=format-local:%Y-%m-%d|%H:%M"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except Exception as e:
        print("❌ git log 실패: %s" % e)
        return 1

    doc = json.load(io.open(P, encoding="utf-8"))
    have = {(e["dt"], e["target"], e["title"]) for e in doc["events"]}
    add, skip_chore, dup = [], 0, 0
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        dt, hm, title = parts
        if title.startswith("chore("):
            skip_chore += 1
            continue
        if title.startswith("Merge ") or title.startswith("merge:"):
            skip_chore += 1
            continue
        # 🚨 커밋 제목은 자유 문장이라 «%%» 가 들어올 수 있고, 그대로 실으면 화면에 두 개가
        #   찍힌다(validate_gate 의 '%%' 누출 검사가 막는다). 실제로 걸렸다 —
        #   하필 «'%%' 가 화면에 그대로 찍히던 것» 이라는, 그 버그를 고친 커밋의 제목이다.
        #   기계적으로 하나로 줄인다. 문장 뜻은 그대로고(퍼센트가 잘못 보였다는 말), 사람이
        #   제목마다 판단하지 않아도 된다 — 판단을 넣는 순간 이 도구도 기억에 기대게 된다.
        title = title.replace("%%", "%")
        if dt < since:
            continue                      # 넓게 긁되 요청 범위 밖은 버린다
        tgt = pick(title)
        key = (dt, tgt, title)
        if key in have:
            dup += 1
            continue
        have.add(key)
        add.append({"dt": dt, "hm": hm, "target": tgt, "title": title})

    print("커밋에서 %d건 · 이미 있음 %d · 자동잡·머지라 제외 %d" % (len(add), dup, skip_chore))
    import collections
    for t, n in collections.Counter(x["target"] for x in add).most_common():
        print("   %-10s %d건" % (t, n))
    for x in add[:6]:
        print("   예: %s %s [%s] %s" % (x["dt"], x["hm"], x["target"], x["title"][:56]))
    if dry:
        print("\n--dry-run — 파일을 쓰지 않았다")
        return 0
    if not add:
        print("채울 것이 없다")
        return 0
    doc["events"] = sorted(doc["events"] + add,
                           key=lambda e: (e["dt"], e.get("hm") or ""), reverse=True)
    doc["updated"] = max(e["dt"] for e in doc["events"])
    io.open(P, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("\n→ data/updates.json · 총 %d건" % len(doc["events"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
