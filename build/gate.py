#!/usr/bin/env python3
"""생성기가 왜 멈췄는지를 GitHub 체크런 **주석**으로 올린다.

왜 필요한가(2026-07-31). 이 저장소의 생성기들은 데이터가 수상하면 `raise SystemExit("사유")`
또는 `❌ …` 를 찍고 `return 1` 로 멈춘다. 이전본을 지키는 옳은 설계다. 그런데 그 **사유는 실행
로그 본문에만** 남는다. Actions API 의 로그 엔드포인트는 외부 스토리지 도메인으로 리다이렉트하는데
사내 PC 는 그쪽으로 나갈 수 없다(보안 화이트리스트). 그래서 "왜 죽었나"를 물을 수단이 없었다 —
실제로 refresh-stocks 실패 원인을 API 만으로는 끝내 못 알아냈고, 주석에는
"Process completed with exit code 1." 한 줄뿐이었다.

Actions 는 stdout 의 `::error::` 줄을 체크런 주석으로 올리고, 주석은 api.github.com 으로 읽힌다.
그래서 멈춤 사유를 그 형식으로 한 번 더 찍는다. 로그를 못 열어도 원인이 남는다.

사용:
    if __name__ == "__main__":
        import gate
        gate.run(main, "종목 시그널")
"""
from __future__ import annotations

import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

_MAXLEN = 900          # 주석 한 줄 상한. 넘기면 UI 가 자른다.
_MARKS = ("❌", "🚨")   # `return 1` 로 멈추는 생성기들이 사유를 찍을 때 쓰는 표식


class _Tee:
    """stdout 을 그대로 흘리되, 실패 표식이 붙은 마지막 줄을 기억한다.

    `return 1` 로 끝나는 생성기는 예외를 안 던지므로 사유를 잡을 다른 방법이 없다.
    """

    def __init__(self, inner):
        self._inner, self._buf, self.last = inner, "", None

    def write(self, s):
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if any(m in line for m in _MARKS):
                self.last = line.strip()
        return self._inner.write(s)

    def flush(self):
        return self._inner.flush()

    def __getattr__(self, n):
        return getattr(self._inner, n)


def _emit(label, msg):
    if not msg:
        return
    # 주석은 한 줄이다. 줄바꿈을 접고 길이를 자른다.
    one = " ".join(str(msg).split())[:_MAXLEN]
    print("::error title=%s 중단::%s" % (label, one), flush=True)


def run(main, label):
    """생성기의 main() 을 감싸 실행하고, 멈춤 사유를 주석으로 올린 뒤 같은 종료코드로 끝낸다."""
    tee = _Tee(sys.stdout)
    sys.stdout = tee
    try:
        rc = main()
    except SystemExit as e:
        sys.stdout = tee._inner
        # `raise SystemExit("사유")` 는 code 에 문자열이 들어온다. 정수면 사유가 없다는 뜻이라
        # 직전에 찍힌 실패 표식 줄로 대신한다.
        _emit(label, e.code if isinstance(e.code, str) and e.code.strip() else tee.last)
        raise
    except BaseException as e:
        sys.stdout = tee._inner
        _emit(label, "%s: %s" % (type(e).__name__, e))
        raise
    sys.stdout = tee._inner
    if rc:
        _emit(label, tee.last or ("종료코드 %s" % rc))
    sys.exit(rc or 0)
