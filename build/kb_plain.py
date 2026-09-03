# -*- coding: utf-8 -*-
"""잠금 페이지의 **전체 평문**을 _build/pages/<페이지> 로 재구성한다.

왜 필요한가. 이 사이트의 잠금 페이지는 둘이다 — kb.html 과 sources.html(2026-08-11 추가).
배포본은 '평문 셸 + 암호화된 본문(PAYLOAD)' 이고, 본문 평문은 _build/pages/*_content.html
조각으로만 관리된다. 그런데 validate_site.py 의 평문 의존 검사 6종
(공통 셸 위치 · NAVCSS 오염 · 미정의 CSS 변수 · 스타일 블록 균형 · 모바일 word-break ·
인라인 JS 괄호/미정의 호출)은 **조각이 아니라 열린 뒤의 페이지 한 장**을 본다.
그 파일이 없어 6종이 늘 SKIP 됐고, 운영 PC의 평문 필수 모드가 이를 실패로 승격시켰다.

무엇을 하나. 배포본의 본문 슬롯(kb 는 <main>, sources 는 <div>) 자리에 조각을 끼워 넣는다.
게이트가 복호 후 하는 일(#content 에 innerHTML 주입)과 같은 결과다.

스테일 방지. 조각의 sha256 이 게이트에 박힌 ph 와 다르면 **만들지 않고 실패**한다.
낡은 조각으로 만든 평문에 초록불을 주면 검사가 있으나 마나다.

    python build/kb_plain.py --page sources
"""
import hashlib
import io
import os
import re
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAINDIR = os.path.join(ROOT, "_build", "pages")

# 🚨 2026-08-11 — 잠금 페이지가 둘이 되면서 일반화했다. 그 전에는 kb.html 이 상수로 박혀
#   있어서, sources.html 을 잠근 직후 이 스크립트가 **kb 조각을 찾다가 실패**했다
#   ("없음: _build/pages/kb_content.html"). 잠근 페이지와 평문을 만드는 페이지가 달랐다.
# ⚠ 본문 슬롯 태그가 페이지마다 다르다 — kb 는 <main>, sources 는 <div> 다.
#   슬롯을 상수 하나로 두면 새 페이지에서 "본문 슬롯을 못 찾았다"로 조용히 실패한다.
PAGES = {
    "kb":      ("kb.html",      "kb_content.html",      '<main id="content" hidden></main>', "main"),
    "sources": ("sources.html", "sources_content.html", '<div id="content" hidden></div>',   "div"),
    # 2026-08-14 — 개인 OKR·KPI 원장. 게이트 셸을 sources.html 에서 떠서 만들었으므로
    # 본문 슬롯도 sources 와 같은 <div> 다.
    "ok":      ("ok.html",      "ok_content.html",      '<div id="content" hidden></div>',   "div"),
    # 2026-08-20 — 운용 포트폴리오. 셸은 sources.html 에서 떴으므로 슬롯 형태가 같다.
    "portfolio": ("portfolio.html", "portfolio_content.html", '<div id="content" hidden></div>', "div"),
    # 2026-09-03 — 사내 DB 지도. 셸은 sources.html 에서 떴으므로 슬롯 형태가 같다.
    "db":      ("db.html",      "db_content.html",      '<div id="content" hidden></div>',   "div"),
}


def main(page="kb"):
    _g, _f, SLOT, _tag = PAGES[page]
    GATE = os.path.join(ROOT, _g)
    FRAG = os.path.join(PLAINDIR, _f)
    OUT = os.path.join(PLAINDIR, _g)
    for p in (GATE, FRAG):
        if not os.path.exists(p):
            print("없음:", p)
            return 1

    # newline="" = 바이트 정확 읽기. 이게 없으면 유니버설 개행 번역이 끼어 CRLF 조각의
    # sha256 이 달라진다 — validate_site.py 와 kb_lock.py 는 둘 다 바이트 정확이라
    # 이 파일만 어긋나 '조각 불일치'가 영원히 뜬다(실측 2026-07-29).
    gate = io.open(GATE, encoding="utf-8", newline="").read()
    frag = io.open(FRAG, encoding="utf-8", newline="").read()

    m = re.search(r'ph:\s*["\']([0-9a-f]{64})["\']', gate)
    if not m:
        print("%s 게이트에 평문 지문(ph)이 없다 — 잠금 도구가 ph 를 함께 기록해야 한다" % _g)
        return 2
    want = m.group(1)
    got = hashlib.sha256(frag.encode("utf-8")).hexdigest()
    if got != want:
        print("조각 평문이 배포 암호문과 불일치 — 다른 PC에서 재잠금됐거나 사본이 낡았다")
        print("  게이트 ph :", want)
        print("  조각 sha256:", got)
        return 3

    if SLOT not in gate:
        print("본문 슬롯을 못 찾았다 — %s 구조가 바뀌었다. 이 스크립트를 맞춰 고칠 것:" % _g)
        print("  기대:", SLOT)
        return 4

    full = gate.replace(SLOT, '<%s id="content">\n%s\n</%s>' % (_tag, frag, _tag))
    io.open(OUT, "w", encoding="utf-8", newline="").write(full)
    print("생성:", OUT)
    print("  배포본 %d + 조각 %d → 평문 %d bytes (ph %s 일치)"
          % (len(gate), len(frag), len(full), want[:12]))
    return 0


if __name__ == "__main__":
    import argparse
    _ap = argparse.ArgumentParser(description="잠금 페이지의 전체 평문을 _build/pages/ 로 재구성")
    _ap.add_argument("--page", default="kb", choices=sorted(PAGES),
                     help="평문을 만들 페이지(기본 kb — 종전 동작 그대로)")
    sys.exit(main(_ap.parse_args().page))
