# -*- coding: utf-8 -*-
"""build/portfolio_go.py — 운용 포트폴리오 갱신 한 방 (사내 PC 전용)

왜 있나. 2026-08-21 사용자: «git pull → portfolio_fund → kb_lock → add → commit → push,
이거 굉장히 번거로우니 그냥 비번 풀어버릴래». 번거로운 것은 **암호가 아니라 여섯 줄**이다.
암호는 한 번 치면 되고, 나머지는 전부 기계가 할 수 있는 일이다. 그래서 여기 묶는다 —
잠금을 유지한 채로 손을 한 번으로 줄인다.

  python build/portfolio_go.py

하는 일(순서 고정 — 이 순서를 틀려서 옛 화면이 두 번 배포됐다):
  ① git pull --rebase --autostash   원격 먼저(비-빨리감기 거부를 없앤다)
  ② python build/portfolio_fund.py  조각 재생성 ← 이걸 건너뛰면 옛 화면이 다시 잠긴다
  ③ python build/kb_lock.py --page portfolio   암호 한 번 입력
  ④ git add portfolio.html && commit && push   바뀐 게 없으면 조용히 건너뛴다

지금까지 실제로 밟은 함정을 전부 여기서 막는다:
  · 조각 재생성 건너뛰기 → ②를 항상 돈다(그래도 kb_lock 의 낡은 조각 가드가 이중 방어)
  · portfolio.html 에 로컬 수정이 남아 pull 중단 → --autostash
  · 원격이 앞서 push 거부 → ①이 먼저 rebase
  · 안내문을 명령에 같이 붙여넣어 생긴 `git`·`python` 쓰레기 파일 → 있으면 지운다
  · 커밋 없이 push 해서 "Everything up-to-date" → ④가 add/commit 을 반드시 한다

⚠ 어느 단계든 실패하면 **거기서 멈춘다.** 반쯤 된 상태로 push 하지 않는다.
"""
from __future__ import annotations
import io
import os
import subprocess
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run(cmd, step, capture=False):
    print("\n[%s] %s" % (step, " ".join(cmd)))
    if capture:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        print(out.rstrip())
        return r.returncode, out
    # 암호 입력이 있는 단계는 화면을 그대로 물려준다(캡처하면 getpass 가 못 읽는다)
    r = subprocess.run(cmd, cwd=ROOT)
    return r.returncode, ""


def die(msg):
    print("\n🚨 %s" % msg)
    print("   여기서 멈춘다 — 반쯤 된 상태로 배포하지 않는다.")
    raise SystemExit(1)


def main() -> int:
    print("운용 포트폴리오 갱신 — 조각 재생성 → 재잠금 → 배포")

    # 안내문을 명령에 붙여넣다 생긴 쓰레기 파일. 있으면 지운다(둘 다 저장소에 없어야 할 이름).
    for junk in ("git", "python"):
        p = os.path.join(ROOT, junk)
        if os.path.isfile(p):
            os.remove(p)
            print("  (정리) 잘못 만들어진 파일 %s 를 지웠다" % junk)

    rc, _ = run(["git", "pull", "--rebase", "--autostash"], "1/4 원격 받기")
    if rc != 0:
        die("pull 실패 — 충돌이면 그 파일을 정리한 뒤 다시 돌릴 것.")

    rc, _ = run([PY, os.path.join("build", "portfolio_fund.py")], "2/4 조각 재생성")
    if rc != 0:
        die("조각 생성 실패 — 위 traceback 을 보고 고칠 것(사내 export·DB 연결 확인).")

    rc, _ = run([PY, os.path.join("build", "kb_lock.py"), "--page", "portfolio"], "3/4 재잠금")
    if rc != 0:
        die("재잠금 실패 — 암호 두 번을 같게 입력했는지 볼 것.")

    rc, out = run(["git", "status", "--porcelain", "portfolio.html"], "4/4 배포", capture=True)
    if not out.strip():
        print("\n✅ portfolio.html 에 바뀐 것이 없다 — 이미 최신이다. 커밋 없이 끝낸다.")
        return 0
    rc, _ = run(["git", "add", "portfolio.html"], "4/4 배포", capture=True)
    if rc != 0:
        die("git add 실패")
    rc, out = run(["git", "commit", "-m", "운용 포트폴리오 재잠금"], "4/4 배포", capture=True)
    if rc != 0:
        die("commit 실패")
    rc, _ = run(["git", "push"], "4/4 배포", capture=True)
    if rc != 0:
        # 그 사이 원격이 또 앞섰을 수 있다 — 한 번만 다시 맞춰 본다
        print("  push 거부 — 원격이 그 사이 앞섰다. rebase 후 한 번 더 시도한다.")
        rc, _ = run(["git", "pull", "--rebase", "--autostash"], "4/4 배포", capture=True)
        if rc != 0:
            die("재-rebase 실패")
        rc, _ = run(["git", "push"], "4/4 배포", capture=True)
        if rc != 0:
            die("push 실패 — 원격 상태를 확인할 것.")
    print("\n✅ 배포 완료. 1~2분 뒤 사이트에 반영된다.")
    print("   https://ydyoon4578.github.io/yeodoo-lab/portfolio.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
