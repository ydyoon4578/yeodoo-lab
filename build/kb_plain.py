# -*- coding: utf-8 -*-
"""kb.html 의 **전체 평문**을 _build/pages/kb.html 로 재구성한다.

왜 필요한가. kb.html 은 이 사이트에서 유일하게 남은 잠금 페이지다(나머지는 해제됨).
배포본은 '평문 셸 + 암호화된 본문(PAYLOAD)' 이고, 본문 평문은 _build/pages/kb_content.html
조각으로만 관리된다. 그런데 validate_site.py 의 평문 의존 검사 6종
(공통 셸 위치 · NAVCSS 오염 · 미정의 CSS 변수 · 스타일 블록 균형 · 모바일 word-break ·
인라인 JS 괄호/미정의 호출)은 **조각이 아니라 열린 뒤의 페이지 한 장**을 본다.
그 파일이 없어 6종이 늘 SKIP 됐고, 운영 PC의 평문 필수 모드가 이를 실패로 승격시켰다.

무엇을 하나. 배포본의 `<main id="content" hidden></main>` 자리에 조각을 끼워 넣는다.
게이트가 복호 후 하는 일(#content 에 innerHTML 주입)과 같은 결과다.

스테일 방지. 조각의 sha256 이 게이트에 박힌 ph 와 다르면 **만들지 않고 실패**한다.
낡은 조각으로 만든 평문에 초록불을 주면 검사가 있으나 마나다.

    python build/kb_plain.py
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
GATE = os.path.join(ROOT, "kb.html")
FRAG = os.path.join(PLAINDIR, "kb_content.html")
OUT = os.path.join(PLAINDIR, "kb.html")

SLOT = '<main id="content" hidden></main>'


def main():
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
        print("kb.html 게이트에 평문 지문(ph)이 없다 — 잠금 도구가 ph 를 함께 기록해야 한다")
        return 2
    want = m.group(1)
    got = hashlib.sha256(frag.encode("utf-8")).hexdigest()
    if got != want:
        print("조각 평문이 배포 암호문과 불일치 — 다른 PC에서 재잠금됐거나 사본이 낡았다")
        print("  게이트 ph :", want)
        print("  조각 sha256:", got)
        return 3

    if SLOT not in gate:
        print("본문 슬롯을 못 찾았다 — kb.html 구조가 바뀌었다. 이 스크립트를 맞춰 고칠 것:")
        print("  기대:", SLOT)
        return 4

    full = gate.replace(SLOT, '<main id="content">\n%s\n</main>' % frag)
    io.open(OUT, "w", encoding="utf-8", newline="").write(full)
    print("생성:", OUT)
    print("  배포본 %d + 조각 %d → 평문 %d bytes (ph %s 일치)"
          % (len(gate), len(frag), len(full), want[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
