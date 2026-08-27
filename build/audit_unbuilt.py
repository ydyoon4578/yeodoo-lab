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
    "index_drop_rank.json":
        "편출 종목 가격 캐시(data/_pit_px_cache.json)가 있어야 돈다 — gitignore 라 "
        "러너에 없다(PIT 랩과 같은 사유). 결과는 constituents.html «편출은 어디서 "
        "일어나나» 구획이 읽는다(2026-08-18 배선).",
    "index_add.json":
        "한 번 재고 **얼린** 사전등록 측정이다(PREREG-2026-08-14-INDEXADD). 자동으로 다시 "
        "구우면 얼린 기록이 조용히 바뀐다 — 그러면 안 되는 종류의 파일이다.",
    "e12.json":
        "한 번 재고 **얼린** 사전등록 측정이다(PREREG-2026-08-19-E12 · SPX/NDX 편입·제외 "
        "이벤트). 자동으로 다시 구우면 얼린 기록이 조용히 바뀐다. 결과는 "
        "PREREG-2026-08-19-E12-RESULT.md 와 tested_not_published.json 의 e-e12press · "
        "e-e12rev 두 줄로 실렸다.",
    "e12_fade.json":
        "얼린 사전등록 측정(PREREG-2026-08-19-E12 §7 · 개선판 «편입 페이드» — 자기 채점 "
        "0/4 로 기각). 자동 재굽기 금지 — 기록이다.",
    "pead.json":
        "얼린 사전등록 측정(PREREG-2026-08-19-PEAD · 채점 3/5 기각). 자동 재굽기 금지 — 기록이다.",
    "earn_dates.json":
        "실적발표일 원장(8-K Item 2.02 접수일 · 795종 · 54,125건). 지금은 얼린 PEAD 측정의 "
        "입력으로만 쓰여 갱신이 필요 없다. ⚠ 발표일 앵커 규칙을 **라이브로** 올리게 되면 "
        "이 원장은 매주 갱신돼야 하고, 그때 refresh_earndates 의 재개 로직을 «한 번 받은 "
        "종목은 영영 건너뜀» 에서 증분(마지막 접수일 이후만)으로 고쳐야 한다 — "
        "고객 집중도에서 밟은 그 함정이다(2026-08-19).",
    "tripod.json":
        "얼린 사전등록 측정(PREREG-2026-08-19-TRIPOD · 5/5 후보 — PIT 직접 측정 대기). "
        "자동 재굽기 금지 — 기록이다.",
    "pead2.json":
        "얼린 사전등록 측정(PREREG-2026-08-19-PEAD2 · 1/5 기각). 자동 재굽기 금지 — 기록이다.",
    "aegis.json":
        "얼린 사전등록 측정(PREREG-2026-08-19-AEGIS · 사용자 6문 2/6 기각 — 분해 A/B/C 포함). "
        "자동 재굽기 금지 — 기록이다.",
    "aegis2.json":
        "얼린 사전등록 측정(PREREG-2026-08-19-AEGIS2 · 사용자 6문 5/6 · 선언 BM 3/3 통과). "
        "자동 재굽기 금지 — 기록이다. 라이브 게시가 결정되면 주간 갱신 잡을 만들고 이 줄을 고칠 것.",
    "aegis3.json":
        "얼린 사전등록 측정(PREREG-2026-08-19-AEGIS3 · 사용자 6문 5/6 — U3 만 0.41%p 미달, "
        "vs NDX 3문 전부 통과). 자동 재굽기 금지 — 기록이다.",
    "tilt.json":
        "얼린 사전등록 측정(PREREG-2026-08-20-TILT · 사용자 3문 3/3 · 틸트효과 t 1.22). "
        "기준 비중이 DB(커밋 금지 · gitignore 캐시)라 러너가 재생산할 수 없다 — "
        "라이브로 올리려면 로컬 잡 + 주간 비중 갱신이 필요하다.",
    "float_decomp.json":
        "얼린 사전등록 측정(PREREG-2026-08-27-FLOAT · 부동주 조정 vs 개별 상한 분해 — "
        "수익률로는 네 짝 전부 |t|<0.5, 비중으로는 상한 30.2%p 대 부동주 16.4%p). "
        "기준 비중이 DB(커밋 금지 · gitignore 캐시)라 러너 재생산 불가 — tilt.json 과 같은 "
        "사유. 결과는 rotation_pool D16 카드의 performance 가 읽는다(2026-08-27 배선).",
    "revscreen.json":
        "얼린 사전등록 측정(PREREG-2026-08-28-REVSCREEN · 하향 리비전 네거티브 스크린 "
        "오버레이 — 발동률 6.7~10.1%·회전 증가 연 0.17~0.81회로 형태는 쌌으나 챔피언 넷 중 "
        "셋에서 샤프 하락, 부호가 갈려 기각). 입력이 투자의견 캐시(data/_ratings_cache.json · "
        "커밋 금지)라 러너가 재생산할 수 없다 — tilt.json 과 같은 사유. 결과는 rotation_pool "
        "E21 카드가 읽는다(2026-08-28 배선).",
    "wvane.json":
        "얼린 사전등록 측정(PREREG-2026-08-20-WVANE · 주 판정 V1 회전 기각 −0.05%p). "
        "기준 비중이 DB(커밋 금지)라 러너 재생산 불가 — tilt.json 과 같은 사유.",
    "fleet.json":
        "얼린 사전등록 측정(PREREG-2026-08-20-FLEET · 무선별 6축 배치 — 주 판정 셀 ④ 기각). "
        "기준 비중이 DB(커밋 금지)라 러너 재생산 불가 — tilt/wvane 과 같은 사유.",
    "web.json":
        "얼린 사전등록 측정(PREREG-2026-08-20-WEB · 주 판정 셀 ① — 계열 최초). "
        "기준 비중이 DB(커밋 금지)라 러너 재생산 불가 — tilt 계열과 같은 사유.",
    "tripod_pit.json":
        "얼린 관문 측정(삼각대 차단 관문 해소 · 혼합 PIT t 2.56 — PREREG-2026-08-19-TRIPOD). "
        "재료(pit_strategies chart.monthly)가 갱신되면 --refreeze 로만 다시 잰다.",
    "strategy_forward.json":
        "틸트 계열 전방 주간 기록(append-only · build/forward_weekly.py). 입력이 DB 비중 "
        "캐시라 로컬 주간 절차로만 자란다(RUNBOOK-FORWARD.md) — 러너 잡이 없는 것이 정상.",
    "delisted_names.json":
        "EODHD_API_TOKEN(유료 외부 열쇠)이 있어야 받는다. 러너에 그 비밀이 없다 — "
        "넣게 되면 이 줄을 지우고 잡에 붙일 것.",
}

# ── ②(읽는 곳이 없다) 전용 사유 ────────────────────────────────────────────
# 🚨 ①의 KNOWN 을 여기 재활용하지 않는다. ①의 사유는 «왜 잡에 못 붙이나» 이고
#   ②가 묻는 것은 «왜 아무도 안 읽나» 다 — 다른 질문이다. 한 번 합쳐 놨다가
#   pit_fetch_report·pit_reuse 가 «러너에 캐시가 없다» 는 상관없는 이유로 조용해졌다.
#   감사기가 상관없는 이유로 발견을 덮으면 그때부터 거짓말을 하는 것이다.
KNOWN_UNREAD = {
    "tripod_pit.json":
        "결과가 build/tested_not_published.json 의 e-tripod 한 줄(관문 해소 · 혼합 PIT t 2.56)로 "
        "실렸고 report.html «돌렸지만 게시 안 함» 에 나온다 — index_add.json 과 같은 패턴. "
        "원본 JSON 은 그 얼린 기록을 만든 작업 산출물이다.",
    "strategy_forward.json":
        "전방 주간 기록의 원장(append-only) — 지금 0행이라 읽을 화면이 아직 없다. "
        "20주쯤 쌓이면 백테스트와의 첫 대조 화면이 이것을 읽는다(RUNBOOK-FORWARD.md). "
        "그때 이 줄을 지우고 독자를 붙일 것.",
    "index_add.json":
        "결과가 build/tested_not_published.json 의 e-spxadd1/3/6 · e-ndxadd1/3/6 여섯 "
        "줄로 실렸고 report.html «돌렸지만 게시 안 함» 에 나온다(2026-08-18). 원본 JSON 은 "
        "그 얼린 기록을 만든 작업 산출물이다.",
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
    # ⚠ ①과 같은 KNOWN 을 여기에도 건다. 이유를 적어 둔 것까지 계속 손가락질하면
    #   목록이 소음이 되고, 소음이 되면 아무도 안 본다 — 그게 이 감사가 죽는 길이다.
    unread = sorted(f for f in owner
                    if f in tracked and not mentions.get(f)
                    and f not in KNOWN_UNREAD)
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
