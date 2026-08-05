# -*- coding: utf-8 -*-
"""검증을 '절대 기준'이 아니라 '회귀 기준'으로 건다.

🚨 2026-08-05 — 이 파일이 생긴 이유.

수집 잡 17개가 전부 이 순서였다:

    수집 → Validate → Commit if changed

의도는 옳다. 깨진 상태를 게시하지 말라는 것이다. 그런데 Validate 가 **저장소 전체의
절대 상태**를 본다. 그래서 이런 일이 벌어졌다:

  · kb.html 이 잠금 메타(ph·공통셸·data-tool)를 잃은 채 main 에 올라가 있었다.
  · 그 잡들과 아무 상관 없는 결함이다. 그 잡들이 만든 것도 아니고 고칠 수도 없다.
  · 그런데 08-05 새벽, 시장 국면·시장 심리·실적 일정·자산 패널 네 잡이 전부
    **자료를 정상으로 다 받아 놓고** 이 단계에서 죽었다. Finnhub 은 4103개 심볼을
    49영업일치 교차검증까지 마친 뒤에 버려졌다.
  · 커밋 단계가 안 돌았으니 받은 자료는 러너와 함께 사라졌다. 화면의 기준일 네 개가
    조용히 08-03 에 멈췄다. **실패는 로그에만 있고 사이트는 멀쩡해 보인다.**

되묻자. 이 관문이 막아야 하는 것은 "이 잡이 무언가를 깼는가"다. 실제로 막고 있던 것은
"저장소가 지금 깨끗한가"였다. 둘은 다르고, 다를 때 손해는 늘 자료 쪽이 본다.

그래서 기준선을 잡는다. 체크아웃 직후 한 번 재고(baseline), 일 다 하고 또 재서(check),
**늘어났을 때만** 막는다. 원래 깨져 있었으면 그건 이 잡의 책임이 아니다 — 크게 떠들고
자료는 커밋한다. 깨진 사실 자체는 push 마다 도는 Validate site 워크플로가 계속 붉게
띄우므로 숨겨지지 않는다.

  baseline  … 세고 파일에 적는다. **항상 0으로 끝난다.**
  check     … 다시 세서 기준선과 비교. 늘었으면 1, 아니면 0.
              기준선 파일이 없으면 절대 기준으로 돌아간다(안전한 쪽).
"""
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = os.path.join(ROOT, ".validate_baseline")
# "사이트 검증: 실패 ❌ 3건" / "사이트 검증: 통과 ✅"
_RE = re.compile(r"사이트 검증:\s*(?:실패\s*❌\s*(\d+)건|통과)")


def _measure():
    """validate_site.py 를 돌려 (오류 개수, 출력) 을 돌려준다."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "build", "validate_site.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    out = (r.stdout or "") + (r.stderr or "")
    m = None
    for m2 in _RE.finditer(out):
        m = m2                      # 마지막 판정줄이 정본
    if m is None:
        # 판정줄을 못 찾았다 = 검증기가 예외로 죽었다. 세지 못한 것을 0으로 읽으면
        # 기준선이 0이 되어 이후 모든 실패를 '회귀'로 만든다. 그건 지금 고치려는
        # 것과 정반대다. 셀 수 없으면 셀 수 없다고 말한다.
        return None, out
    return int(m.group(1) or 0), out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    n, out = _measure()

    if mode == "baseline":
        if n is None:
            print("[관문] 기준선을 못 쟀다 — 검증기가 판정줄 없이 죽었다. 절대 기준으로 돌린다.")
            print(out[-3000:])
            if os.path.exists(MARK):
                os.remove(MARK)
            return 0                                  # 기준선 단계는 절대 막지 않는다
        with open(MARK, "w", encoding="utf-8") as fh:
            fh.write(str(n))
        print("[관문] 기준선 %d건 — 일을 시작하기 전 저장소 상태다." % n)
        if n:
            print(out[-3000:])
        return 0

    # ── check ────────────────────────────────────────────────────────────
    if n is None:
        print(out)
        print("[관문] 검증기가 판정줄 없이 죽었다 — 막는다.")
        return 1

    base = None
    if os.path.exists(MARK):
        try:
            base = int(open(MARK, encoding="utf-8").read().strip())
        except ValueError:
            base = None

    print(out.rstrip())
    if n == 0:
        return 0
    if base is None:
        print("[관문] 기준선이 없다 — 절대 기준으로 막는다. (%d건)" % n)
        return 1
    if n > base:
        print("[관문] %d건 → %d건. **이 잡이 %d건을 늘렸다.** 막는다."
              % (base, n, n - base))
        return 1
    print("[관문] ⚠ %d건 남아 있지만 시작할 때도 %d건이었다 — 이 잡이 깬 것이 아니다.\n"
          "       자료는 커밋한다. 남은 결함은 Validate site 워크플로가 계속 띄운다."
          % (n, base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
