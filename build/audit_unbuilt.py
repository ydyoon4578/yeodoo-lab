# -*- coding: utf-8 -*-
"""build/audit_unbuilt.py — «아무 잡도 굽지 않는 산출물» 을 찾는다.

왜 있나 (2026-08-18).
  짝인 build/audit_commit_lists.py 는 «잡이 쓰는데 커밋 목록에 없는 것» 을 찾는다.
  🚨 그런데 그 감사는 **잡에 들어 있는 산출물만** 본다. 아예 어느 잡에도 없는 빌더가
    구운 파일은 시야 밖이다 — 목록에 없으니 «빠졌다» 고도 말하지 않는다.
  실제로 그 빈칸에 둘이 있었다. data/guru_overlap.json · data/guru_qperf.json 은 입력이
  guru_history.json 뿐인데 어느 워크플로에도 없었다. 이력은 매주 토 자동 갱신되니,
  **갱신될 때마다 이 둘만 조용히 낡았다.** 잡이 죽지도 않고 화면도 아무 말을 안 한다.
  랩이 되풀이하는 «수집만 하고 배선 안 함» 의 가장 조용한 판이다.

무엇을 잡나 / 안 잡나.
  잡는 것: 빌더가 있고, 그 빌더를 **어느 잡도 안 부르는데**, 그 빌더가 읽는 입력 중
    하나 이상이 **잡이 자동으로 갱신하는 파일** 인 산출물. 입력은 움직이는데 산출물은
    영영 안 움직이는 조합이다.
  ⚠ 안 잡는 것: 「입력이 산출물보다 새롭다」 자체는 결함이 아니다. 주 1회 산출물이
    매일 갱신되는 stocks.json 보다 사흘 뒤처지는 것은 **설계대로**다. 주기가 있는
    산출물의 신선도는 각 잡의 check_freshness.py 가 본다 — 여기서 두 번 재지 않는다.
  ⚠ 손으로 굽는 것이 전부 결함도 아니다. 한 번 재고 얼려 두는 기록(사전등록 결과 등)은
    입력이 움직여도 다시 구우면 안 된다. 그런 것은 KNOWN 에 **이유와 함께** 적는다 —
    적지 않으면 이 감사가 계속 손가락질하고, 적어 두면 다음 사람이 이유를 읽는다.

🚨 이 감사는 «이상 없음» 을 증명하지 못한다.
  · 커버 판정은 «잡이 부르는 빌더 + 그것이 임포트하는 빌더» 로 **넓게** 잡는다.
    임포트했다고 그 쓰기 함수를 실제로 부르는 것은 아니므로, 실제보다 «덮였다» 고
    말할 수 있다(거짓 음성). 좁게 잡으면 home_summary 처럼 refresh_stocks 안에서
    불리는 것을 거짓 경보로 띄운다 — 둘 중 조용한 쪽을 골랐다.
  · 경로가 변수로 만들어지는 쓰기는 정적으로 못 푼다. 그 수를 끝에 찍는다.
  그래서 **아무것도 실패시키지 않는다**(항상 exit 0). 못 푼 것이 있는데 exit 1 을 내면
  «통과했다» 는 잘못된 안심을 준다 — audit_commit_lists.py 와 같은 이유다.

  python build/audit_unbuilt.py
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

# ── 일부러 손으로 굽는 산출물 — 이유를 적는다 ──────────────────────────────
# ⚠ 여기에 넣는 것은 «잡에 넣지 못하는 이유» 가 있어야 한다. «아직 안 했다» 는 이유가
#   아니다. 이유 없이 조용히 만들려고 넣으면 이 감사가 있는 뜻이 사라진다.
KNOWN = {
    "updates.json":
        "갱신 피드. 커밋 이력에서 만들고 사람이 덧붙인다 — 자료 입력이 없다.",
    "nav.json":
        "페이지 공통 셸. HTML 을 읽어 만들며 data/ 입력이 아니다.",
    "_pit_vol_cache.json":
        "PIT 거래량 캐시. 산출물이 아니라 재실행 비용을 줄이는 캐시다.",
    "delisted_names.json":
        "EODHD_API_TOKEN(유료 외부 열쇠)이 있어야 받는다. 러너에 그 비밀이 없다 — "
        "넣게 되면 이 줄을 지우고 잡에 붙일 것.",
}

# PIT 랩은 통째로 로컬에서 돈다(가격 캐시가 있는 PC). 파일마다 같은 말을 적지 않는다.
KNOWN_BUILDER = {
    "pit_backtest.py":
        "PIT 랩은 원본 가격 캐시가 있는 PC 에서만 돈다(러너에 그 캐시가 없다). "
        "낡으면 validate_site 의 시점정확 대조가 말한다.",
    "style_pit.py":
        "같은 이유로 로컬 전용. 낡으면 validate_site 가 «편향 캐비엇 기준일 불일치» 로 잡는다.",
}


def _src(rel):
    try:
        return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()
    except Exception:
        return ""


def writes_of(rel):
    """그 빌더가 쓰는 data/ 산출물, 그리고 정적으로 못 푼 쓰기 수."""
    s = _src(rel)
    out = set()
    for m in re.finditer(r'^\s*([A-Za-z_]\w*)\s*=\s*os\.path\.join\('
                         r'([^\n]*?)"([^"]+\.(?:json|pdf|csv|md))"\s*\)', s, re.M):
        var, mid, fn = m.groups()
        if ("DATA" in mid or '"data"' in mid) and \
           re.search(r'open\(\s*%s\s*,\s*"w' % re.escape(var), s):
            out.add(fn)
    out |= set(re.findall(r'open\(\s*os\.path\.join\([^\n]*?'
                          r'"([^"]+\.(?:json|pdf|csv|md))"\s*\)\s*,\s*"w', s))
    unresolved = len(re.findall(r'open\(\s*[a-z_]\w*\s*,\s*"w', s))
    return out, unresolved


def reads_of(rel):
    """읽는 data/ 파일(근사) — 주석 안의 파일명도 걸리므로 넓게 잡힌다.

    ⚠ 넓게 잡히는 쪽이 여기서는 안전하다. 이 집합은 «입력이 자동으로 움직이는가» 를
      묻는 데만 쓰이고, 넓으면 «움직인다» 쪽으로 기울어 더 자주 손가락질한다.
    """
    s = _src(rel)
    got = set(re.findall(r'"([a-z_0-9]+\.json)"', s))
    return got


def main() -> int:
    mods = {f[:-3] for f in os.listdir(os.path.join(ROOT, "build")) if f.endswith(".py")}

    # ① 잡이 부르는 빌더 + 그것이 임포트하는 빌더(폐포)
    direct = set()
    for wf in sorted(os.listdir(WF)):
        if not wf.endswith(".yml"):
            continue
        direct |= set(re.findall(r'build/([a-z_0-9]+)\.py', _src(".github/workflows/" + wf)))
    imports = {}
    for m in mods:
        s = _src("build/%s.py" % m)
        imports[m] = (set(re.findall(r'^\s*import\s+([a-z_0-9]+)', s, re.M)) |
                      set(re.findall(r'^\s*from\s+([a-z_0-9]+)\s+import', s, re.M))) & mods
    covered, stack = set(), [x for x in direct if x in mods]
    while stack:
        x = stack.pop()
        if x in covered:
            continue
        covered.add(x)
        stack += list(imports.get(x, ()))

    # ② 산출물 → 빌더, 그리고 «잡이 굽는 산출물» 집합
    owner, unres = {}, 0
    for m in sorted(mods):
        w, u = writes_of("build/%s.py" % m)
        unres += u
        for f in w:
            owner.setdefault(f, []).append(m + ".py")
    auto = {f for f, bs in owner.items() if any(b[:-3] in covered for b in bs)}

    # 🚨 git 이 비면 **조용히 «이상 없음»** 이 된다 — 감사기의 최악의 실패다.
    #   (실제로 겪었다: 이 검사가 무는지 증명하려고 임시 트리에 풀어 돌렸더니 저장소가
    #    아니라 목록이 0개였고, 도구는 태연히 «없음» 이라 답했다.)
    #   비면 디렉터리 목록으로 되돌리고, «미검증» 이라고 말한다.
    tracked = {os.path.basename(x) for x in subprocess.run(
        ["git", "ls-files", "data"], cwd=ROOT, capture_output=True, text=True
    ).stdout.split("\n") if x.count("/") == 1 and x}
    degraded = not tracked
    if degraded:
        _d = os.path.join(ROOT, "data")
        tracked = set(os.listdir(_d)) if os.path.isdir(_d) else set()

    rows = []
    for f in sorted(owner):
        if f not in tracked:
            continue                                   # 추적 안 되는 캐시·산출
        bs = owner[f]
        if any(b[:-3] in covered for b in bs):
            continue                                   # 어떤 잡이든 굽는다
        moving = sorted({g for b in bs for g in reads_of("build/" + b)
                         if g in auto and g != f})
        rows.append((f, bs, moving))

    print("빌더 %d개 · 잡이 부르는 것 %d개 · 임포트까지 %d개 · 산출물 %d개%s"
          % (len(mods), len(direct & mods), len(covered), len(tracked),
             "  ⚠ git 을 못 읽어 디렉터리 목록으로 대신했다 — 통과가 아니라 미검증이다"
             if degraded else ""))
    print()
    print("%-30s %-8s %s" % ("산출물", "입력", "상태"))
    flag = []
    for f, bs, moving in rows:
        why = KNOWN.get(f) or next((KNOWN_BUILDER[b] for b in bs if b in KNOWN_BUILDER), None)
        if why:
            print("%-30s %-8s 손으로 굽는다 — %s" % (f[:30], "움직임" if moving else "고정", why))
            continue
        if not moving:
            print("%-30s %-8s 입력이 자동 갱신되지 않는다 — 낡을 길이 없다" % (f[:30], "고정"))
            continue
        flag.append((f, bs, moving))
        print("%-30s %-8s 🚨 굽는 잡이 없다 (%s ← %s)"
              % (f[:30], "움직임", " · ".join(bs), " · ".join(moving[:3])))
    # ── ② 읽는 곳이 없는 산출물 ────────────────────────────────────────────
    # 🚨 이 랩의 격언 «재 놓고 안 실으면 잰 적 없는 것» 의 기계 판이다. 위 ①이 «굽는 잡이
    #   없다» 를 본다면 여기는 «읽는 곳이 없다» 를 본다 — 잡을 붙여 부지런히 구워도
    #   아무도 안 읽으면 잰 적 없는 것과 같다. 실제로 사전등록까지 갖춘 측정 둘이
    #   그 상태였다(index_add · index_drop_rank, 2026-08-18 이 검사가 찾음).
    # ⚠ «읽는다» 는 파일명이 저장소 어디에든(빌더·페이지·워크플로·문서) 나오면 인정한다.
    #   좁게 잡으면 fetch 문자열을 조립하는 화면을 놓쳐 거짓 경보가 난다.
    mentions = {}
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "data", "_build")]
        for fn in files:
            if not fn.endswith((".py", ".html", ".js", ".yml", ".md", ".sh")):
                continue
            rel = os.path.relpath(os.path.join(root, fn), ROOT)
            if rel.startswith("build" + os.sep + "audit_"):
                continue                       # 감사기 자신은 «읽는 곳» 이 아니다
            body = _src(rel)
            for f in owner:
                if f in body and rel != os.path.join("build", (owner[f][0])):
                    mentions.setdefault(f, set()).add(rel)
    unread = sorted(f for f in owner if f in tracked and not mentions.get(f))
    if unread:
        print()
        print("🚨 구워는 놓았는데 **읽는 곳이 없는** 산출물 %d개:" % len(unread))
        for f in unread:
            print("   data/%s ← %s  (만든 빌더 말고는 저장소 어디에도 안 나온다)"
                  % (f, " · ".join(owner[f])))
        print("   → 화면·리포트에 실을 것. 이 랩은 «재 놓고 안 실으면 잰 적 없는 것» 이라 적어 뒀다.")

    print()
    if flag:
        print("🚨 입력은 자동으로 움직이는데 **굽는 잡이 없는** 산출물 %d개:" % len(flag))
        for f, bs, moving in flag:
            print("   data/%s ← %s" % (f, " · ".join(bs)))
            print("      움직이는 입력: %s" % " · ".join(moving))
        print("   → 그 빌더를 입력을 굽는 잡에 붙이고 ci_push 목록에도 넣을 것.")
        print("     붙일 수 없는 이유가 있으면 KNOWN 에 **이유와 함께** 적을 것.")
    else:
        print("굽는 잡 없이 낡을 산출물 없음.")
    print("⚠ 커버는 «잡이 부르는 빌더 + 임포트» 로 넓게 잡았다 — 실제보다 덮였다고")
    print("  말할 수 있다(거짓 음성). 정적으로 못 푼 쓰기 %d곳." % unres)
    print("  짝인 build/audit_commit_lists.py 는 반대쪽(«잡이 쓰는데 목록에 없는 것»)을 본다.")
    return 0        # 🚨 일부러 항상 0 — 머리말 참조


if __name__ == "__main__":
    sys.exit(main())
